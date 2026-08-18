FROM mcr.microsoft.com/mssql/server:2025-latest

WORKDIR /usr/config

USER root
RUN apt-get update && \
    apt-get install --assume-yes curl && \
    rm --recursive --force /var/lib/apt/lists/*
USER mssql

RUN curl --location --remote-name https://github.com/Microsoft/sql-server-samples/releases/download/adventureworks/AdventureWorksDW2025.bak

COPY . .