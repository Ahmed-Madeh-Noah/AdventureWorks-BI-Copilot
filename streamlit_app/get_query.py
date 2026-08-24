import ollama


def translate_to_sql(prompt, context) -> tuple[str, str]:
    ollama_client = ollama.Client(host="http://ollama:11434")
    prompt = f"THIS IS THE QUESTION TO ANSWER --> {prompt} <--"
    prompt += f"""
                Use the following database schema information:
                {context}
               """
    system = """
             You are an expert database assistant specializing in Microsoft SQL Server and T-SQL. Your task is to translate natural language user prompts into accurate, efficient, and executable SQL Server queries based on the provided database schema.
             ### Guidelines

             * **Dialect:** Write valid **Microsoft SQL Server (T-SQL)** syntax.
             * **Schema Accuracy:** Strictly use only the tables, columns, and relationships defined in the attached schema context.
             * **Formatting:** Return **only** the SQL query with no formatting. Do not include conversational filler, or markdown.
             * **Best Practices:** Use appropriate joins, aliases, and aggregate functions where necessary to accurately fulfill the user's request.

             Example Input: <Query>

             Example Output:
                
                <SQL>
                Select * from Products
                </SQL>

             """
    generated_response = ollama_client.generate(
        "qwen2.5-coder:3b-instruct-q8_0",
        prompt,
        system=system,
        think=False,
        options={"seed": 42, "temperature": 0.0},
    )
    # assert generated_response.thinking is not None
    assert generated_response.response is not None
    return generated_response.thinking, generated_response.response
