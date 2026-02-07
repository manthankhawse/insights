from agent.state import AgentState


def synthesize_node(state: AgentState):
    print("Finalizing payload for frontend")

    if state.get("attempt_count", 0) >= 3:
        error_block = {
            "type": "markdown",
            "content": "⚠️ **Execution Failed:** I tried to analyze the data, but hit a persistent error. Please try rephrasing your request."
        }

        return {"ui_block": error_block}

    return {}