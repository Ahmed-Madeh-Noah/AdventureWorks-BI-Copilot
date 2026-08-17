from contextlib import asynccontextmanager

import anyio
from dotenv import load_dotenv
from fastapi import Body, FastAPI, Request
from mssql_python import connect
from pydantic_settings import BaseSettings
from toon_format import encode


class Settings(BaseSettings):
    mssql_server: str
    mssql_port: str
    mssql_database: str
    mssql_context_retriever_reader_username: str
    mssql_context_retriever_reader_password: str

    @property
    def sql_connection_str(self) -> str:
        return (
            f"Server={self.mssql_server},{self.mssql_port};"
            f"Database={self.mssql_database};"
            f"UID={self.mssql_context_retriever_reader_username};"
            f"PWD={self.mssql_context_retriever_reader_password};"
            "Encrypt=yes;TrustServerCertificate=yes"
        )


load_dotenv()
settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_schema = ""
    conn = connect(settings.sql_connection_str)
    cursor = conn.cursor()

    try:
        get_db_schema_path = anyio.Path("./get_db_schema.sql")
        assert await get_db_schema_path.is_file(), (
            "DB schema getter query file not found"
        )
        async with await anyio.open_file(
            await get_db_schema_path.resolve()
        ) as get_db_schema_file:
            get_db_schema_query = await get_db_schema_file.read()
            cursor.execute(get_db_schema_query)
            assert cursor.description is not None, "Query description not found."
            column_names = tuple(column[0] for column in cursor.description)
            rows = [tuple(row) for row in cursor.fetchall()]
            records = [column_names] + rows
            app.state.db_schema = encode(records)
    finally:
        cursor.close()
        conn.close()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health/live")
async def liveness_check():
    return {"status": "alive"}


@app.post("/retrieve-relevant-context")
async def root(request: Request, query: str = Body(...)) -> str:
    return request.app.state.db_schema
