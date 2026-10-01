import os
from pathlib import Path

import sqlalchemy
import sqlalchemy.orm

from scripts import polling as polling_mock
from src.api import models
from src.services import order_ingestion
from src.storage import models as storage_models


DEFAULT_SAMPLE_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "api_responses.jsonl"
)


def poll_orders(
    session: sqlalchemy.orm.Session,
    *,
    response_limit: int | None = None,
) -> list[storage_models.Order]:
    configured_path = os.getenv("POLLING_API_FILE")
    # TODO: This is "fake" implementation for MVP that just rips data out of the sample response.json
    sample_path = Path(configured_path) if configured_path else DEFAULT_SAMPLE_PATH
    responses = polling_mock.get_polling_segment(
        sample_path,
        limit=response_limit,
    )

    combined_data: dict[str, models.PollingOrderItem] = {}
    for response in responses:
        # TODO: We need to better handle partially ingested orders
        if response.response == 200:
            order_ingestion.ingest_polling_response(session, response)
        combined_data.update(response.data)

    if not combined_data:
        return []
    result = order_ingestion.ingest_polling_response(
        session, models.PollingAPIResponse(response=200, data=combined_data)
    )
    if not result.order_ids:
        return []
    statement = (
        sqlalchemy.select(storage_models.Order)
        .options(sqlalchemy.orm.selectinload(storage_models.Order.items))
        .where(storage_models.Order.id.in_(result.order_ids))
        .order_by(storage_models.Order.created_at, storage_models.Order.id)
    )
    print("Found poll results, injecting into database...")
    return list(session.scalars(statement).all())
