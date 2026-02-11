from contextlib import asynccontextmanager
from fastapi import FastAPI
from db.db import init_db
from routes.chat_router import chat_router
from routes.ingest import router
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def life_span(app: FastAPI):
    print("Starting application...")
    await init_db()
    yield
    print("Stopping application...")

app = FastAPI(lifespan=life_span)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")

@app.get("/")
async def run_root():
    return {"message": "hello"}