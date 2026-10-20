FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    OUTPUT_DIR=/app/output \
    DATABASE_PATH=/app/data/books.db

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev

COPY . .
COPY scrapyd.conf /etc/scrapyd/scrapyd.conf

RUN chmod +x docker-entrypoint.sh

EXPOSE 6800

HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
    CMD curl -fsS http://localhost:6800/daemonstatus.json || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
