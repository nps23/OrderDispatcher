import logging
from uuid import UUID

import fastapi
import sqlalchemy
import sqlalchemy.exc
import sqlalchemy.orm

from src.api import models
from src.services import order_ingestion
from src.services import polling_source
from src.storage import database
from src.storage import models as storage_models


logger = logging.getLogger(__name__)


class GraceRouterAPI:

    def __init__(self) -> None:
        self.router = fastapi.APIRouter()
        self._init_routes()

    def _init_routes(self) -> None: 

        self.router.add_api_route(
            path="/status",
            endpoint=self.status,
            methods=["GET"],
            tags=["API"],
        )
        self.router.add_api_route(
            path="/health/database",
            endpoint=self.database_health,
            methods=["GET"],
            tags=["Health"],
        )
        self.router.add_api_route(
            path="/orders/{order_id}",
            endpoint=self.read_order,
            methods=["GET"],
            response_model=models.OrderReadResponse,
            tags=["Orders"],
        )
        self.router.add_api_route(
            path="/orders",
            endpoint=self.list_orders,
            methods=["GET"],
            response_model=list[models.OrderReadResponse],
            tags=["Orders"],
        )
        self.router.add_api_route(
            path="/orders/{order_id}/events",
            endpoint=self.read_order_events,
            methods=["GET"],
            response_model=list[models.OrderEventReadResponse],
            tags=["Orders"],
        )
        self.router.add_api_route(
            path="/orders/{order_id}/dispatch",
            endpoint=self.dispatch_order,
            methods=["POST"],
            response_model=models.DispatchReadResponse,
            tags=["Orders"],
        )
        self.router.add_api_route(
            path="/orders",
            endpoint=self.create_order,
            methods=["POST"],
            response_model=models.OrderReadResponse,
            status_code=fastapi.status.HTTP_201_CREATED,
            tags=["Orders"],
        )
        self.router.add_api_route(
            path="/ingest/csv",
            endpoint=self.ingest_csv,
            methods=["POST"],
            response_model=models.IngestionBatchResponse,
            tags=["Ingestion"],
        )
        self.router.add_api_route(
            path="/polling",
            endpoint=self.poll_orders,
            methods=["GET"],
            response_model=list[models.OrderReadResponse],
            tags=["Orders"],
        )

    def status(self) -> models.BasicResponse:
        return models.BasicResponse(message="Connected to the GraceRouterAPI")

    def read_order(
        self,
        order_id: UUID,
        session: sqlalchemy.orm.Session = fastapi.Depends(database.get_db),
    ) -> storage_models.Order:
        statement = (
            sqlalchemy.select(storage_models.Order)
            .options(sqlalchemy.orm.selectinload(storage_models.Order.items))
            .where(storage_models.Order.id == order_id)
        )
        order = session.scalars(statement).one_or_none()
        if order is None:
            raise fastapi.HTTPException(status_code=404, detail="Order not found")
        return order

    def list_orders(
        self,
        offset: int = fastapi.Query(default=0, ge=0),
        limit: int = fastapi.Query(default=50, ge=1, le=100),
        status: storage_models.OrderStatus | None = None,
        session: sqlalchemy.orm.Session = fastapi.Depends(database.get_db),
    ) -> list[storage_models.Order]:
        statement = sqlalchemy.select(storage_models.Order).options(
            sqlalchemy.orm.selectinload(storage_models.Order.items)
        )
        if status is not None:
            statement = statement.where(storage_models.Order.status == status)
        statement = (
            statement.order_by(
                storage_models.Order.created_at.desc(), storage_models.Order.id
            )
            .offset(offset)
            .limit(limit)
        )
        return list(session.scalars(statement).all())

    def read_order_events(
        self,
        order_id: UUID,
        session: sqlalchemy.orm.Session = fastapi.Depends(database.get_db),
    ) -> list[storage_models.OrderEvent]:
        if session.get(storage_models.Order, order_id) is None:
            raise fastapi.HTTPException(status_code=404, detail="Order not found")
        statement = (
            sqlalchemy.select(storage_models.OrderEvent)
            .where(storage_models.OrderEvent.order_id == order_id)
            .order_by(storage_models.OrderEvent.occurred_at, storage_models.OrderEvent.id)
        )
        return list(session.scalars(statement).all())

    def create_order(
        self,
        payload: models.OrderCreateRequest,
        session: sqlalchemy.orm.Session = fastapi.Depends(database.get_db),
    ) -> storage_models.Order:
        return order_ingestion.create_order(session, payload)

    def dispatch_order(
        self,
        order_id: UUID,
        session: sqlalchemy.orm.Session = fastapi.Depends(database.get_db),
    ) -> storage_models.DispatchedOrder:
        return order_ingestion.dispatch_order(session, order_id)

    def poll_orders(
        self,
        session: sqlalchemy.orm.Session = fastapi.Depends(database.get_db),
    ) -> list[storage_models.Order]:
        return polling_source.poll_orders(session)

    async def ingest_csv(
        self,
        file: fastapi.UploadFile = fastapi.File(...),
        session: sqlalchemy.orm.Session = fastapi.Depends(database.get_db),
    ) -> models.IngestionBatchResponse:
        content = await file.read()
        return order_ingestion.ingest_csv_file(session, content)

    def database_health(self) -> models.BasicResponse:
        logger.info("Running DataBaseHealth.")
        try:
            with database.get_engine().connect() as connection:
                connection.execute(sqlalchemy.text("SELECT 1"))
        except sqlalchemy.exc.SQLAlchemyError as exc:
            logger.exception("Database health check failed")
            raise fastapi.HTTPException(
                status_code=503, detail="Database is unavailable"
            ) from exc

        logger.info("Running DataBaseHealth check complete.")
        return models.BasicResponse(message="Database connection is healthy")
