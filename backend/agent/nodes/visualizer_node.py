import io
import json
import pandas as pd
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from agent.state import AgentState
from agent.nodes.router import llm

MAX_CHART_ROWS = 500


# ── The model sometimes puts the Vega-Lite keys flat at the tool-call level
# instead of nested under "spec". _VEGA_KEYS lets us detect and rescue that.
_VEGA_KEYS = {"mark", "encoding", "layer", "facet", "hconcat", "vconcat", "transform"}


class VegaLiteSpec(BaseModel):
    spec: dict = Field(
        ...,
        description=(
            "REQUIRED. Put the entire Vega-Lite v5 JSON object as the value of this 'spec' key. "
            "The object must have keys such as 'mark', 'encoding', 'width', 'height', 'config', 'data'. "
            "NEVER place 'mark', 'encoding', or 'config' at the top level of the tool call — "
            "they must always be nested inside the 'spec' object."
        ),
    )
    skip: bool = Field(
        False,
        description="Set true ONLY when the data is completely non-visualizable (e.g. a single text value).",
    )
    reason: str = Field("", description="If skip=true, one sentence explaining why.")


VEGA_SYSTEM_PROMPT = """\
You are a data visualization expert. Return a tool call with this exact structure:

{
  "spec": {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "data": {"name": "table"},
    "mark": ...,
    "encoding": {...},
    "width": "container",
    "height": 280,
    "config": {...}
  },
  "skip": false,
  "reason": ""
}

THE "spec" KEY IS MANDATORY. Never put "mark", "encoding", or "config" at the top level of the tool call.

CHART SELECTION:
- Category comparisons → bar
- Trends over time → line or area
- Distributions → histogram (bin transform) or boxplot
- Correlations → point (scatter)
- Part-to-whole → arc (pie/donut)
- Multiple metrics → layer or facet
- Rankings → sorted horizontal bar
- Heatmaps → rect with color encoding
- Honor explicit user requests for chart type

SPEC RULES:
1. "data": {"name": "table"} — always, never inline data
2. Use EXACT column names from the schema
3. "width": "container", "height": 280
4. Aggregate in the spec when needed (sum, mean, count, etc)
5. For time columns use timeUnit (year, month, yearmonth, date, etc)

ALWAYS include this config inside spec:
"config": {
  "background": "#111111",
  "view": {"stroke": "transparent"},
  "axis": {"gridColor": "#2a2a2a", "tickColor": "#3a3a3a", "labelColor": "#9ca3af",
           "titleColor": "#6b7280", "domainColor": "#2a2a2a", "labelFont": "monospace",
           "titleFont": "monospace", "labelFontSize": 11, "titleFontSize": 11},
  "legend": {"labelColor": "#9ca3af", "titleColor": "#6b7280",
             "labelFont": "monospace", "titleFont": "monospace", "labelFontSize": 11},
  "title": {"color": "#d1d5db", "font": "monospace", "fontSize": 12},
  "arc": {"stroke": "#111111", "strokeWidth": 1.5},
  "bar": {"cornerRadiusTopLeft": 3, "cornerRadiusTopRight": 3}
}

Colors: single-series → use {"value": "#60a5fa"} in color encoding.
Multi-series → "scheme": "category10".
"""


def _rescue_bare_spec(raw: dict) -> dict | None:
    """
    If the LLM placed Vega-Lite keys flat at the tool-call level instead of
    nesting them under 'spec', wrap them automatically.
    Returns the rescued spec dict, or None if it doesn't look like a Vega-Lite spec.
    """
    if not _VEGA_KEYS.intersection(raw.keys()):
        return None
    # Move all non-model keys into a spec wrapper
    rescued = {k: v for k, v in raw.items() if k not in ("skip", "reason")}
    if "data" not in rescued:
        rescued["data"] = {"name": "table"}
    print("📊 [Visualizer] Rescued bare spec from flat tool-call output.")
    return rescued


def generate_visuals(state: AgentState):
    """
    Calls the LLM to generate a Vega-Lite v5 spec from the SQL result.
    Appends { type: "chart", spec: {...}, data: [...] } to ui_blocks.
    """
    print("📊 [Visualizer] Generating Vega-Lite spec via LLM...")

    df_json  = state.get("df_json")
    messages = state.get("messages", [])

    if not df_json:
        print("📊 [Visualizer] No df_json — skipping.")
        return {}

    try:
        df = pd.read_json(io.StringIO(df_json), orient="split")
    except Exception as e:
        print(f"📊 [Visualizer] df deserialization failed: {e}")
        return {}

    if df.empty:
        print("📊 [Visualizer] Empty DataFrame — skipping.")
        return {}

    # Build schema description for the prompt
    schema_lines = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        samples = df[col].dropna().head(3).tolist()
        schema_lines.append(f"  - {col} ({dtype}): e.g. {samples}")
    schema_text = "\n".join(schema_lines)

    sample_text = json.dumps(df.head(10).to_dict(orient="records"), default=str, indent=2)

    user_question = ""
    for msg in reversed(messages):
        if hasattr(msg, "type") and msg.type == "human":
            user_question = msg.content
            break

    total_rows = len(df)

    human_prompt = (
        f'User question: "{user_question}"\n\n'
        f"Dataset schema ({total_rows} rows):\n{schema_text}\n\n"
        f"Sample (first 10 rows):\n{sample_text}\n\n"
        'Return the Vega-Lite spec nested under the "spec" key in the tool call.'
    )

    try:
        structured_llm = llm.with_structured_output(VegaLiteSpec)
        result: VegaLiteSpec = structured_llm.invoke([
            SystemMessage(content=VEGA_SYSTEM_PROMPT),
            HumanMessage(content=human_prompt),
        ])

        if result.skip:
            print(f"📊 [Visualizer] Skipping chart: {result.reason}")
            return {}

        spec = result.spec

    except Exception as e:
        error_str = str(e)
        print(f"📊 [Visualizer] Structured output failed: {error_str}")

        # ── Rescue attempt: extract the raw failed_generation JSON ────────────
        # Anthropic returns the raw tool-call JSON in the error message.
        # If the model put Vega-Lite keys flat, we can rescue them.
        try:
            import re
            # Pull the JSON blob out of the error message
            match = re.search(r"'failed_generation':\s*'<function=\w+>(\{.*\})'", error_str, re.DOTALL)
            if not match:
                # Try alternate format with double quotes
                match = re.search(r'"failed_generation":\s*"<function=\w+>(\{.*?\})"', error_str, re.DOTALL)
            if match:
                raw = json.loads(match.group(1))
                spec = _rescue_bare_spec(raw)
                if spec is None:
                    print("📊 [Visualizer] Rescue failed — not a recognizable Vega-Lite spec.")
                    return {}
                print("📊 [Visualizer] Rescue succeeded.")
            else:
                print("📊 [Visualizer] Could not extract raw spec from error — giving up.")
                return {}
        except Exception as rescue_err:
            print(f"📊 [Visualizer] Rescue attempt threw: {rescue_err}")
            return {}

    # Ensure data source is always the named dataset, not inline
    spec["data"] = {"name": "table"}

    chart_data = df.head(MAX_CHART_ROWS).to_dict(orient="records")
    chart_block = {
        "type": "chart",
        "spec": spec,
        "data": chart_data,
        "row_count": total_rows,
    }

    mark = spec.get("mark", "")
    mark_type = mark.get("type", mark) if isinstance(mark, dict) else mark
    print(f"📊 [Visualizer] Done. Mark type: {mark_type}")

    return {"ui_blocks": [chart_block]}