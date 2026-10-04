FROM node:22-alpine AS assets

WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY app/static/css/input.css app/static/css/input.css
COPY app/web/templates ./app/web/templates
COPY scripts ./scripts
RUN npm run build

FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

RUN pip install --no-cache-dir uv==0.10.4 \
    && useradd --system --uid 10001 --create-home appuser

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
COPY --from=assets /build/app/static/ ./app/static/

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
