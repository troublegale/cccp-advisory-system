FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml .
RUN uv sync --no-dev

COPY app/ app/
COPY alembic.ini .
COPY alembic/ alembic/
COPY scripts/ scripts/

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
