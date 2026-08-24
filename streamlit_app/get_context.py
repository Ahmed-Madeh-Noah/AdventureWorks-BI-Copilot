import ollama
from neo4j import GraphDatabase
from toon_format import encode


def retrieve_hybrid_context(query_text: str):
    ollama_client = ollama.Client(host="http://ollama:11434")
    query_vector = ollama_client.embed(
        model="qwen3-embedding:0.6b", input=query_text
    ).embeddings[0]

    cypher_query = """
    WITH
      $query AS query,
      $queryVector AS queryVector,
      $sourceK AS sourceK,
      $finalK AS finalK,
      $rrfConstant AS rrfConstant,
      $sourceWeights AS sourceWeights

    CALL {
      WITH query, queryVector, sourceK, rrfConstant, sourceWeights

      // SIGNAL 1: Lexical Search (Matches BOTH Tables and Columns)
      CALL db.index.fulltext.queryNodes('schema_fulltext', query, {limit: sourceK})
      YIELD node AS entity, score
      ORDER BY score DESC, elementId(entity) ASC
      WITH collect(entity) AS entities, rrfConstant, sourceWeights
      WITH entities, rrfConstant, coalesce(sourceWeights['fulltext'], 1.0) AS weight
      UNWIND CASE WHEN size(entities) = 0 THEN [] ELSE range(0, size(entities) - 1) END AS rankIndex
      RETURN
        entities[rankIndex] AS entity,
        weight / (rrfConstant + rankIndex + 1) AS contribution

      UNION ALL

      // SIGNAL 2: Semantic Search (Matches ONLY Tables)
      WITH queryVector, sourceK, rrfConstant, sourceWeights
      CALL db.index.vector.queryNodes('table_embeddings', sourceK, queryVector)
      YIELD node AS entity, score
      WHERE entity:Table
      ORDER BY score DESC, elementId(entity) ASC
      WITH collect(entity) AS entities, rrfConstant, sourceWeights
      WITH entities, rrfConstant, coalesce(sourceWeights['vector'], 1.0) AS weight
      UNWIND CASE WHEN size(entities) = 0 THEN [] ELSE range(0, size(entities) - 1) END AS rankIndex
      RETURN
        entities[rankIndex] AS entity,
        weight / (rrfConstant + rankIndex + 1) AS contribution

      UNION ALL

      // SIGNAL 3: Semantic Search (Matches ONLY Columns)
      WITH queryVector, sourceK, rrfConstant, sourceWeights
      CALL db.index.vector.queryNodes('column_embeddings', sourceK, queryVector)
      YIELD node AS entity, score
      WHERE entity:Column
      ORDER BY score DESC, elementId(entity) ASC
      WITH collect(entity) AS entities, rrfConstant, sourceWeights
      WITH entities, rrfConstant, coalesce(sourceWeights['vector'], 1.0) AS weight
      UNWIND CASE WHEN size(entities) = 0 THEN [] ELSE range(0, size(entities) - 1) END AS rankIndex
      RETURN
        entities[rankIndex] AS entity,
        weight / (rrfConstant + rankIndex + 1) AS contribution
    }

    // Fuse Results Together
    WITH entity, finalK, sum(contribution) AS wrrf
    ORDER BY wrrf DESC, elementId(entity) ASC
    WITH collect({entity: entity, wrrf: wrrf}) AS orderedRows, finalK
    WITH orderedRows[..finalK] AS limitedRows
    UNWIND limitedRows AS row
    WITH row.entity AS entity, row.wrrf AS wrrf

    // --- NEW EXTRACT LOGIC: From matches to related schema ---

    // 1. Find the parent table if the matched entity is a column
    OPTIONAL MATCH (t:Table)-[:HAS_COLUMN]->(entity)
    WITH coalesce(t, entity) AS targetTable
    WHERE targetTable:Table

    // 2. Find any tables referenced by the target table (borrowed from neo4j_setup.py)
    OPTIONAL MATCH (targetTable)-[:HAS_COLUMN]->()-[:REFERENCES]->()<-[:HAS_COLUMN]-(refTable:Table)
    WHERE targetTable.name <> refTable.name

    // 3. Combine the target table and its referenced tables into a single list
    WITH targetTable, collect(DISTINCT refTable) AS refTables
    WITH [targetTable] + refTables AS tablesToInclude
    UNWIND tablesToInclude AS tableNode

    // 4. Retrieve the full schema (all columns) for these tables
    MATCH (tableNode)-[:HAS_COLUMN]->(c:Column)
    
    // 5. Look up foreign key references for these columns to provide complete context
    OPTIONAL MATCH (c)-[:REFERENCES]->(targetCol:Column)<-[:HAS_COLUMN]-(targetRefTable:Table)

    // 6. Return the detailed schema structure rather than just the matched nodes
    RETURN DISTINCT
      tableNode.name AS TableName,
      tableNode.description AS TableDescription,
      c.name AS ColumnName,
      c.data_type AS DataType,
      coalesce(c.is_primary_key, false) AS IsPrimaryKey,
      c.description AS ColumnDescription,
      targetRefTable.name AS ReferencedTableName,
      targetCol.name AS ReferencedColumnName
    ORDER BY TableName, ColumnName;
    """

    parameters = {
        "query": query_text,
        "queryVector": query_vector,
        "sourceK": 30,
        "finalK": 10,
        "rrfConstant": 60.0,
        "sourceWeights": {"fulltext": 1.0, "vector": 1.0},
    }

    with GraphDatabase.driver(
        "neo4j://neo4j", auth=("neo4j", "&4kx3!7^d!<weZ9n")
    ) as driver:
        records, _, _ = driver.execute_query(cypher_query, **parameters)
        return encode([record.data() for record in records]).replace(r"\n", "\n")
