#!/bin/bash

/opt/mssql/bin/sqlservr &
pid=$!

ERRCODE=1
until [[ "$ERRCODE" -eq 0 ]]; do
    sleep 1
    /opt/mssql-tools18/bin/sqlcmd -U sa -P "$MSSQL_SA_PASSWORD" -S localhost -C -t 1 -h -1 -Q "SET NOCOUNT ON; IF (SELECT SUM(state) FROM sys.databases) > 0 RAISERROR('Databases not ready', 16, 1)" -b
    ERRCODE=$?
done
/opt/mssql-tools18/bin/sqlcmd -U sa -P "$MSSQL_SA_PASSWORD" -S localhost -C -d master -i /usr/config/setup.sql -v MSSQL_DBGATE_READER_USERNAME="$MSSQL_DBGATE_READER_USERNAME" MSSQL_DBGATE_READER_PASSWORD="$MSSQL_DBGATE_READER_PASSWORD" MSSQL_CONTEXT_RETRIEVER_READER_USERNAME="$MSSQL_CONTEXT_RETRIEVER_READER_USERNAME" MSSQL_CONTEXT_RETRIEVER_READER_PASSWORD="$MSSQL_CONTEXT_RETRIEVER_READER_PASSWORD"

wait $pid