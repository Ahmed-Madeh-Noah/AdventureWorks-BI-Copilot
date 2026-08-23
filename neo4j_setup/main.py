import os

import pandas as pd
from neo4j import Driver, GraphDatabase, Record
from sqlalchemy import Engine, create_engine, text
from toon_format import encode


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


def merge_schema_information(driver: Driver, schema_df: pd.DataFrame) -> None:
    driver.execute_query(
        """//cypher
        CREATE CONSTRAINT table_name_unique IF NOT EXISTS
        FOR (t:Table) REQUIRE t.name IS UNIQUE;
        """
    )

    unique_tables = [{"tableName": t} for t in schema_df["TableName"].unique()]
    driver.execute_query(
        """//cypher
        UNWIND $tables AS row
        MERGE (:Table {name: row.tableName})
        """,
        tables=unique_tables,
    )

    col_df = schema_df[["TableName", "ColumnName", "DataType", "IsPrimaryKey"]].copy()
    col_df["IsPrimaryKey"] = col_df["IsPrimaryKey"].fillna(False).astype(bool)
    columns_batch = col_df.to_dict("records")
    driver.execute_query(
        """//cypher
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
            """//cypher
            UNWIND $fksBatch AS row
            MATCH (source_table:Table {name: row.TableName})-[:HAS_COLUMN]->(source_col:Column {name: row.ColumnName})
            MATCH (target_table:Table {name: row.ReferencedTableName})-[:HAS_COLUMN]->(target_col:Column {name: row.ReferencedColumnName})
            MERGE (source_col)-[:REFERENCES]->(target_col)
            """,
            fksBatch=fks_batch,
        )


def get_table_relationships(records: list[Record]) -> dict[str, set[str]]:
    table_relationships = {}
    for record in records:
        table_name = record["TableName"]
        referenced_table_name = record["ReferencedTableName"]
        if table_name not in table_relationships:
            table_relationships[table_name] = {referenced_table_name}
        else:
            table_relationships[table_name].add(referenced_table_name)
    return table_relationships


def get_tables_of_interest(table_relationships: dict[str, set[str]]) -> list[set[str]]:
    tables_of_interest = []
    for table, referenced_tables in table_relationships.items():
        referenced_tables.add(table)
        tables_of_interest.append(referenced_tables)
    return tables_of_interest


def merge_table_nodes_descriptions(driver: Driver, schema_df: pd.DataFrame) -> None:
    records, _, _ = driver.execute_query(
        """//cypher
        MATCH (t:Table)
        WHERE t.description IS NULL
        MATCH (t)-[:HAS_COLUMN]->()-[:REFERENCES]->(refCol)
        MATCH (refTable)-[:HAS_COLUMN]->(refCol)
        WHERE t.name <> refTable.name
        RETURN t.name AS TableName, refTable.name AS ReferencedTableName
        """
    )
    table_relationships = get_table_relationships(records)
    tables_of_interest = get_tables_of_interest(table_relationships)
    for target_table, referenced_tables in zip(
        table_relationships.keys(), tables_of_interest
    ):
        referenced_tables_schema = schema_df[
            schema_df["TableName"].isin(referenced_tables)
        ]
        referenced_tables_schema = encode(referenced_tables_schema.to_csv(index=False))
        prompt = f"""
                  You are a business intelligence copilot.
                  I will provide you a target table and all the relevant database schema for you to generate a one-sentence long,
                  business-friendly description for the table without overlapping with other tables' or columns' descriptions.
                  Make sure to not use more than ten words.

                  Target Table: {target_table}

                  Relevant Database Schema:
                  {referenced_tables_schema}
                  """.replace(r"\n", "\n")


def merge_nodes_descriptions(driver: Driver, schema_df: pd.DataFrame) -> None:
    merge_table_nodes_descriptions(driver, schema_df)
    # records, _, _ = driver.execute_query(
    #     """//cypher
    #     MATCH (c:Column)
    #     WHERE c.description IS NULL
    #     MATCH (t)-[:HAS_COLUMN]->(c)
    #     MATCH (t)-[:HAS_COLUMN]->()-[:REFERENCES]->(refCol)
    #     MATCH (refTable)-[:HAS_COLUMN]->(refCol)
    #     WHERE t.name <> refTable.name
    #     RETURN c.name AS ColumnName, t.name AS TableName, refTable.name AS ReferencedTableName
    #     """
    # )
    # table_relationships = {}
    # for record in records:
    #     table_name = record["TableName"]
    #     referenced_table_name = record["ReferencedTableName"]
    #     if table_name == referenced_table_name:
    #         continue
    #     if table_name not in table_relationships:
    #         table_relationships[table_name] = {referenced_table_name}
    #     else:
    #         table_relationships[table_name].add(referenced_table_name)


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
        assert not schema_df.empty
        merge_schema_information(driver, schema_df)
        merge_nodes_descriptions(driver, schema_df)


if __name__ == "__main__":
    populate_knowledge_graph()
