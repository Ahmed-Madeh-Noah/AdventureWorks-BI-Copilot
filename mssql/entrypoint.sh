#!/bin/bash

/opt/mssql/bin/sqlservr &
pid=$!

BACKUP_DIR="/var/opt/mssql/backup"
BACKUP_FILE="$BACKUP_DIR/AdventureWorks2025.bak"
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Downloading AdventureWorks backup..."
    mkdir --parents "$BACKUP_DIR"
    curl --location --output "$BACKUP_FILE" https://github.com/Microsoft/sql-server-samples/releases/download/adventureworks/AdventureWorksDW2025.bak
fi

ERRCODE=1
until [[ "$ERRCODE" -eq 0 ]]; do
    sleep 1
    /opt/mssql-tools18/bin/sqlcmd -U sa -P "$MSSQL_SA_PASSWORD" -S localhost -C -t 1 -h -1 -Q "SET NOCOUNT ON; IF (SELECT SUM(state) FROM sys.databases) > 0 RAISERROR('Databases not ready', 16, 1)" -b
    ERRCODE=$?
done
/opt/mssql-tools18/bin/sqlcmd -U sa -P "$MSSQL_SA_PASSWORD" -S localhost -C -d master -i /usr/config/setup.sql -v MSSQL_DBGATE_READER_USERNAME="$MSSQL_DBGATE_READER_USERNAME" MSSQL_DBGATE_READER_PASSWORD="$MSSQL_DBGATE_READER_PASSWORD" MSSQL_CONTEXT_RETRIEVER_READER_USERNAME="$MSSQL_CONTEXT_RETRIEVER_READER_USERNAME" MSSQL_CONTEXT_RETRIEVER_READER_PASSWORD="$MSSQL_CONTEXT_RETRIEVER_READER_PASSWORD"

wait $pid