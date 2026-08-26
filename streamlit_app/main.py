import streamlit as st
from utils import execute_sql_query, get_context, infer_sql

if "sql_response" not in st.session_state:
    st.session_state.sql_response = None

prompt = st.text_area("Prompt the copilot")

if st.button("Translate to SQL"):
    if not prompt:
        st.warning("Empty prompt")
    else:
        context = get_context(prompt)
        response = infer_sql(prompt, context)

        st.session_state.sql_response = response

if st.session_state.sql_response is not None:
    edited_sql = st.text_area("SQL query", value=st.session_state.sql_response)

    if st.button("Query SQL"):
        if not edited_sql:
            st.warning("Empty query")
        else:
            results_df = execute_sql_query(edited_sql)
            if isinstance(results_df, str):
                st.warning(results_df)
            else:
                st.dataframe(results_df)
