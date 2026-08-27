import os
import re
from collections.abc import Sequence

import ollama
import pandas as pd
from neo4j import GraphDatabase
from sqlalchemy import create_engine, text
from sqlalchemy.exc import (
    SQLAlchemyError,
)  # Add this linefrom toon_format import encode
from neo4j_viz.neo4j import from_neo4j
from neo4j_viz import VisualizationGraph
from toon_format import encode

ollama_embeddding = os.environ.get("OLLAMA_EMBEDDING")
assert ollama_embeddding is not None

ollama_llm = os.environ.get("OLLAMA_LLM")
assert ollama_llm is not None

ollama_coder = os.environ.get("OLLAMA_CODER")
assert ollama_coder is not None

ollama_client = ollama.Client(host="http://ollama:11434")

neo4j_username = os.environ.get("NEO4J_USERNAME")
assert neo4j_username is not None

neo4j_password = os.environ.get("NEO4J_PASSWORD")
assert neo4j_password is not None

driver = GraphDatabase.driver("bolt://neo4j", auth=(neo4j_username, neo4j_password))
driver.verify_connectivity()

mssql_username = os.environ.get("MSSQL_NEO4J_SETUP_READER_USERNAME")
assert mssql_username is not None
mssql_password = os.environ.get("MSSQL_NEO4J_SETUP_READER_PASSWORD")
assert mssql_password is not None

engine = create_engine(
    f"mssql+mssqlpython://{mssql_username}:{mssql_password}@mssql/AdventureWorks2025?TrustServerCertificate=yes"
)

sql_multi_line_block_pattern = re.compile(
    r"```(?:sql)?\s*([\s\S]*?)\s*```",
    re.IGNORECASE,
)

sql_inline_block_pattern = re.compile(
    r"`([^`\n]+)`",
    re.IGNORECASE,
)


def execute_sql_query(sql: str) -> pd.DataFrame | str:
    try:
        with engine.connect() as conn:
            query = text(sql)
            results_df = pd.read_sql_query(query, conn)
            return results_df
    except SQLAlchemyError as e:
        # SQLAlchemy wraps errors; we extract the original driver error if it exists
        if hasattr(e, "orig") and e.orig:
            # e.orig contains the pure driver error without the repeated SQL string
            return f"Database Error: {str(e.orig)}"
        return f"Database Error: {str(e)}"
    except Exception as e:
        # Catch-all for non-database exceptions (e.g., Pandas parsing issues)
        return f"System Error: {str(e)}"


schema_df = None
with open("./get_db_schema.sql") as get_db_schema_file:
    get_db_schema_query = get_db_schema_file.read()
    schema_df = execute_sql_query(get_db_schema_query)
assert schema_df is not None


def get_all_graph_vg() -> VisualizationGraph:
    """Fetches all nodes and relationships in the database."""
    result = driver.execute_query(
        """//cypher
        MATCH (n)
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN n, r, m
        """
    )

    # Create the graph first
    vg = from_neo4j(result)
    # Apply the node captions using the explicit 'property' keyword argument
    vg.set_node_captions(property="name")
    return vg


def get_subgraph_vg(table_names: list[str]) -> VisualizationGraph:
    """Fetches specific tables, their columns, and valid internal references."""
    result = driver.execute_query(
        """//cypher
        MATCH (t:Table)
        WHERE t.name IN $table_names
        OPTIONAL MATCH (t)-[hc:HAS_COLUMN]->(c:Column)
        OPTIONAL MATCH (c)-[ref:REFERENCES]->(c_ref:Column)
        // Ensure REFERENCES are only returned if the target column is also in the display set
        WHERE c_ref IS NULL OR EXISTS {
            MATCH (t_ref:Table)-[:HAS_COLUMN]->(c_ref)
            WHERE t_ref.name IN $table_names
        }
        RETURN t, hc, c, ref, c_ref
        """,
        table_names=table_names,
    )

    # Create the subgraph first
    vg = from_neo4j(result)
    # Apply the node captions using the explicit 'property' keyword argument
    vg.set_node_captions(property="name")
    return vg


