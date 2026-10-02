# Order Dispatcher

A prototype order ingestion and dispatch system for a robot that combines webhook, polling API, and CSV sources.
Orders from the different pipelines are normalized into the `Order` model and their changes are recorded as order events.
`POST /orders/{order_id}/dispatch` marks an eligible order as dispatched in the database.
Once an order is dispatched, we can presume it went to the robot for preperation.
Scheduled orders cannot be dispatched before their scheduled time.
A background worker checks for due scheduled orders every 30 seconds and records each dispatch and its audit event.

## Architecture and UI

![Order dispatcher architecture](./inital_arch.drawio.png)

![Orders page](./orders.png)

![Order history page](./orders_event.png)

## Prerequisites

For local development, install [Docker Engine](https://docs.docker.com/engine/install/), [uv](https://docs.astral.sh/uv/getting-started/installation/), and [Node.js with npm](https://nodejs.org/en/download/). Docker Compose is not required.

## Database

PostgreSQL runs from the official `postgres:17-alpine` Docker image. Create a Docker network so the database and optional backend container can communicate:

```bash
docker network create order-dispatcher-network
```

Then start the database from the repository root:

```bash
docker run -d \
  --name order-dispatcher-db \
  --network order-dispatcher-network \
  --network-alias db \
  --health-cmd="pg_isready -U order_dispatcher -d order_dispatcher" \
  --health-interval=3s \
  --health-timeout=3s \
  --health-retries=10 \
  -e POSTGRES_DB=order_dispatcher \
  -e POSTGRES_USER=order_dispatcher \
  -e POSTGRES_PASSWORD=order_dispatcher \
  -p 5432:5432 \
  -v order_dispatcher_data:/var/lib/postgresql/data \
  postgres:17-alpine
```

The database is reachable at `localhost:5432` from your computer and at `db:5432` from containers on the Docker network. Check that it is ready before starting the API:

```bash
docker inspect --format='{{.State.Health.Status}}' order-dispatcher-db
```

Wait for the command to report `healthy`. The API creates missing tables from the SQLModel definitions when it starts. Its database health check is available at `http://localhost:9000/health/database` once the API is running.

Stop the database while keeping its data with `docker stop order-dispatcher-db`

To completely reset the local database, remove the container and its volume, then repeat the `docker run` command above:

```bash
docker rm -f order-dispatcher-db
docker volume rm order_dispatcher_data
```

Removing the volume permanently deletes the local database contents. The API's `create_all` creates missing tables but does not migrate or remove columns in an existing database.

## Backend

### Run locally with hot reload

Start PostgreSQL using the [database instructions](#database).
From the repository root, sync backend dependencies and start the API with hot reload:

```bash
cd backend
uv sync --locked
DATABASE_URL='postgresql+psycopg://order_dispatcher:order_dispatcher@localhost:5432/order_dispatcher' \
  uv run uvicorn src.api.main:build_app --factory --reload --host 0.0.0.0 --port 9000
```

The API documentation is available at `http://localhost:9000/docs`.

### Optionally run the backend in Docker

You can run the API locally with hot reload as above while using the database container. Alternatively, build and run the backend image from the repository root:

```bash
docker build -f backend/Dockerfile -t order-dispatcher-backend .
docker run --rm \
  --name order-dispatcher-backend \
  --network order-dispatcher-network \
  -e DATABASE_URL='******db:5432/order_dispatcher' \
  -p 9000:9000 \
  order-dispatcher-backend
```

The API documentation is available at `http://localhost:9000/docs`.
Stop the backend container with `Ctrl+C`. The database continues running until stopped separately.

### Background workers

The polling worker reads up to five responses from `data/api_responses.jsonl` at startup and advances through the fixture in batches of five every 30 seconds.
The worker also dispatches scheduled orders when their scheduled time has arrived.

## Ingestion examples

### Upload a CSV

The required columns for CSV uploads are `items`, `tomorrow`, and `meal`.
Rows with `tomorrow=true` are scheduled 24 hours after upload whereas rows with `tomorrow=false` are received immediately.
With the backend running, execute the upload CLI from `backend/`:

```bash
uv run python -m scripts.pipeline_cli upload-csv <path_to_csv>
```

### Simulate webhook traffic

The webhook simulator posts bursts of sample orders to `POST /ingest/webhook` until interrupted.
Run it from `backend/` while the API is running:

```bash
uv run python -m scripts.pipeline_cli simulate-bursts \
  --burst-size 25 \
  --sleep-seconds 2
```

Use `--sample <path_to_jsonl>` to choose a different webhook fixture.

## Frontend

The React frontend is in `ui/` and uses Vite for scaffolding.
Start the backend first so the UI can load orders from `http://localhost:9000`.
From the repository root, install frontend dependencies and start the development server:

```bash
cd ui
npm ci
npm run dev
```

Open the local URL printed by Vite, usually `http://localhost:5173/orders`.
Order history pages are available at `/orders/{order_id}`.
To check the production build and lint, run these commands from `ui/`:

```bash
npm run build
npm run lint
```

## Follow-up work

### Tests

Add backend service and API tests, UI component tests, and Playwright flows for listing, filtering, order history, dispatch, and failure cases.

### Security and RBAC controls
- When DB is deployed, we need sectuiry and an Vault-like for for the API to authenticate.
- Should introduce RBA controls to ensure not anyone can dispatch to the robot.

### Robot lifecycle

Define order and robot state transitions before adding robot endpoints.
Add a dispatch queue and distinguish queued orders from orders accepted by the robot or being assembled.
Consider moving workers into separate services when deployment needs require it.

### Logging and metrics

Add structured logs and trace or correlation IDs, potentially using `structlog`.
Instrument production metrics with the chosen monitoring platform.

### Frontend API client

Add a typed API module to centralize request URLs, response and error handling, and shared order types.

### UI organization

Extract the orders list and dispatch actions into focused components.
