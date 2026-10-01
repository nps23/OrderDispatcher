import os
from collections.abc import Generator

import sqlalchemy
import sqlalchemy.orm

from src.storage import models as storage_models


def _get_database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://order_dispatcher:order_dispatcher@localhost:5432/order_dispatcher",
    )

_engine = sqlalchemy.create_engine(_get_database_url(), pool_pre_ping=True)
_local_session = sqlalchemy.orm.sessionmaker(
    bind=_engine, autoflush=False, expire_on_commit=False
)


def create_db_and_tables() -> None:
    storage_models.Base.metadata.create_all(_engine)


def get_db() -> Generator[sqlalchemy.orm.Session, None, None]:
    with _local_session() as session:
        yield session

def get_engine():
    return _engine
