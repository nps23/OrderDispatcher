from datetime import datetime
from decimal import Decimal
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
    first_name: str
    last_name: str
    items: str
    notes: str = ""
    tomorrow: bool
    meal: storage_models.Meal


class OrderItemCreateRequest(sqlmodel.SQLModel):
    source_item_id: str | None = sqlmodel.Field(default=None, max_length=255)
    name: str = sqlmodel.Field(min_length=1, max_length=255)
    quantity: int = sqlmodel.Field(default=1, gt=0)
    unit_price: Decimal | None = sqlmodel.Field(default=None, ge=0)
    category: str | None = sqlmodel.Field(default=None, max_length=100)
    special_instructions: str | None = sqlmodel.Field(default=None, max_length=1000)


class OrderCreateRequest(sqlmodel.SQLModel):
    source_order_id: str | None = sqlmodel.Field(default=None, max_length=255)
    order_source: str | None = sqlmodel.Field(default=None, max_length=100)
    restaurant: str | None = sqlmodel.Field(default=None, max_length=255)
    first_name: str | None = sqlmodel.Field(default=None, max_length=100)
    last_name: str | None = sqlmodel.Field(default=None, max_length=100)
    total: Decimal | None = sqlmodel.Field(default=None, ge=0)
    order_type: storage_models.OrderType = storage_models.OrderType.REALTIME
    scheduled_for: datetime | None = None
    notes: str | None = None
    items: list[OrderItemCreateRequest] = sqlmodel.Field(min_length=1)


class OrderItemReadResponse(sqlmodel.SQLModel):
    model_config = pydantic.ConfigDict(from_attributes=True)

    id: UUID
    source_item_id: str | None
    name: str
    quantity: int
    unit_price: Decimal | None
    category: str | None
    special_instructions: str | None


class OrderReadResponse(sqlmodel.SQLModel):
    model_config = pydantic.ConfigDict(from_attributes=True)

    id: UUID
    source_order_id: str | None
    order_source: str | None
    restaurant: str | None
    first_name: str | None
    last_name: str | None
    total: Decimal | None
    order_type: storage_models.OrderType
    status: storage_models.OrderStatus
    scheduled_for: datetime | None
    notes: str | None
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
