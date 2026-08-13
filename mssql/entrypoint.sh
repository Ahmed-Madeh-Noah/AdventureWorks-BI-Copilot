#!/bin/bash

sqlservr &
pid=$!

./configure-db.sh &

BACKUP_DIR="/var/opt/mssql/backup"
BACKUP_FILE="$BACKUP_DIR/AdventureWorks2025.bak"
if [ ! -f "$BACKUP_FILE" ]; then
    echo "Downloading AdventureWorks backup..."
    mkdir --parents "$BACKUP_DIR"
    curl --location --output "$BACKUP_FILE" https://github.com/Microsoft/sql-server-samples/releases/download/adventureworks/AdventureWorksDW2025.bak
fi

wait $pid