FROM python:3.12-slim

ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /usr/src/app


RUN apt-get update && \
    apt-get install --assume-yes git libltdl7 libkrb5-3 libgssapi-krb5-2 && \
    rm --recursive --force /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/
COPY pyproject.toml uv.lock ./
RUN uv sync --locked

COPY . .