import os

import ollama
import pandas as pd
from neo4j import Driver, GraphDatabase
from sqlalchemy import Engine, create_engine, text
from toon_format import encode
from tqdm import tqdm


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


def get_ollama_client() -> ollama.Client:
    return ollama.Client(host="http://ollama:11434")


def merge_table_descriptions(driver: Driver, schema_df: pd.DataFrame) -> None:
    records, _, _ = driver.execute_query(
        """//cypher
        MATCH (t:Table)
        WHERE t.description IS NULL
        
        OPTIONAL MATCH (t)-[:HAS_COLUMN]->()-[:REFERENCES]->()<-[:HAS_COLUMN]-(refTable:Table)
        WHERE t.name <> refTable.name
        
        RETURN t.name AS TableName, 
               collect(DISTINCT refTable.name) AS ReferencedTables
        """
    )

    if not records:
        return

    ollama_client = get_ollama_client()
    ollama_llm = os.environ.get("OLLAMA_LLM")
    assert ollama_llm is not None

    for record in tqdm(records, desc="Generating table descriptions"):
        table_name = record["TableName"]
        ref_tables = record["ReferencedTables"]

        tables_to_include = [table_name] + ref_tables
        relevant_schema = schema_df[schema_df["TableName"].isin(tables_to_include)]
        schema_csv = encode(relevant_schema.to_csv(index=False))

        prompt = f"""
        Target Table: {table_name}
        Referenced Tables Context: {", ".join(ref_tables) if ref_tables else "None"}
        Relevant Database Schema:
        {schema_csv}
        """.replace(r"\n", "\n")

        system = """
        You are a business intelligence copilot.
        I will provide you a target table, tables it references, and the relevant database schema. 
        Generate a one-sentence long, business-friendly description for the table without overlapping with other tables' descriptions.
        Make sure to not use more than ten words.
        Respond in plain text with no formatting.
        """

        description_response = ollama_client.generate(
            model=ollama_llm,
            prompt=prompt,
            system=system,
            think=False,
            options={"seed": 42, "temperature": 0.0},
        ).response

        assert description_response is not None
        final_description = description_response.replace(r"\n", "\n")

        driver.execute_query(
            """//cypher
            MATCH (t:Table {name: $tableName})
            SET t.description = $description
            """,
            tableName=table_name,
            description=final_description,
        )


def merge_table_embeddings(driver: Driver) -> None:
    records, _, _ = driver.execute_query(
        """//cypher
        MATCH (t:Table)
        WHERE t.description IS NOT NULL AND t.embedding IS NULL
        RETURN t.name AS TableName, t.description AS Description
        """
    )

    if not records:
        return

    ollama_client = get_ollama_client()
    ollama_embedding = os.environ.get("OLLAMA_EMBEDDING")
    assert ollama_embedding is not None

    table_data = []
    descriptions = []

    for record in tqdm(records, desc="Preparing table embeddings"):
        table_data.append({"tableName": record["TableName"]})
        descriptions.append(record["Description"])

    embeddings = ollama_client.embed(
        model=ollama_embedding,
        input=descriptions,
    ).embeddings

    embedding_batch = [
        {"tableName": item["tableName"], "embedding": vector}
        for item, vector in zip(table_data, embeddings)
    ]

    driver.execute_query(
        """//cypher
        UNWIND $batch AS row
        MATCH (t:Table {name: row.tableName})
        SET t.embedding = row.embedding
        """,
        batch=embedding_batch,
    )


