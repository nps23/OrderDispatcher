# Order Dispatcher

A prototype for a basic order ingest and dispatch system.

All three inputs are normalized into the `Order` model.
Robot dispatch is intentionally a small handoff for this prototype: `POST /orders/{order_id}/dispatch` dispatches an eligible order immediately.
Scheduled orders cannot be dispatched before their timestamp.
A backend worker also checks for due scheduled orders every 30 seconds, creates one record in `dispatched_orders`, changes each order status to `dispatched`, and records an audit event.

## Backend

The project runs a local Postgres database, intended to be run out of a Docker container.
The backend can run directly to take advantage of FastAPI's hot reload capabilities, or separately in a Docker container.
For local development, you need Docker Engine with the Docker Compose v2 plugin and [uv](https://docs.astral.sh/uv/).

### Run the backend locally with hot reload

From the repository root, start PostgreSQL and wait for its health check:

```bash
docker compose -f backend/compose.yaml up -d --wait db
```

Docker creates the local `order_dispatcher` database and user.
When the API starts, it creates any missing tables from the SQLModel definitions.
Then, from `backend/`, sync the Python dependencies and start the API with reload:

```bash
uv sync --locked
DATABASE_URL='postgresql+psycopg://order_dispatcher:order_dispatcher@localhost:5432/order_dispatcher' \
  uv run uvicorn src.api.main:build_app --factory --reload --host 0.0.0.0 --port 9000
```

`create_all` does not migrate or remove columns in an existing database.
If you are using a disposable development database with the old schema, back up anything you need, then recreate the database volume before starting the new backend:

```bash
docker compose -f backend/compose.yaml down --volumes
docker compose -f backend/compose.yaml up -d --wait db
```

The API is at `http://localhost:9000/docs`; the database health check is at `http://localhost:9000/health/database`.

The backend polls `data/api_responses.jsonl` immediately at startup and then every 30 seconds.
It also dispatches scheduled orders when their `scheduled_for` timestamp arrives.
CSV timestamps must use ISO 8601 with an explicit timezone, for example `2030-10-01T09:00:00-04:00`.

To run the backend and database in Docker, from the repository root use:

```bash
docker compose -f backend/compose.yaml up --build --wait
```

The API is then available at `http://localhost:9000/docs`.

### Test the CSV ingest endpoints

The test CLI sends sample data to a running backend.
Upload one CSV through the same HTTP endpoint used by clients:

```bash
uv run python -m scripts.pipeline_cli upload-csv ../data/orders_1.csv
```

### Simulating real webhook traffic

To continuously simulate bursty webhook-like order traffic, run:

```bash
uv run python -m scripts.pipeline_cli simulate-bursts \
  --burst-size 25 \
  --sleep-seconds 2
```

The simulator posts each burst to `POST /ingest/webhook`, sleeps between bursts, and continues until interrupted.
Set `--sample` to use another webhook JSONL fixture.
The CLI targets the local backend at `http://localhost:9000`.

### Background polling
The backend reads `data/api_responses.jsonl` at startup and polls the fixture again every 30 seconds.
Set `POLLING_API_FILE` to use another JSONL fixture.
There is no public polling endpoint.

Once the backend is running, API documentation can be found at the `/docs` endpoint.

Stop PostgreSQL from the repository root with `docker compose -f backend/compose.yaml down`.
To start over with a fresh database, add `--volumes` to that command, which will wipe the database.

Docker Compose v2 is required.
Check whether it is installed with:

```bash
docker compose version
```

On Linux, you can install the plugin via:

```bash
sudo apt update
sudo apt install docker-compose-v2
```

## Follow up work (roughtly in priority order)

Tests: Start with backend service and API tests, then UI component tests, then a small number of Playwright or similar flows for list/filter, order history, dispatch, and failure states.

Robot model: Define the states and allowed transitions before adding endpoints.
In particular, distinguish queued for dispatch from accepted by the robot / being assembled.
For now, we keep the MVP worker in-process or as a separate local process.
But we may explore microservicing one the concurrency and reliability needs of the robot are unknown.
Make robot callbacks idempotent and associate them with a dispatch ID.

Logging and metrics: Structured logs and trace/correlation IDs.
Probably can start with something like `structlog` for the backend.

Frontend API wrappers: Add a typed API module before the UI grows further.
It can centralize URLs, response/error handling, and order/event types.

UI organization: Extract the orders list and dispatch actions.
