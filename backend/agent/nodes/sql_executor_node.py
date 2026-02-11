import pandas as pd
from agent.state import AgentState
from db.duck_db import get_duckdb_connection

MAX_TABLE_ROWS  = 100   # Rows shown in the frontend table block
MAX_VIZ_ROWS    = 500   # Rows passed to the visualizer node


def execute_sql_node(state: AgentState):
    """
    Executes the LLM-generated SQL query against the S3 parquet view.

    Produces:
    - ui_blocks: [sql code block, table block (capped)]
    - df_json:   compact JSON of the result (capped for viz) passed to generate_visuals
    """
    query        = state.get("current_code")
    artifact_url = state.get("artifact_url")
    s3_path      = f"s3://raw-data/{artifact_url}"

    print(f"⚙️ [SQL Executor] Running query...")

    con = get_duckdb_connection()

    try:
        con.execute(f"CREATE OR REPLACE VIEW data_table AS SELECT * FROM read_parquet('{s3_path}')")
        df = con.execute(query).df()
        df = df.where(df.notnull(), None)

        total_rows = len(df)

        # ── Table block (capped for client safety) ────────────────────────────
        df_display = df.head(MAX_TABLE_ROWS)
        records    = df_display.to_dict(orient="records")
        columns    = df.columns.tolist()

        warning = None
        if total_rows > MAX_TABLE_ROWS:
            warning = (
                f"Showing {MAX_TABLE_ROWS} of {total_rows:,} rows. "
                f"Ask for an aggregated view to see full trends."
            )

        ui_blocks = [
            {"type": "code",  "language": "sql", "content": query},
            {"type": "table", "columns": columns, "data": records, "warning": warning},
        ]

        # ── Pass a larger (but still capped) df to the visualizer ─────────────
        df_viz   = df.head(MAX_VIZ_ROWS)
        df_json  = df_viz.to_json(orient="split", date_format="iso")

        print(f"✅ [SQL Executor] {total_rows} rows returned.")
        return {
            "ui_blocks":   ui_blocks,
            "df_json":     df_json,
            "error_trace": None,
            "attempt_count": 0,
        }

    except Exception as e:
        print(f"❌ [SQL Executor] Crashed: {str(e)}")
        return {
            "ui_blocks":     [],
            "df_json":       None,
            "error_trace":   str(e),
            "attempt_count": state.get("attempt_count", 0) + 1,
        }
    finally:
        con.close()