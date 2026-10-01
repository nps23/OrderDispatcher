FROM ghcr.io/astral-sh/uv:0.12.21 AS uv

FROM python:3.12-slim

COPY --from=uv /uv /uvx /bin/

WORKDIR /app

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY backend/ ./
COPY data/api_responses.jsonl /data/api_responses.jsonl

EXPOSE 9000

CMD ["uv", "run", "--no-sync", "python", "run.py"]
