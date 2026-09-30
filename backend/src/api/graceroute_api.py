from fastapi import APIRouter
from src.api import models


class GraceRouterAPI:

    def __init__(self) -> None:
        self.router = APIRouter()
        self._init_routes()

    def _init_routes(self) -> None: 

        self.router.add_api_route(
            path="/status",
            endpoint=self.status,
            methods=["GET"],
            tags=["API"],
        )

    async def status(self) -> models.BasicResponse:
        return models.BasicResponse(message="Connected to the GraceRouterAPI")

    

