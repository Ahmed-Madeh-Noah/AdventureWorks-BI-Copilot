FROM mcr.microsoft.com/mssql/server:2025-latest

USER root
RUN apt-get update && \
    apt-get install -y dos2unix curl && \
    rm -rf /var/lib/apt/lists/*

USER mssql

WORKDIR /usr/config
COPY --chmod=755 . .

USER root
RUN dos2unix *.sh
USER mssql

ENTRYPOINT ["./entrypoint.sh"]