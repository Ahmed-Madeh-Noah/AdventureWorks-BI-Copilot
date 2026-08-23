import os

import pandas as pd
from neo4j import Driver, GraphDatabase
from sqlalchemy import Engine, create_engine, text


def get_database_engine() -> Engine:
    username = os.environ.get("MSSQL_NEO4J_SETUP_READER_USERNAME")
    assert username is not None
    password = os.environ.get("MSSQL_NEO4J_SETUP_READER_PASSWORD")
    assert password is not None
    return create_engine(
        f"mssql+mssqlpython://{username}:{password}@mssql/AdventureWorks2025?TrustServerCertificate=yes"
    )


def get_graph_connection_info() -> tuple[str, tuple[str, str]]:
    uri = "neo4j://neo4j"
    username = os.environ.get("NEO4J_USERNAME")
    assert username is not None
    password = os.environ.get("NEO4J_PASSWORD")
    assert password is not None
    return uri, (username, password)


def merge_schema_information(driver: Driver, schema_df: pd.DataFrame):
    driver.execute_query(
        "CREATE CONSTRAINT table_name_unique IF NOT EXISTS FOR (t:Table) REQUIRE t.name IS UNIQUE;"
    )

    unique_tables = [{"tableName": t} for t in schema_df["TableName"].unique()]
    driver.execute_query(
        """
        UNWIND $tables AS row
        MERGE (:Table {name: row.tableName})
    """,
        tables=unique_tables,
    )

    col_df = schema_df[["TableName", "ColumnName", "DataType", "IsPrimaryKey"]].copy()
    col_df["IsPrimaryKey"] = col_df["IsPrimaryKey"].fillna(False).astype(bool)
    columns_batch = col_df.to_dict("records")
    driver.execute_query(
        """
        UNWIND $columnsBatch AS row
        MATCH (t:Table {name: row.TableName})
        MERGE (t)-[:HAS_COLUMN]->(c:Column {name: row.ColumnName})
        SET 
            c.data_type = row.DataType,
            c.is_primary_key = row.IsPrimaryKey
    """,
        columnsBatch=columns_batch,
    )

    fk_df = schema_df[
        ["TableName", "ColumnName", "ReferencedTableName", "ReferencedColumnName"]
    ].dropna()
    fks_batch = fk_df.to_dict("records")
    if fks_batch:
        driver.execute_query(
            """
            UNWIND $fksBatch AS row
            MATCH (source_table:Table {name: row.TableName})-[:HAS_COLUMN]->(source_col:Column {name: row.ColumnName})
            MATCH (target_table:Table {name: row.ReferencedTableName})-[:HAS_COLUMN]->(target_col:Column {name: row.ReferencedColumnName})
            MERGE (source_col)-[:REFERENCES]->(target_col)
        """,
            fksBatch=fks_batch,
        )


def populate_knowledge_graph() -> None:
    engine = get_database_engine()
    uri, auth = get_graph_connection_info()
    with (
        open("get_db_schema.sql") as get_db_schema_file,
        engine.connect() as conn,
        GraphDatabase.driver(uri, auth=auth) as driver,
    ):
        driver.verify_connectivity()
        get_db_schema_query = text(get_db_schema_file.read())
        schema_df = pd.read_sql_query(get_db_schema_query, conn)
        assert len(schema_df) != 0
        merge_schema_information(driver, schema_df)


if __name__ == "__main__":
    populate_knowledge_graph()
