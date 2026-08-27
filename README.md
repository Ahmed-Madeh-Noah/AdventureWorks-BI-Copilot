# AdventureWorks-BI-Copilot

![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)
![Docker](https://img.shields.io/badge/docker-compose-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## What the project does
AdventureWorks-BI-Copilot is an intelligent, privacy-focused Business Intelligence copilot for the AdventureWorks database. It uses a knowledge graph as a semantic metadata layer to translate natural language questions into precise database queries, enabling seamless enterprise analytics without exposing underlying tabular data.

## Why the project is useful
* **Privacy-First Architecture**: Utilizes local Ollama models (`qwen3.5`, `qwen3-embedding`, `qwen2.5-coder`) for NLP embedding and SQL translation, ensuring your data never leaves your environment.
* **Semantic Knowledge Graph**: Uses Neo4j to map database schemas (Tables, Columns, Primary/Foreign Keys), creating an intelligent context-retrieval system that feeds accurate schema segments to the LLM.
* **Interactive UI**: Features a robust Streamlit application allowing users to input natural language questions, visualize the underlying context graph, and review, edit, or execute the generated T-SQL in an integrated code editor.
* **Ready-to-Use Data Environment**: Spins up an entire MS SQL Server instance loaded with the AdventureWorks dataset, accompanied by DbGate for standard database administration.

## How users can get started

### Prerequisites
* Docker and Docker Compose
* Git

### Installation & Setup

1. **Clone the repository**
    ```bash
    git clone https://github.com/Ahmed-Madeh-Noah/AdventureWorks-BI-Copilot.git
    cd AdventureWorks-BI-Copilot
    ```

2. **Configure Environment Variables**
    Copy the provided template to create your `.env` file.
    ```bash
    cp .env.example .env
    ```
    Open the `.env` file and populate the necessary passwords and port configurations for MS SQL Server, Neo4j, DbGate, and Streamlit.


3. **Launch the Application stack**
    Use Docker Compose to build and spin up the services.
    ```bash
    docker compose up -d
    ```
    *Note: On the first run, the `ollama_setup` and `neo4j_setup` containers will pull the necessary models and build the Neo4j knowledge graph from the MS SQL schema. Wait a few moments for these setup tasks to complete*.

### Usage Example

Once the containers are healthy, navigate to your Streamlit port (e.g., `http://localhost:80`) in your browser.
Try asking natural language questions such as:
* "Get the account descriptions for all accounts where the account type is 'Assets'."
* "Group the customers by their marital status and count how many fall into each category."
The Copilot will search the schema knowledge graph, generate the required T-SQL, and allow you to execute the query against the MS SQL server directly from the interface.
