FROM mcr.microsoft.com/mssql/server:2025-latest

USER root
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

USER mssql

WORKDIR /usr/config
COPY --chmod=755 . .

USER root
USER mssql

ENTRYPOINT ["./entrypoint.sh"]