def embed(prompt: str) -> Sequence[float]:
    assert ollama_embeddding is not None
    return ollama_client.embed(ollama_embeddding, prompt).embeddings[0]


def get_context(prompt: str) -> tuple[str, list[str], list[str]]:
    """Returns the encoded schema alongside the table names for graph visualization."""
    prompt_embedding = embed(prompt)
    records = driver.execute_query(
        """//cypher
        WITH
        $query AS query,
        $queryVector AS queryVector,
        $sourceK AS sourceK,
        $finalK AS finalK,
        $rrfConstant AS rrfConstant,
        $sourceWeights AS sourceWeights
        CALL {
        // 1. Full-Text Search (covers both Tables and Columns)
        WITH query, sourceK, rrfConstant, sourceWeights
        CALL db.index.fulltext.queryNodes('schema_fulltext', query, {limit: sourceK})
        YIELD node, score
        WITH node, score, rrfConstant, sourceWeights
        ORDER BY score DESC, elementId(node) ASC
        WITH collect(node) AS nodes, rrfConstant, sourceWeights
        WITH nodes, rrfConstant, coalesce(sourceWeights['fulltext'], 1.0) AS weight
        UNWIND CASE WHEN size(nodes) = 0 THEN [] ELSE range(0, size(nodes) - 1) END AS rankIndex
        RETURN
            nodes[rankIndex] AS node,
            weight / (rrfConstant + rankIndex + 1) AS contribution
        UNION ALL
        // 2. Vector Search for Tables
        WITH queryVector, sourceK, rrfConstant, sourceWeights
        CALL db.index.vector.queryNodes('table_embeddings', sourceK, queryVector)
        YIELD node, score
        WITH node, score, sourceK, rrfConstant, sourceWeights
        ORDER BY score DESC, elementId(node) ASC
        WITH collect(node) AS nodes, sourceK, rrfConstant, sourceWeights
        WITH nodes, rrfConstant, coalesce(sourceWeights['vector'], 1.0) AS weight
        UNWIND CASE WHEN size(nodes) = 0 THEN [] ELSE range(0, size(nodes) - 1) END AS rankIndex
        RETURN
            nodes[rankIndex] AS node,
            weight / (rrfConstant + rankIndex + 1) AS contribution
        UNION ALL
        // 3. Vector Search for Columns
        WITH queryVector, sourceK, rrfConstant, sourceWeights
        CALL db.index.vector.queryNodes('column_embeddings', sourceK, queryVector)
        YIELD node, score
        WITH node, score, sourceK, rrfConstant, sourceWeights
        ORDER BY score DESC, elementId(node) ASC
        WITH collect(node) AS nodes, sourceK, rrfConstant, sourceWeights
        WITH nodes, rrfConstant, coalesce(sourceWeights['vector'], 1.0) AS weight
        UNWIND CASE WHEN size(nodes) = 0 THEN [] ELSE range(0, size(nodes) - 1) END AS rankIndex
        RETURN
            nodes[rankIndex] AS node,
            weight / (rrfConstant + rankIndex + 1) AS contribution
        }
        // Combine all scores
        WITH node, finalK, sum(contribution) AS wrrf
        ORDER BY wrrf DESC, elementId(node) ASC
        // Slice the array to get only the top finalK results
        WITH collect({node: node, wrrf: wrrf}) AS orderedRows, finalK
        UNWIND orderedRows[..finalK] AS row
        WITH row.node AS node, row.wrrf AS wrrf
        // Find the parent table IF the matched node is a Column
        OPTIONAL MATCH (parentTable:Table)-[:HAS_COLUMN]->(node)
        // Return the required data
        RETURN 
         coalesce(parentTable.name, node.name) AS tableName,
        labels(node)[0] AS matchedEntityType,
        node.name AS matchedEntityName,
        node.description AS description,
        wrrf
        ORDER BY wrrf DESC, elementId(node) ASC;
        """,
        query=prompt,
        queryVector=prompt_embedding,
        sourceK=10,
        finalK=5,
        rrfConstant=60,
        sourceWeights={"fulltext": 1.2, "vector": 1.0},
    ).records

    table_names = [record["tableName"] for record in records]

    relevant_table_names = driver.execute_query(
        """//cypher
        // 1. Unwind the input list into individual table names
        UNWIND $tableNames AS inputName
        // 2. Match the starting tables in the graph
        MATCH (t:Table {name: inputName})
        // 3. Optionally find any tables referenced by the starting table's columns
        OPTIONAL MATCH (t)-[:HAS_COLUMN]->()-[:REFERENCES]->()<-[:HAS_COLUMN]-(refT:Table)
        // 4. Combine the original table name and the referenced table name 
        UNWIND [t.name, refT.name] AS combinedName
        // 5. Ensure uniqueness and filter out nulls (which occur if refT doesn't exist)
        WITH DISTINCT combinedName
        WHERE combinedName IS NOT NULL
        // 6. Return the final deduplicated result as a list
        RETURN collect(combinedName) AS expandedTableList;
        """,
        tableNames=table_names,
    ).records[0]["expandedTableList"]

    assert isinstance(schema_df, pd.DataFrame)
    relevant_schema = schema_df[schema_df["TableName"].isin(relevant_table_names)]

    return (
        encode(relevant_schema.to_csv(index=False)),
        table_names,
        relevant_table_names,
    )


