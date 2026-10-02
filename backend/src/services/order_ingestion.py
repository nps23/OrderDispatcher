import collections
import csv
import hashlib
import io
import uuid
from datetime import datetime, timezone

import fastapi
import pydantic
import sqlalchemy
import sqlalchemy.orm

from src.api import models as api_models
from src.storage import models as storage_models


def _find_order(
    session: sqlalchemy.orm.Session,
    source_order_id: str,
) -> storage_models.Order | None:
    statement = (
        sqlalchemy.select(storage_models.Order)
        .options(sqlalchemy.orm.selectinload(storage_models.Order.items))
        .where(
            storage_models.Order.source_order_id == source_order_id,
        )
    )
    return session.scalars(statement).one_or_none()


def _add_order_event(
    order: storage_models.Order,
    event_type: str,
    source: storage_models.IngestionSource | None,
    details: dict[str, object],
) -> None:
    order.events.append(
        storage_models.OrderEvent(
            event_type=event_type,
            ingestion_source=source,
            details=details,
        )
    )


def _split_csv_items(value: str) -> list[str]:
    items = []
    current = []
    parenthesis_depth = 0
    for character in value:
        if character == "(":
            parenthesis_depth += 1
        elif character == ")" and parenthesis_depth:
            parenthesis_depth -= 1
        if character in ",\r\n" and parenthesis_depth == 0:
            item = "".join(current).strip()
            if item:
                items.append(item)
            current = []
        else:
            current.append(character)
    item = "".join(current).strip()
    if item:
        items.append(item)
    return items


# TODO: All of this CRUD stuff should be behind a shared manager
def ingest_webhook_order(
    session: sqlalchemy.orm.Session,
    payload: api_models.WebhookEvent,
) -> storage_models.Order:
    source = storage_models.IngestionSource.WEBHOOK
    source_order_id = str(payload.order_id)

    try:
        order = _find_order(session, source_order_id)
        cancelled = bool(payload.update and "cancelled" in payload.update)
        if order is None:
            order = storage_models.Order(
                source_order_id=source_order_id,
                status=(
                    storage_models.OrderStatus.CANCELLED
                    if cancelled
                    else storage_models.OrderStatus.RECEIVED
                ),
                items=[
                    storage_models.OrderItem(name=name)
                    for name in payload.items
                ],
            )
            session.add(order)
            _add_order_event(
                order,
                "order_cancelled" if cancelled else "order_received",
                source,
                {"status": order.status.value},
            )
        else:
            changed = [item.name for item in order.items] != payload.items
            if changed:
                order.items = [
                    storage_models.OrderItem(name=name)
                    for name in payload.items
                ]
            if cancelled and order.status != storage_models.OrderStatus.CANCELLED:
                order.status = storage_models.OrderStatus.CANCELLED
                changed = True
            if changed:
                _add_order_event(
                    order,
                    "order_cancelled"
                    if cancelled
                    else "order_updated",
                    source,
                    {"status": order.status.value},
                )
        session.commit()
    except Exception:
        session.rollback()
        raise

    return order


def create_order(
    session: sqlalchemy.orm.Session,
    payload: api_models.OrderCreateRequest,
) -> storage_models.Order:
    source = storage_models.IngestionSource.WEBHOOK
    order = storage_models.Order(
        source_order_id=payload.source_order_id,
        status=(
            storage_models.OrderStatus.SCHEDULED
            if payload.scheduled_for is not None
            else storage_models.OrderStatus.RECEIVED
        ),
        scheduled_for=payload.scheduled_for,
        items=[
            storage_models.OrderItem(name=name) for name in payload.items
        ],
    )
    try:
        session.add(order)
        session.flush()
        _add_order_event(
            order,
            "order_received",
            source,
            {"status": order.status.value},
        )
        session.commit()
    except sqlalchemy.exc.IntegrityError as exc:
        session.rollback()
        # TODO: decide if this should be allowd, maybe with RBAC'd overrides.
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_409_CONFLICT,
            detail="An order with this source_order_id already exists",
        ) from exc
    except Exception:
        session.rollback()
        raise
    return order


def dispatch_order(
    session: sqlalchemy.orm.Session,
    order_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> storage_models.DispatchedOrder:
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("now must include a timezone")

    order = session.get(storage_models.Order, order_id)
    if order is None:
        raise fastapi.HTTPException(status_code=404, detail="Order not found")
    if order.status == storage_models.OrderStatus.CANCELLED:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_409_CONFLICT,
            detail="Cancelled orders cannot be dispatched",
        )
    if order.status == storage_models.OrderStatus.SCHEDULED and order.scheduled_for:
        scheduled_for = order.scheduled_for
        if scheduled_for.tzinfo is None or scheduled_for.utcoffset() is None:
            scheduled_for = scheduled_for.replace(tzinfo=timezone.utc)
        if scheduled_for > current_time:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_409_CONFLICT,
                detail="Scheduled orders cannot be dispatched before their scheduled time",
            )

    existing = session.scalars(
        sqlalchemy.select(storage_models.DispatchedOrder).where(
            storage_models.DispatchedOrder.order_id == order_id
        )
    ).one_or_none()
    if existing is not None:
        return existing

    dispatch = storage_models.DispatchedOrder(
        order_id=order.id,
        status=storage_models.DispatchStatus.DISPATCHED,
    )
    order.status = storage_models.OrderStatus.DISPATCHED
    _add_order_event(
        order,
        "order_dispatched",
        None,
        {"status": order.status.value},
    )
    try:
        session.add(dispatch)
        session.commit()
    except Exception:
        session.rollback()
        raise
    return dispatch


