# Order Dispatcher

A prototype for a basic order ingest and dispatch system.

All three inputs are normalized into the `Order` model. CSV rows with
`tomorrow=true` are scheduled for the following day at 09:00 (breakfast),
12:00 (lunch), or 18:00 (dinner), using UTC. `OrderEvent` is the append-only
order history exposed by `GET /orders/{order_id}/events`.

Robot dispatch is intentionally a small synchronous handoff for this
prototype: `POST /orders/{order_id}/dispatch` creates one record in
`dispatched_orders`, changes the order status to `dispatched`, and records an
audit event. It does not run a backend worker or contact a robot.

## Backend

The project runs a local Postgres database, intended to be run out of a Docker container.
The backend can run directly to take advantage of FastAPI's hot reload capabilities, or separately in a Docker container. For local development, you need Docker Engine with the Docker Compose v2 plugin and
[uv](https://docs.astral.sh/uv/).

### Run the backend locally with hot reload

From the repository root, start PostgreSQL and wait for its health check:

```bash
docker compose -f backend/compose.yaml up -d --wait db
```

Docker creates the local `order_dispatcher` database and user. When the API
starts, it creates any missing tables from the SQLModel definitions. Then,
from `backend/`, sync the Python dependencies and start the API with reload:

```bash
uv sync --locked
DATABASE_URL='postgresql+psycopg://order_dispatcher:order_dispatcher@localhost:5432/order_dispatcher' \
  uv run uvicorn src.api.main:build_app --factory --reload --host 0.0.0.0 --port 9000
```

The API is at `http://localhost:9000/docs`; the database health check is at
`http://localhost:9000/health/database`.

### Test the CSV ingest endpoints

The test CLI sends sample data to a running backend. Upload one CSV through the
same HTTP endpoint used by clients:

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

The simulator posts each burst to `POST /orders`, sleeps between bursts, and
continues until interrupted. Set `--sample` to use another webhook JSONL
fixture. The CLI targets the local backend at `http://localhost:9000`.

### Simulating API polling
There is a `/polling` endpoint that, for now, just returns data from a json fixture.
The implementation of this endpoint could be updated in the future to poll from a real external service.


Once the backend is running, API documentation can be found at the `/docs` endpoint.

Stop PostgreSQL from the repository root with
`docker compose -f backend/compose.yaml down`. To start over with a fresh
database, add `--volumes` to that command, which will wipe the database.


Docker Compose v2 is required. Check whether it is installed with:

```bash
docker compose version
```

## Follow up work
1. Build a frontend component with CSV upload flow and deprecate CLI.


On Linux, if that command is unavailable, install the plugin:

```bash
sudo apt update
sudo apt install docker-compose-v2
```
