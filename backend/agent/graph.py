from langgraph.graph import StateGraph, END
from pydantic import BaseModel

from agent.nodes.chat import chat_node
from agent.nodes.generator import generate_code_node
from agent.nodes.query_node import query_node
from agent.nodes.router import router_node, route_to_specialist
from agent.nodes.sandbox import execute_sandbox_node
from agent.nodes.sql_executor_node import execute_sql_node
from agent.nodes.synthesizer import synthesize_node
from agent.nodes.visualizer_node import generate_visuals
from agent.state import AgentState


def check_execution(state: AgentState)->str:
    if state.get("error_trace"):
        if state.get("attempt_count", 0) >= 3:
            return "end"
        return "rewrite_code"

    return "success"

def check_sql_execution(state: AgentState) -> str:
    """Checks SQL execution."""
    if state.get("error_trace"):
        if state.get("attempt_count", 0) >= 3:
            return "fail"
        return "rewrite_sql"
    return "success"

workflow = StateGraph(AgentState)

workflow.add_node("router", router_node)
workflow.add_node("chat", chat_node)
workflow.add_node("sql", query_node)
workflow.add_node("sql_executor", execute_sql_node)
workflow.add_node("visualizer", generate_visuals)
workflow.add_node("generator", generate_code_node)
workflow.add_node("executor", execute_sandbox_node)
workflow.add_node("synthesizer", synthesize_node)

workflow.set_entry_point("router")
workflow.add_edge("chat", "synthesizer")
workflow.add_edge("sql", "sql_executor")
workflow.add_edge("visualizer", "synthesizer")
workflow.add_edge("generator", "executor")

workflow.add_conditional_edges(
    "router",
    route_to_specialist,
    {
        "chat": "chat",
        "sql": "sql",
        "python": "generator"
    }
)
workflow.add_conditional_edges(
    "executor",
    check_execution,
    {
        "rewrite_code": "generator",
        "success": "synthesizer",
        "end": "synthesizer"
    }
)
workflow.add_conditional_edges(
    "sql_executor",
    check_sql_execution,
    {"rewrite_sql": "sql", "success": "visualizer", "fail": "synthesizer"}
)

workflow.add_edge("synthesizer", END)

data_agent = workflow.compile()