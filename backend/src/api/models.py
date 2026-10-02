from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

import pydantic
import sqlmodel

from src.storage import models as storage_models


class BasicResponse(sqlmodel.SQLModel):
    message: str


class WebhookEvent(sqlmodel.SQLModel):
    order_id: UUID
    order_source: str
    restaurant: str
    first_name: str
    last_name: str
    total: Decimal = sqlmodel.Field(ge=0)
    items: list[str]
    notes: str = ""
    update: list[str] | None = None


class PollingOrderItem(sqlmodel.SQLModel):
    order: int
    name: str
    category: str
    price: Decimal = sqlmodel.Field(ge=0)
    status: str


class PollingAPIResponse(sqlmodel.SQLModel):
    response: int
    data: dict[str, PollingOrderItem] = sqlmodel.Field(default_factory=dict)
    error: str | None = None


class CSVOrderPayload(sqlmodel.SQLModel):
    items: str
    tomorrow: bool
    meal: Literal["breakfast", "lunch", "dinner"]


class OrderCreateRequest(sqlmodel.SQLModel):
    source_order_id: str = sqlmodel.Field(min_length=1, max_length=255)
    scheduled_for: datetime | None = None
    items: list[str] = sqlmodel.Field(min_length=1)

    @pydantic.field_validator("scheduled_for")
    @classmethod
    def schedule_must_include_timezone(
        cls, value: datetime | None
    ) -> datetime | None:
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError("scheduled_for must include a timezone")
        return value

class OrderItemReadResponse(sqlmodel.SQLModel):
    model_config = pydantic.ConfigDict(from_attributes=True)

    id: UUID
    name: str


class OrderReadResponse(sqlmodel.SQLModel):
    model_config = pydantic.ConfigDict(from_attributes=True)

    id: UUID
    source_order_id: str
    status: storage_models.OrderStatus
    scheduled_for: datetime | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemReadResponse]


class OrderEventReadResponse(sqlmodel.SQLModel):
    model_config = pydantic.ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    ingestion_source: storage_models.IngestionSource | None
    details: dict[str, object]
    occurred_at: datetime


class DispatchReadResponse(sqlmodel.SQLModel):
    model_config = pydantic.ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    status: storage_models.DispatchStatus
    dispatched_at: datetime


class IngestionBatchResponse(sqlmodel.SQLModel):
    processed_orders: int
    order_ids: list[UUID]
