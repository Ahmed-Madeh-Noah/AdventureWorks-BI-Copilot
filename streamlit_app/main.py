import pandas as pd
import streamlit as st
from get_context import retrieve_hybrid_context
from get_query import translate_to_sql
from sqlalchemy import create_engine, text

if "sql_response" not in st.session_state:
    st.session_state.sql_response = None
if "thinking" not in st.session_state:
    st.session_state.thinking = None

prompt = st.text_area("Prompt the copilot")

if st.button("Translate to SQL"):
    if not prompt:
        st.warning("Empty prompt")
    else:
        context = retrieve_hybrid_context(prompt)
        thinking, response = translate_to_sql(prompt, context)

        st.session_state.thinking = thinking
        st.session_state.sql_response = response

if st.session_state.sql_response is not None:
    st.write(st.session_state.thinking)

    edited_sql = st.text_area("SQL query", value=st.session_state.sql_response)

    if st.button("Query SQL"):
        if not edited_sql:
            st.warning("Empty query")
        else:
            engine = create_engine(
                "mssql+mssqlpython://dbgate_reader:ry7hhkRY9QB1dW68@mssql/AdventureWorks2025?TrustServerCertificate=yes"
            )
            with engine.connect() as conn:
                query = text(edited_sql)
                results_df = pd.read_sql_query(query, conn)
                st.dataframe(results_df)
