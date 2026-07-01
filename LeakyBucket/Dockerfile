FROM python:3.14-alpine

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /LeakyBucket/app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-cache

COPY . /LeakyBucket
