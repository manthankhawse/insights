from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from agent.state import AgentState
from agent.nodes.router import llm
from db.duck_db import get_duckdb_connection

class SQLGeneration(BaseModel):
    query: str = Field(..., description="A valid DuckDB SQL query.")

def fetch_schema(artifact_url: str) -> str:
    """Uses DuckDB to instantly read the schema metadata from MinIO."""
    con = get_duckdb_connection()
    s3_path = f"s3://raw-data/{artifact_url}"
    try:
        df = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{s3_path}')").df()
        schema_text = "\n".join([f"- {row['column_name']} ({row['column_type']})" for _, row in df.iterrows()])
        return schema_text
    except Exception as e:
        return f"Error fetching schema: {str(e)}"
    finally:
        con.close()

def query_node(state: AgentState):
    """Fetches schema and generates standard SQL."""
    print("📝 [SQL Node] Fetching schema and generating query...")

    messages = state.get("messages", [])
    artifact_url = state.get("artifact_url")
    error_trace = state.get("error_trace")

    schema_text = fetch_schema(artifact_url)

    # --- THE CLEAN ABSTRACTION PROMPT ---
    system_prompt = f"""
    You are an expert SQL developer. 

    CRITICAL RULES:
    1. You are querying a table named exactly: data_table
    2. Write standard SQL queries (e.g., SELECT, DESCRIBE, PRAGMA) against 'data_table'.
    3. Return ONLY the valid SQL query. Do not use Markdown backticks.

    DATASET SCHEMA:
    {schema_text}
    """

    if error_trace:
        system_prompt += f"\n\n🚨 PREVIOUS ERROR TO FIX:\nYour last query failed with this error: {error_trace}\nRewrite the query to fix this."

    structured_llm = llm.with_structured_output(SQLGeneration)
    result = structured_llm.invoke([SystemMessage(content=system_prompt)] + messages)

    print(f"📝 [SQL Node] Generated Query: {result.query}")

    return {
        "current_code": result.query,
        "error_trace": None
    }