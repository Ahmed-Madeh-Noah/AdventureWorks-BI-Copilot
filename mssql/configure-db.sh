#!/bin/bash

DBSTATUS=1
ERRCODE=1
i=0

while [[ "$DBSTATUS" -ne 0 ]] && [[ "$i" -lt 120 ]] && [[ "$ERRCODE" -ne 0 ]]; do
    ((i++))
    DBSTATUS=$(/opt/mssql-tools18/bin/sqlcmd -h -1 -t 1 -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C -Q "SET NOCOUNT ON; Select SUM(state) from sys.databases")
    ERRCODE=$?
    if [[ -z "$DBSTATUS" ]]; then
        DBSTATUS=1
    fi
    sleep 1
done

if [ "$DBSTATUS" -ne 0 ] || [ "$ERRCODE" -ne 0 ]; then
    echo "SQL Server took more than 120 seconds to start up or one or more databases are not in an ONLINE state"
    exit 1
fi

/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C -d master -i /usr/config/setup.sql -v MSSQL_DBGATE_READER_USERNAME="$MSSQL_DBGATE_READER_USERNAME" MSSQL_DBGATE_READER_PASSWORD="$MSSQL_DBGATE_READER_PASSWORD"