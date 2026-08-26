import re
import streamlit as st
from utils import (
    execute_sql_query,
    get_context,
    get_subgraph_vg,
    infer_sql,
)
from neo4j_viz.streamlit import display_widget
from code_editor import code_editor

# Set the page configuration for a modern look
st.set_page_config(page_title="AdventureWorks BI Copilot", layout="wide")


def clean_sql_markdown(text: str) -> str:
    """Strips markdown formatting from the LLM output if validation failed."""
    match = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    text = text.strip()
    if text.startswith("```sql"):
        text = text[6:].strip()
    elif text.startswith("```"):
        text = text[3:].strip()
    if text.endswith("```"):
        text = text[:-3].strip()
    return text


# Initialize session state variables to hold our data between reruns
if "sql_response" not in st.session_state:
    st.session_state.sql_response = None
if "search_tables" not in st.session_state:
    st.session_state.search_tables = None
if "context_tables" not in st.session_state:
    st.session_state.context_tables = None
if "context" not in st.session_state:
    st.session_state.context = None

# Header Section
st.title("AdventureWorks BI Copilot")
st.markdown(
    "Translate your natural language business questions into precise SQL queries using a semantic Knowledge Graph."
)
st.divider()

# Prompt Area inside an st.form
with st.form("prompt_form"):
    col1, col2 = st.columns([4, 1])
    with col1:
        prompt = st.text_area(
            "Ask your data a question:",
            placeholder="e.g., Get the account descriptions for all accounts where the account type is 'Assets'.",
            height=100,
            label_visibility="collapsed",
        )
    with col2:
        st.write("")
        st.write("")
        translate_btn = st.form_submit_button(
            "Translate to SQL", type="primary", use_container_width=True
        )

# Action: Translate to SQL
if translate_btn:
    if not prompt:
        st.warning("Please enter a prompt first.")
    else:
        # Phase A: Retrieve context
        with st.spinner("Searching schema knowledge graph..."):
            context, search_tables, context_tables = get_context(prompt)
            st.session_state.search_tables = search_tables
            st.session_state.context_tables = context_tables
            st.session_state.context = context

            # Set a flag to trigger Phase B after the UI updates
            st.session_state.pending_llm_prompt = prompt

        # Rerun immediately to render the graphs on screen
        st.rerun()

# Sequential Rendering for Graphs
# Sequential Rendering for Graphs
if st.session_state.search_tables is not None:
    st.subheader("Search Results Graph")
    search_vg = get_subgraph_vg(st.session_state.search_tables)
    display_widget(search_vg.render_widget(), key="search_graph")

if st.session_state.context_tables is not None:
    st.subheader("Context Results Graph (1-Hop Expansion)")
    context_vg = get_subgraph_vg(st.session_state.context_tables)
    display_widget(context_vg.render_widget(), key="context_graph")

# Phase B: Perform LLM inference AFTER graphs are rendered
if st.session_state.get("pending_llm_prompt"):
    prompt = st.session_state.pending_llm_prompt
    with st.spinner("Generating T-SQL query with LLM..."):
        response = infer_sql(prompt, st.session_state.context)
        st.session_state.sql_response = response

    # Clear the flag so we don't run the LLM again
    st.session_state.pending_llm_prompt = None

    # Rerun to reveal the code editor area with the new SQL
    st.rerun()

# SQL editing area
if st.session_state.sql_response is not None:
    st.divider()
    # ... rest of your code ...    st.subheader("Generated SQL Query")
    st.markdown(
        "Review and edit the generated query below. Click **▶ Run Query** inside the editor to execute."
    )

    cleaned_sql = clean_sql_markdown(st.session_state.sql_response)

    # Create a custom button for the code editor
    custom_buttons = [
        {
            "name": "Run Query",
            "feather": "Play",
            "primary": True,
            "hasText": True,
            "showWithIcon": True,
            "commands": ["submit"],
            "style": {"bottom": "15px", "right": "15px"},
        }
    ]

    # Render the code editor with the custom button
    response_dict = code_editor(
        cleaned_sql,
        lang="sql",
        height=[10, 25],
        shortcuts="vscode",
        buttons=custom_buttons,
    )

    # Execute the query ONLY when the editor's submit button is clicked
    if response_dict.get("type") == "submit":
        current_sql = response_dict.get("text", "")

        if not current_sql.strip():
            st.warning("SQL query cannot be empty.")
        else:
            with st.spinner("Executing query against SQL Server..."):
                results_df = execute_sql_query(current_sql)

                st.subheader("Query Results")
                if isinstance(results_df, str):
                    st.error(f"Execution Error: {results_df}")
                else:
                    st.dataframe(results_df, use_container_width=True)
