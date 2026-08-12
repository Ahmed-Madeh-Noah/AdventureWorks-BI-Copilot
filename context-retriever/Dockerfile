FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/

RUN apt-get update && \
    apt-get install -y git libltdl7 libkrb5-3 libgssapi-krb5-2 && \
    rm -rf /var/lib/apt/lists/*


WORKDIR /usr/src/app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked

COPY . .

ENTRYPOINT [ "uv", "run", "-m" , "fastapi", "run"]