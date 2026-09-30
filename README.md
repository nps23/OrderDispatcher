# Order Dispatcher

A prototype for a basic order ingest and dispatch system.

## Backend

Commands below assume [uv](https://docs.astral.sh/uv/) is installed. Run them
from the backend directory:

```bash
cd backend
```

### Run locally

Install the dependencies declared in `pyproject.toml` and locked in `uv.lock`:

```bash
uv sync --locked
```

Start the development server with hot reload:

```bash
uv run uvicorn src.api.main:build_app --factory --reload --host 0.0.0.0 --port 9000
```

Or start the app with the launcher (without hot reload):

```bash
uv run python run.py
```

The API listens on port 9000.

### Run with Docker

Build and run the image from the backend directory:

```bash
docker build -t order-dispatcher .
docker run --rm -p 9000:9000 order-dispatcher
```

The container listens on port 9000. If Docker reports permission denied while
connecting to its daemon, ensure Docker is running and that your user has
permission to access it.

### Dependency updates

Edit the dependencies in `backend/pyproject.toml`, then regenerate and commit
the lockfile:

```bash
uv lock
uv sync
```
