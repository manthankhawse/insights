from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage
from agent.state import AgentState
from agent.nodes.router import llm
from db.duck_db import get_duckdb_connection


class SQLGeneration(BaseModel):
    query: str = Field(..., description="A valid DuckDB SQL query.")


def fetch_schema(artifact_url: str) -> str:
    """Uses DuckDB to instantly read the schema metadata from MinIO without downloading the file."""
    con = get_duckdb_connection()
    s3_path = f"s3://raw-data/{artifact_url}"

    try:
        # DESCRIBE returns the column names and data types
        df = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{s3_path}')").df()
        schema_text = "\n".join([f"- {row['column_name']} ({row['column_type']})" for _, row in df.iterrows()])
        return schema_text, s3_path
    except Exception as e:
        return f"Error fetching schema: {str(e)}", s3_path
    finally:
        con.close()


def query_node(state: AgentState):
    """Fetches schema, injects it into prompt, and generates DuckDB SQL."""
    print("📝 [SQL Node] Fetching schema and generating query...")

    messages = state.get("messages", [])
    artifact_url = state.get("artifact_url")
    error_trace = state.get("error_trace")

    # 1. Fetch the real schema dynamically from MinIO
    schema_text, s3_path = fetch_schema(artifact_url)

    # 2. Build the System Prompt
    system_prompt = f"""
    You are an expert DuckDB SQL developer.

    CRITICAL RULES:
    1. The table you are querying is located at: '{s3_path}'
    2. Example syntax: SELECT column_a FROM read_parquet('{s3_path}') LIMIT 10;
    3. Return ONLY the valid SQL query. Do not use Markdown backticks.

    DATASET SCHEMA:
    {schema_text}
    """

    if error_trace:
        system_prompt += f"\n\n🚨 PREVIOUS ERROR TO FIX:\nYour last query failed with this error: {error_trace}\nRewrite the query to fix this."

    structured_llm = llm.with_structured_output(SQLGeneration)
    result = structured_llm.invoke([SystemMessage(content=system_prompt)] + messages)

    print(f"📝 [SQL Node] Generated Query:\n{result.query}")

    return {
        "current_code": result.query,
        "error_trace": None
    }