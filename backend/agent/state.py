import operator
from typing import Annotated, TypedDict, List, Dict, Optional, Any
from langchain_core.messages import BaseMessage

def append_block(left: List[Dict[str, Any]], right: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not left: left = []
    if not right: right = []
    return left + right

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    intent: str
    dataset_name: str
    artifact_url: str
    current_code: Optional[str]
    error_trace: Optional[str]
    attempt_count: int
    ui_blocks: Annotated[List[Dict[str, Any]], append_block]
    df_json: Optional[str]
