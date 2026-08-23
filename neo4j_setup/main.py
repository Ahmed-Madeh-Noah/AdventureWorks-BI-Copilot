import os

import pandas as pd
from sqlalchemy import Engine, create_engine, text


def get_engine() -> Engine:
    username = os.environ.get("MSSQL_NEO4J_SETUP_READER_USERNAME")
    assert username is not None
    password = os.environ.get("MSSQL_NEO4J_SETUP_READER_PASSWORD")
    assert password is not None
    return create_engine(
        f"mssql+mssqlpython://{username}:{password}@mssql/AdventureWorks2025?TrustServerCertificate=yes"
    )


def knowledge_graph_exists() -> bool:
    engine = get_engine()
    with open("get_db_schema.sql") as get_db_schema_file, engine.connect() as conn:
        get_db_schema_query = text(get_db_schema_file.read())
        schema_df = pd.read_sql_query(get_db_schema_query, conn)
        print(schema_df)


if __name__ == "__main__":
    if not knowledge_graph_exists():
        pass
