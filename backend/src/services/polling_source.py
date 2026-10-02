import logging
import os
from pathlib import Path

import sqlalchemy
import sqlalchemy.orm

from scripts import polling as polling_mock
from src.api import models
from src.services import order_ingestion
from src.storage import models as storage_models

logger = logging.getLogger(__name__)
POLL_BATCH_SIZE = 5


DEFAULT_SAMPLE_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "api_responses.jsonl"
)


def create_poller() -> polling_mock.PollingFixture:
    configured_path = os.getenv("POLLING_API_FILE")
    sample_path = Path(configured_path) if configured_path else DEFAULT_SAMPLE_PATH
    return polling_mock.PollingFixture(sample_path, batch_size=POLL_BATCH_SIZE)


def poll_orders(
    session: sqlalchemy.orm.Session,
    poller: polling_mock.PollingFixture,
) -> list[storage_models.Order]:
    responses = poller.poll()

    combined_data: dict[str, models.PollingOrderItem] = {}
    for response in responses:
        if response.response != 200:
            logger.warning(
                "Polling source returned response %d: %s",
                response.response,
                response.error or "no error details",
            )
        combined_data.update(response.data)

    if not combined_data:
        return []
    result = order_ingestion.ingest_polling_response(
        session,
        models.PollingAPIResponse(response=200, data=combined_data),
    )
    if not result.order_ids:
        return []

    statement = (
        sqlalchemy.select(storage_models.Order)
        .options(sqlalchemy.orm.selectinload(storage_models.Order.items))
        .where(storage_models.Order.id.in_(result.order_ids))
        .order_by(storage_models.Order.created_at, storage_models.Order.id)
    )
    return list(session.scalars(statement).all())
