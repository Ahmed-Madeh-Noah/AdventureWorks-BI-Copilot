SET
    NOCOUNT ON;

IF DB_ID ('AdventureWorks2025') IS NULL
OR DATABASEPROPERTYEX ('AdventureWorks2025', 'Status') <> 'ONLINE' RAISERROR ('Database is not ready.', 16, 1);

IF NOT EXISTS (
    SELECT
        *
    FROM
        sys.server_principals
    WHERE
        name = '$(MSSQL_NEO4J_SETUP_READER_USERNAME)'
) RAISERROR ('DBGATE user is not ready.', 16, 1);

IF NOT EXISTS (
    SELECT
        *
    FROM
        sys.server_principals
    WHERE
        name = '$(MSSQL_DBGATE_READER_USERNAME)'
) RAISERROR ('DBGATE user is not ready.', 16, 1);