def dispatch_due_scheduled_orders(
    session: sqlalchemy.orm.Session,
    *,
    now: datetime | None = None,
) -> list[storage_models.DispatchedOrder]:
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("now must include a timezone")

    statement = (
        sqlalchemy.select(storage_models.Order.id)
        .where(
            storage_models.Order.status == storage_models.OrderStatus.SCHEDULED,
            storage_models.Order.scheduled_for <= current_time,
        )
        .order_by(storage_models.Order.scheduled_for, storage_models.Order.id)
    )
    order_ids = list(session.scalars(statement).all())
    print(f"Found: {len(order_ids)} to dispatch to robot...")
    return [
        dispatch_order(session, order_id, now=current_time)
        for order_id in order_ids
    ]


# TODO: Move outside of this module. This is real
def ingest_polling_response(
    session: sqlalchemy.orm.Session,
    payload: api_models.PollingAPIResponse,
) -> api_models.IngestionBatchResponse:
    source = storage_models.IngestionSource.POLLING_API
    if payload.response != 200:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_502_BAD_GATEWAY,
            detail=f"Polling source returned response {payload.response}",
        )

    try:
        grouped_items: dict[int, list[api_models.PollingOrderItem]] = (
            collections.defaultdict(list)
        )
        for item in payload.data.values():
            grouped_items[item.order].append(item)

        processed_orders = []
        for source_order_number, source_items in grouped_items.items():
            source_order_id = str(source_order_number)
            order = _find_order(session, source_order_id)
            if order is None:
                order = storage_models.Order(
                    source_order_id=source_order_id,
                    status=(
                        storage_models.OrderStatus.CANCELLED
                        if source_items
                        and all(item.status.lower() == "cancelled" for item in source_items)
                        else storage_models.OrderStatus.RECEIVED
                    ),
                    items=[storage_models.OrderItem(name=item.name) for item in source_items],
                )
                session.add(order)
                _add_order_event(
                    order,
                    "order_cancelled"
                    if order.status == storage_models.OrderStatus.CANCELLED
                    else "order_received",
                    source,
                    {"item_count": len(source_items), "status": order.status.value},
                )
            else:
                incoming_names = [item.name for item in source_items]
                if [item.name for item in order.items] != incoming_names:
                    order.items = [
                        storage_models.OrderItem(name=name)
                        for name in incoming_names
                    ]
                    _add_order_event(
                        order,
                        "order_items_updated",
                        source,
                        {"item_count": len(incoming_names)},
                    )
            cancelled = any(
                item.status.lower() == "cancelled" for item in source_items
            )
            if cancelled and order.status != storage_models.OrderStatus.CANCELLED:
                order.status = storage_models.OrderStatus.CANCELLED
                _add_order_event(
                    order,
                    "order_cancelled",
                    source,
                    {"status": order.status.value},
                )
            processed_orders.append(order)
        session.commit()
    except Exception:
        session.rollback()
        raise

    return api_models.IngestionBatchResponse(
        processed_orders=len(processed_orders),
        order_ids=[order.id for order in processed_orders],
    )


def ingest_csv_file(
    session: sqlalchemy.orm.Session,
    content: bytes,
) -> api_models.IngestionBatchResponse:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_400_BAD_REQUEST,
            detail="CSV file must be UTF-8 encoded",
        ) from exc

    reader = csv.DictReader(io.StringIO(text))
    required_headers = {"items", "scheduled_for"}
    if reader.fieldnames is None or not required_headers.issubset(reader.fieldnames):
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"CSV must include columns: {', '.join(sorted(required_headers))}",
        )

    validated_rows = []
    try:
        for row_number, row in enumerate(reader, start=1):
            if None in row or any(value is None for value in row.values()):
                raise fastapi.HTTPException(
                    status_code=fastapi.status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"CSV row {row_number} has an unexpected number of columns",
                )
            csv_payload = api_models.CSVOrderPayload.model_validate(row)
            items = _split_csv_items(csv_payload.items)
            if not items:
                raise fastapi.HTTPException(
                    status_code=fastapi.status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"CSV row {row_number} must contain at least one item",
                )
            validated_rows.append((row_number, csv_payload, items))
    except pydantic.ValidationError as exc:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=exc.errors(include_url=False),
        ) from exc

    if not validated_rows:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="CSV file contains no order rows",
        )

    batch_id = hashlib.sha256(content).hexdigest()
    source = storage_models.IngestionSource.CSV
    order_ids = []
    try:
        for row_number, csv_payload, items in validated_rows:
            source_order_id = f"{batch_id}:{row_number}"
            if _find_order(session, source_order_id) is not None:
                continue

            order = storage_models.Order(
                source_order_id=source_order_id,
                status=(
                    storage_models.OrderStatus.SCHEDULED
                    if csv_payload.scheduled_for is not None
                    else storage_models.OrderStatus.RECEIVED
                ),
                scheduled_for=csv_payload.scheduled_for,
                items=[
                    storage_models.OrderItem(name=name) for name in items
                ],
            )
            session.add(order)
            session.flush()
            _add_order_event(
                order,
                "order_received",
                source,
                {
                    "status": order.status.value,
                    "scheduled_for": (
                        order.scheduled_for.isoformat()
                        if order.scheduled_for is not None
                        else None
                    ),
                },
            )
            order_ids.append(order.id)
        session.commit()
    except Exception:
        session.rollback()
        raise

    return api_models.IngestionBatchResponse(
        processed_orders=len(order_ids), order_ids=order_ids
    )
