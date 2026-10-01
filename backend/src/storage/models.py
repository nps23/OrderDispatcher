import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

import sqlalchemy
import sqlmodel


Base = sqlmodel.SQLModel


class IngestionSource(enum.StrEnum):
    WEBHOOK = "webhook"
    POLLING_API = "polling_api"
    CSV = "csv"


class OrderType(enum.StrEnum):
    REALTIME = "realtime"
    SCHEDULED = "scheduled"


class OrderStatus(enum.StrEnum):
    RECEIVED = "received"
    SCHEDULED = "scheduled"
    DISPATCHED = "dispatched"
    CANCELLED = "cancelled"


class DispatchStatus(enum.StrEnum):
    DISPATCHED = "dispatched"


class Meal(enum.StrEnum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"


def _enum_values(enum_class: type[enum.StrEnum]) -> list[str]:
    return [member.value for member in enum_class]


def _enum_column(
    enum_class: type[enum.StrEnum], name: str, **kwargs: Any
) -> sqlalchemy.Column:
    return sqlalchemy.Column(
        sqlalchemy.Enum(
            enum_class,
            name=name,
            native_enum=False,
            create_constraint=True,
            values_callable=_enum_values,
        ),
        **kwargs,
    )


class Order(sqlmodel.SQLModel, table=True):
    __tablename__ = "orders"
    __table_args__ = (
        sqlalchemy.UniqueConstraint("source_order_id", name="uq_orders_source_external_id"),
        sqlalchemy.Index("ix_orders_status_created_at", "status", "created_at"),
        sqlalchemy.Index("ix_orders_scheduled_for", "scheduled_for"),
    )

    id: uuid.UUID = sqlmodel.Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.types.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
        )
    )
    source_order_id: str | None = sqlmodel.Field(
        default=None, sa_column=sqlalchemy.Column(sqlalchemy.String(255), nullable=True)
    )
    order_source: str | None = sqlmodel.Field(
        default=None, sa_column=sqlalchemy.Column(sqlalchemy.String(100), nullable=True)
    )
    restaurant: str | None = sqlmodel.Field(
        default=None, sa_column=sqlalchemy.Column(sqlalchemy.String(255), nullable=True)
    )
    first_name: str | None = sqlmodel.Field(
        default=None, sa_column=sqlalchemy.Column(sqlalchemy.String(100), nullable=True)
    )
    last_name: str | None = sqlmodel.Field(
        default=None, sa_column=sqlalchemy.Column(sqlalchemy.String(100), nullable=True)
    )
    total: Decimal | None = sqlmodel.Field(
        default=None, sa_column=sqlalchemy.Column(sqlalchemy.Numeric(10, 2), nullable=True)
    )
    order_type: OrderType = sqlmodel.Field(
        sa_column=_enum_column(OrderType, "order_type", nullable=False)
    )
    status: OrderStatus = sqlmodel.Field(
        sa_column=_enum_column(
            OrderStatus, "order_status", nullable=False, default=OrderStatus.RECEIVED
        )
    )
    scheduled_for: datetime | None = sqlmodel.Field(
        default=None, sa_column=sqlalchemy.Column(sqlalchemy.DateTime(timezone=True), nullable=True)
    )
    notes: str | None = sqlmodel.Field(
        default=None, sa_column=sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    )
    created_at: datetime = sqlmodel.Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=True),
            nullable=False,
            server_default=sqlalchemy.func.now(),
        )
    )
    updated_at: datetime = sqlmodel.Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=True),
            nullable=False,
            server_default=sqlalchemy.func.now(),
            onupdate=sqlalchemy.func.now(),
        )
    )
    items: list["OrderItem"] = sqlmodel.Relationship(
        back_populates="order",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    events: list["OrderEvent"] = sqlmodel.Relationship(
        back_populates="order",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "OrderEvent.occurred_at",
        },
    )
    dispatch: "DispatchedOrder" = sqlmodel.Relationship(
        back_populates="order",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"},
    )


class DispatchedOrder(sqlmodel.SQLModel, table=True):
    __tablename__ = "dispatched_orders"

    id: uuid.UUID = sqlmodel.Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.types.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
        )
    )
    order_id: uuid.UUID = sqlmodel.Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.types.Uuid(as_uuid=True),
            sqlalchemy.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        )
    )
    status: DispatchStatus = sqlmodel.Field(
        sa_column=_enum_column(DispatchStatus, "dispatch_status", nullable=False)
    )
    dispatched_at: datetime = sqlmodel.Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=True),
            nullable=False,
            server_default=sqlalchemy.func.now(),
        )
    )

    order: "Order" = sqlmodel.Relationship(back_populates="dispatch")
class OrderItem(sqlmodel.SQLModel, table=True):
    __tablename__ = "order_items"
    __table_args__ = (
        sqlalchemy.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        sqlalchemy.CheckConstraint(
            "unit_price IS NULL OR unit_price >= 0", name="ck_order_items_price_nonnegative"
        ),
    )

    id: uuid.UUID = sqlmodel.Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.types.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
        )
    )
    source_item_id: str | None = sqlmodel.Field(
        default=None,
        sa_column=sqlalchemy.Column(sqlalchemy.String(255), nullable=True, index=True),
    )
    order_id: uuid.UUID = sqlmodel.Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.types.Uuid(as_uuid=True),
            sqlalchemy.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    name: str = sqlmodel.Field(sa_column=sqlalchemy.Column(sqlalchemy.String(255), nullable=False))
    quantity: int = sqlmodel.Field(
        default=1,
        sa_column=sqlalchemy.Column(sqlalchemy.Integer, nullable=False, default=1),
    )
    category: str | None = sqlmodel.Field(
        default=None, sa_column=sqlalchemy.Column(sqlalchemy.String(100), nullable=True)
    )
    unit_price: Decimal | None = sqlmodel.Field(
        default=None, sa_column=sqlalchemy.Column(sqlalchemy.Numeric(10, 2), nullable=True)
    )
    special_instructions: str | None = sqlmodel.Field(
        default=None, sa_column=sqlalchemy.Column(sqlalchemy.String(1000), nullable=True)
    )

    order: "Order" = sqlmodel.Relationship(back_populates="items")


class OrderEvent(sqlmodel.SQLModel, table=True):
    __tablename__ = "order_events"
    __table_args__ = (
        sqlalchemy.Index("ix_order_events_order_occurred_at", "order_id", "occurred_at"),
    )

    id: uuid.UUID = sqlmodel.Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.types.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
        )
    )
    order_id: uuid.UUID = sqlmodel.Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.types.Uuid(as_uuid=True),
            sqlalchemy.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        )
    )
    event_type: str = sqlmodel.Field(
        sa_column=sqlalchemy.Column(sqlalchemy.String(100), nullable=False)
    )
    ingestion_source: IngestionSource | None = sqlmodel.Field(
        default=None,
        sa_column=_enum_column(IngestionSource, "order_event_source", nullable=True),
    )
    details: dict[str, Any] = sqlmodel.Field(
        default_factory=dict, sa_column=sqlalchemy.Column(sqlalchemy.JSON, nullable=False, default=dict)
    )
    occurred_at: datetime = sqlmodel.Field(
        sa_column=sqlalchemy.Column(
            sqlalchemy.DateTime(timezone=True),
            nullable=False,
            server_default=sqlalchemy.func.now(),
        )
    )

    order: "Order" = sqlmodel.Relationship(back_populates="events")
