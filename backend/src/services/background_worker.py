import asyncio
import logging

from src.services import order_ingestion
from src.services import polling_source
from src.storage import database


logger = logging.getLogger(__name__)
POLL_INTERVAL_SECONDS = 30


def _poll_source() -> None:
    with database.new_session() as session:
        polling_source.poll_orders(session)


def _dispatch_due_orders() -> None:
    with database.new_session() as session:
        dispatched = order_ingestion.dispatch_due_scheduled_orders(session)
        if dispatched:
            logger.info("Dispatched %d scheduled orders", len(dispatched))


async def run_background_worker() -> None:
    """
    Spin up a background thread to handle:
        - Polling of an exteral service
        - Dispatching orders to the robot


    """
    
    while True:
        try:
            await asyncio.to_thread(_poll_source)
        except Exception:
            logger.exception("Background polling cycle failed")

        try:
            await asyncio.to_thread(_dispatch_due_orders)
        except Exception:
            logger.exception("Scheduled order dispatch cycle failed")

        await asyncio.sleep(POLL_INTERVAL_SECONDS)
