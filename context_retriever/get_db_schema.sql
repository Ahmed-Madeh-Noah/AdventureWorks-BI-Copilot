SELECT
    t.name AS TABLE_NAME,
    c.name AS COLUMN_NAME,
    c.is_nullable AS IS_NULLABLE,
    ty.name AS DATA_TYPE,
    CAST(
        CASE
            WHEN ic.column_id IS NOT NULL THEN 1
            ELSE 0
        END AS BIT
    ) AS IS_PRIMARY_KEY,
    rt.name AS REFERENCED_TABLE_NAME,
    rc.name AS REFERENCED_COLUMN_NAME
FROM
    sys.tables t
    -- Get the columns for each table
    INNER JOIN sys.columns c ON t.object_id = c.object_id
    -- Get the data types for each column
    INNER JOIN sys.types ty ON c.user_type_id = ty.user_type_id
    -- Check for Primary Key constraints
    LEFT JOIN sys.index_columns ic
    INNER JOIN sys.indexes i ON i.object_id = ic.object_id
    AND i.index_id = ic.index_id
    AND i.is_primary_key = 1 ON ic.object_id = c.object_id
    AND ic.column_id = c.column_id
    -- Check for Foreign Key constraints
    LEFT JOIN sys.foreign_key_columns fkc ON fkc.parent_object_id = c.object_id
    AND fkc.parent_column_id = c.column_id
    -- Get the referenced table name
    LEFT JOIN sys.tables rt ON rt.object_id = fkc.referenced_object_id
    -- Get the referenced column name
    LEFT JOIN sys.columns rc ON rc.object_id = fkc.referenced_object_id
    AND rc.column_id = fkc.referenced_column_id
    -- Exclude internal system tables
WHERE
    t.is_ms_shipped = 0
ORDER BY
    t.name,
    c.column_id;