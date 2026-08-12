from os import getenv

from dotenv import load_dotenv
from mssql_python import connect


def get_sql_connection_str() -> str:
    load_dotenv()
    server = getenv("MSSQL_SERVER")
    assert server is not None, "Could not find MSSQL_SERVER environment variable."
    port = getenv("MSSQL_PORT")
    assert port is not None, "Could not find MSSQL_PORT environment variable."
    database = getenv("MSSQL_DATABASE")
    assert database is not None, "Could not find MSSQL_DATABASE environment variable."
    username = getenv("MSSQL_CONTEXT_RETRIEVER_READER_USERNAME")
    assert username is not None, (
        "Could not find MSSQL_CONTEXT_RETRIEVER_READER_USERNAME environment variable."
    )
    password = getenv("MSSQL_CONTEXT_RETRIEVER_READER_PASSWORD")
    assert password is not None, (
        "Could not find MSSQL_CONTEXT_RETRIEVER_READER_PASSWORD environment variable."
    )
    sql_connection_str = f"Server={server},{port};"
    sql_connection_str += f"Database={database};"
    sql_connection_str += f"UID={username};"
    sql_connection_str += f"PWD={password};"
    sql_connection_str += "Encrypt=yes;TrustServerCertificate=yes"
    return sql_connection_str


def main() -> None:
    sql_connection_str = get_sql_connection_str()
    with (
        connect(sql_connection_str) as conn,
        conn.cursor() as cursor,
        open("./get_db_schema.sql") as get_db_schema_file,
    ):
        get_db_schema_query = get_db_schema_file.read()
        cursor.execute(get_db_schema_query)
        records = cursor.fetchall()
        for r in records:
            print(r)


if __name__ == "__main__":
    main()
