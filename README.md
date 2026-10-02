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

For local development, install Docker Engine with Docker Compose v2, [uv](https://docs.astral.sh/uv/), and Node.js with npm.

## Database

PostgreSQL runs in Docker using `backend/compose.yaml`.
From the repository root, start the database and wait for its health check:

```bash
docker compose -f backend/compose.yaml up -d --wait db
```

Compose creates the local `order_dispatcher` database and user.
The API creates missing tables from the SQLModel definitions when it starts.
The database health check is available at `http://localhost:9000/health/database` once the API is running.

Stop the database from the repository root with:

```bash
docker compose -f backend/compose.yaml down
```

To completely reset the local database, remove the Docker volume and start the database again:

```bash
docker compose -f backend/compose.yaml down --volumes
docker compose -f backend/compose.yaml up -d --wait db
```

Removing the volume permanently deletes the local database contents.
`create_all` creates missing tables but does not migrate or remove columns in an existing database.

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

### Run the backend and database in Docker

From the repository root, build and start the backend and PostgreSQL together:

```bash
docker compose -f backend/compose.yaml up --build --wait
```

The API documentation is available at `http://localhost:9000/docs`.
Stop both containers with `docker compose -f backend/compose.yaml down`.

### Background workers

The polling worker reads up to five responses from `data/api_responses.jsonl` at startup and advances through the fixture in batches of five every 30 seconds.
The worker also dispatches scheduled orders when their scheduled time has arrived.

## Ingestion examples

### Upload a CSV

The CSV uploader accepts the Homework survey columns and ignores additional columns.
The required columns are `items`, `tomorrow`, and `meal`.
Rows with `tomorrow=true` are scheduled 24 hours after upload; rows with `tomorrow=false` are received immediately.
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
