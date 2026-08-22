FROM python:3.12-slim

ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /usr/src/app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --locked

COPY . .