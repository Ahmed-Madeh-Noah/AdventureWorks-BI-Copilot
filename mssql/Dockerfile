FROM mcr.microsoft.com/mssql/server:2025-latest

USER root
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

USER mssql
WORKDIR /var/opt/mssql/config

COPY --chmod=755 . .

ENTRYPOINT ["./entrypoint.sh"]