def extract_sql(text: str) -> str | None:
    text = text.replace(r"\n", "\n").strip()
    if isinstance(execute_sql_query(text), pd.DataFrame):
        return text
    match = sql_multi_line_block_pattern.search(text)
    if match:
        sql = match.group(1).strip()
        if isinstance(execute_sql_query(sql), pd.DataFrame):
            return sql
    match = sql_inline_block_pattern.search(text)
    if match:
        sql = match.group(1).strip()
        if isinstance(execute_sql_query(sql), pd.DataFrame):
            return sql
    return None


def infer_sql(prompt: str, context: str):
    system = f"""
              You are a Microsoft SQL Server (T-SQL) expert. Write a valid T-SQL query to answer the user question using ONLY the schema provided below.
              ### Database Schema
              {context}
              ### Rules:
                1. Use valid T-SQL syntax only (e.g., use TOP instead of LIMIT).
                2. Use ONLY tables and columns defined in the schema above. Do not invent objects.
                3. Return ONLY the executable query inside a single ```sql ``` code block. Do not add explanations or notes.
              """
    assert ollama_coder is not None
    coder_response = ollama_client.generate(
        ollama_coder,
        prompt=prompt,
        system=system,
        think=False,
        options={"seed": 42, "temperature": 0.0},
    ).response

    assert coder_response is not None
    sql = extract_sql(coder_response)
    if sql is not None:
        return sql

    system = """
             You are an automated SQL extractor. Your sole function is to extract raw SQL statements from unstructured text and return only clean, executable SQL code.
             ### Instructions:
                1. Extract ONLY the SQL query statements found in the input.
                2. Strip all Markdown formatting, including code fences (```sql, ```), inline code ticks (`), bolding, and headers.
                3. Remove all non-SQL text: explanations, pleasantries, preambles, trailing notes, and summaries.
                4. Preserve the exact SQL logic, table names, column names, aliases, and whitespace structure. Do not optimize, alter, or reformat the query syntax.
                5. If multiple separate SQL statements are present, output them sequentially separated by semicolons.
                6. Do NOT enclose your output in backticks, markdown fences, or quotes. Output plain text only.
                7. If no SQL query exists in the input, return an empty string.
             """
    assert ollama_llm is not None
    response = ollama_client.generate(
        ollama_llm,
        prompt=coder_response,
        system=system,
        think=False,
        options={"seed": 42, "temperature": 0.0},
    ).response
    assert response is not None

    sql = extract_sql(response)
    if sql is not None:
        return sql
    return coder_response.replace(r"\n", "\n").strip()
