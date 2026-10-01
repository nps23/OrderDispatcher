import asyncio
import uvicorn

from src.api import main as api_main

def main():
    fast_api = api_main.build_app()

    server = uvicorn.Server(uvicorn.Config(
        fast_api,
        port=9000,
        access_log=False,
        host="0.0.0.0",
        log_level="info",
        lifespan="on",
    ))

    asyncio.run(server.serve())


if __name__ == "__main__":
    main()
