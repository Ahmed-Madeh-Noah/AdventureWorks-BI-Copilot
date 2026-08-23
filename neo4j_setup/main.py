import os

import pandas as pd
from neo4j import GraphDatabase
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


if __name__ == "__main__":
    populate_knowledge_graph()
