from contextlib import asynccontextmanager
from typing import AsyncGenerator

import fastapi
import fastapi.middleware.cors

from src.api import graceroute_api
from src.storage import database


def build_app():

    @asynccontextmanager
    async def lifespan(app: fastapi.FastAPI) -> AsyncGenerator[None, None]:
        # TODO: decouple for a prod deployment, fine for prototype
        database.create_db_and_tables()
        yield

    app = fastapi.FastAPI(
        lifespan=lifespan,
        debug=True,
        title="GraceRouterAPI",
        version="0.0.0",
    )

    core_api = graceroute_api.GraceRouterAPI()
    app.include_router(core_api.router)

    app.add_middleware(
        fastapi.middleware.cors.CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"]
    )

    return app