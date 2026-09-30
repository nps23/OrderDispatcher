from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import AsyncGenerator


from src.api.graceroute_api import GraceRouterAPI


def build_app():

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        yield

    app = FastAPI(
        lifespan=lifespan,
        debug=True,
        title="GraceRouterAPI",
        version="0.0.0",
    )

    core_api = GraceRouterAPI()
    app.include_router(core_api.router)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"]
    )

    return app