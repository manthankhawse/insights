from agent.state import AgentState
from db.duck_db import get_duckdb_connection


def execute_sql_node(state: AgentState):
    """Executes the LLM's DuckDB query directly against MinIO/S3."""
    query = state.get("current_code")

    print(f"⚙️ [SQL Executor] Running remote query over httpfs...")

    con = get_duckdb_connection()

    try:
        # Run the zero-copy query directly against the S3 path
        df = con.execute(query).df()

        # Format for Next.js
        df = df.where(df.notnull(), None)
        records = df.to_dict(orient="records")
        columns = df.columns.tolist()

        ui_blocks = [
            {"type": "code", "language": "sql", "content": query},
            {"type": "table", "columns": columns, "data": records}
        ]

        print("✅ [SQL Executor] Remote query successful.")
        return {
            "ui_blocks": ui_blocks,
            "error_trace": None,
            "attempt_count": 0
        }

    except Exception as e:
        print(f"❌ [SQL Executor] Query crashed: {str(e)}")
        return {
            "error_trace": str(e),
            "attempt_count": state.get("attempt_count", 0) + 1
        }
    finally:
        con.close()