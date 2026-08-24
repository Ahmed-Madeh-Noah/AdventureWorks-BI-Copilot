SELECT
    t.name AS TableName,
    c.name AS ColumnName,
    ty.name AS DataType,
    CAST(ISNULL (pk.is_primary_key, 0) AS BIT) AS IsPrimaryKey,
    rt.name AS ReferencedTableName,
    rc.name AS ReferencedColumnName
FROM
    sys.tables t
    INNER JOIN sys.columns c ON t.object_id = c.object_id
    INNER JOIN sys.types ty ON c.user_type_id = ty.user_type_id
    -- Find Primary Keys
    LEFT JOIN (
        SELECT
            ic.object_id,
            ic.column_id,
            1 AS is_primary_key
        FROM
            sys.index_columns ic
            INNER JOIN sys.indexes i ON ic.object_id = i.object_id
            AND ic.index_id = i.index_id
        WHERE
            i.is_primary_key = 1
    ) pk ON c.object_id = pk.object_id
    AND c.column_id = pk.column_id
    -- Find Foreign Key References
    LEFT JOIN sys.foreign_key_columns fkc ON fkc.parent_object_id = c.object_id
    AND fkc.parent_column_id = c.column_id
    LEFT JOIN sys.tables rt ON fkc.referenced_object_id = rt.object_id
    LEFT JOIN sys.columns rc ON fkc.referenced_object_id = rc.object_id
    AND fkc.referenced_column_id = rc.column_id
ORDER BY
    TableName,
    c.column_id;