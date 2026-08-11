#!/bin/bash

BACKUP_DIR="/var/opt/mssql/backup"
BACKUP_FILE="$BACKUP_DIR/AdventureWorks2025.bak"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Downloading AdventureWorks backup..."
    mkdir -p "$BACKUP_DIR"
    curl -L -o "$BACKUP_FILE" https://github.com/Microsoft/sql-server-samples/releases/download/adventureworks/AdventureWorksDW2025.bak
fi

/usr/config/configure-db.sh &

exec /opt/mssql/bin/sqlservr