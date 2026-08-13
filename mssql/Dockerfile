FROM mcr.microsoft.com/mssql/server:2025-latest

RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*


WORKDIR /usr/config

COPY . .

ENTRYPOINT ["./entrypoint.sh"]