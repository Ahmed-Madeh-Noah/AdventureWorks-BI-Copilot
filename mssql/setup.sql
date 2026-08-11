USE [master];
GO

RESTORE DATABASE [AdventureWorks2025]
FROM DISK = '/var/opt/mssql/backup/AdventureWorks2025.bak'
WITH
    MOVE 'AdventureWorksDW' TO '/var/opt/mssql/data/AdventureWorks2025_Data.mdf', 
    MOVE 'AdventureWorksDW_log' TO '/var/opt/mssql/data/AdventureWorks2025_log.ldf',
    FILE = 1,
    NOUNLOAD,
    STATS = 5;
GO

USE [master];
CREATE LOGIN $(MSSQL_DBGATE_READER_USERNAME) WITH PASSWORD = '$(MSSQL_DBGATE_READER_PASSWORD)';
GO

USE [AdventureWorks2025];
CREATE USER $(MSSQL_DBGATE_READER_USERNAME) FOR LOGIN $(MSSQL_DBGATE_READER_USERNAME);
GO

ALTER ROLE db_datareader ADD MEMBER $(MSSQL_DBGATE_READER_USERNAME);
GO