def merge_column_descriptions(driver: Driver, schema_df: pd.DataFrame) -> None:
    records, _, _ = driver.execute_query(
        """//cypher
        MATCH (t:Table)-[:HAS_COLUMN]->(c:Column)
        WHERE c.description IS NULL
        
        OPTIONAL MATCH (t)-[:HAS_COLUMN]->()-[:REFERENCES]->(refCol)<-[:HAS_COLUMN]-(refTable:Table)
        WHERE t.name <> refTable.name
        
        RETURN c.name AS ColumnName, 
               t.name AS TableName, 
               collect(DISTINCT refTable.name) AS ReferencedTables
        """
    )

    if not records:
        return

    ollama_client = get_ollama_client()
    ollama_llm = os.environ.get("OLLAMA_LLM")
    assert ollama_llm is not None

    for record in tqdm(records, desc="Generating column descriptions"):
        col_name = record["ColumnName"]
        table_name = record["TableName"]
        ref_tables = record["ReferencedTables"]

        tables_to_include = [table_name] + ref_tables
        relevant_schema = schema_df[schema_df["TableName"].isin(tables_to_include)]
        schema_csv = encode(relevant_schema.to_csv(index=False))

        prompt = f"""
        Target Column: {col_name}
        Parent Table: {table_name}
        Relevant Database Schema:
        {schema_csv}
        """.replace(r"\n", "\n")

        system = """
        You are a business intelligence copilot.
        I will provide you a target column, its parent table, and the relevant database schema. 
        Generate a one-sentence long, business-friendly description for the column without overlapping with other tables' or columns' descriptions.
        Make sure to not use more than ten words.
        Respond in plain text with no formatting.
        """

        description_response = ollama_client.generate(
            model=ollama_llm,
            prompt=prompt,
            system=system,
            think=False,
            options={"seed": 42, "temperature": 0.0},
        ).response

        assert description_response is not None
        final_description = description_response.replace(r"\n", "\n")

        driver.execute_query(
            """//cypher
            MATCH (t:Table {name: $tableName})-[:HAS_COLUMN]->(c:Column {name: $columnName})
            SET c.description = $description
            """,
            tableName=table_name,
            columnName=col_name,
            description=final_description,
        )


def merge_column_embeddings(driver: Driver) -> None:
    records, _, _ = driver.execute_query(
        """//cypher
        MATCH (t:Table)-[:HAS_COLUMN]->(c:Column)
        WHERE c.description IS NOT NULL AND c.embedding IS NULL
        RETURN t.name AS TableName, c.name AS ColumnName, c.description AS Description
        """
    )

    if not records:
        return

    ollama_client = get_ollama_client()
    ollama_embedding = os.environ.get("OLLAMA_EMBEDDING")
    assert ollama_embedding is not None

    column_data = []
    descriptions = []

    for record in tqdm(records, desc="Preparing column embeddings"):
        column_data.append(
            {"tableName": record["TableName"], "columnName": record["ColumnName"]}
        )
        descriptions.append(record["Description"])

    embeddings = ollama_client.embed(
        model=ollama_embedding,
        input=descriptions,
    ).embeddings

    embedding_batch = [
        {
            "tableName": item["tableName"],
            "columnName": item["columnName"],
            "embedding": vector,
        }
        for item, vector in zip(column_data, embeddings)
    ]

    driver.execute_query(
        """//cypher
        UNWIND $batch AS row
        MATCH (t:Table {name: row.tableName})-[:HAS_COLUMN]->(c:Column {name: row.columnName})
        SET c.embedding = row.embedding
        """,
        batch=embedding_batch,
    )


def create_hybrid_search_indexes(driver: Driver) -> None:
    driver.execute_query(
        """//cypher
        CREATE FULLTEXT INDEX schema_fulltext IF NOT EXISTS 
        FOR (n:Table|Column) 
        ON EACH [n.name, n.description]
        """
    )

    driver.execute_query(
        """//cypher
        CREATE VECTOR INDEX table_embeddings IF NOT EXISTS 
        FOR (t:Table) 
        ON t.embedding
        OPTIONS {indexConfig: {
          `vector.dimensions`: 1024, 
          `vector.similarity_function`: 'cosine'
        }}
        """
    )

    driver.execute_query(
        """//cypher
        CREATE VECTOR INDEX column_embeddings IF NOT EXISTS 
        FOR (c:Column) 
        ON c.embedding
        OPTIONS {indexConfig: {
          `vector.dimensions`: 1024, 
          `vector.similarity_function`: 'cosine'
        }}
        """
    )

    driver.execute_query("CALL db.awaitIndexes(30)")


def merge_nodes_descriptions_and_embeddings(
    driver: Driver, schema_df: pd.DataFrame
) -> None:
    merge_table_descriptions(driver, schema_df)
    merge_column_descriptions(driver, schema_df)
    merge_table_embeddings(driver)
    merge_column_embeddings(driver)
    create_hybrid_search_indexes(driver)


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
        merge_nodes_descriptions_and_embeddings(driver, schema_df)


if __name__ == "__main__":
    populate_knowledge_graph()
