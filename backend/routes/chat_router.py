import uuid
from fastapi import APIRouter, HTTPException
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from agent.graph import data_agent
from db.db import AsyncSessionLocal
from db.models.data_source import DataSource

chat_router = APIRouter()

class ChatRequest(BaseModel):
    message: str

@chat_router.post("/chat")
async def hello():
    return {"message": "Chat"}

@chat_router.post("/chat/{source_id}")
async def chat(source_id: str, request: ChatRequest):
    print("source id ", source_id)
    async with AsyncSessionLocal() as session:
        try:
            source_uuid = uuid.UUID(source_id)  # Using a new variable prevents overwrite bugs
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid source_id")

        source = await session.get(DataSource, source_uuid)

        if not source:
            raise HTTPException(status_code=404, detail="Data source not found.")

    initial_state = {
        "messages": [HumanMessage(content=request.message)],
        "dataset_name": source.dataset_name,
        "artifact_url": source.artifact_url,
        "source_type": source.source_type,
        "ui_blocks": []
    }

    print(f"🚀 [API] Triggering agent for dataset: {source.dataset_name}")

    final_state = await data_agent.ainvoke(initial_state)

    return {
        "blocks": final_state.get("ui_blocks", [])
    }