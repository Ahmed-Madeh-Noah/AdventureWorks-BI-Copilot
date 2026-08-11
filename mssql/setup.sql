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