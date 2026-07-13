FROM python:3.14-alpine

# Install netcat for health checks, Docker CLI for testcontainers, and redis-cli for cleanup
RUN apk add --no-cache netcat-openbsd docker-cli redis

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set WORKDIR to project root
WORKDIR /FixedWindowCounter/app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache

# Copy the app code
COPY . /FixedWindowCounter

# Set PYTHONPATH
ENV PYTHONPATH="/FixedWindowCounter:/FixedWindowCounter/app"

# Copy entrypoint script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]