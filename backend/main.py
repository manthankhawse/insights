from fastapi import FastAPI
from dotenv import load_dotenv
from db.database import get_db 
from routes import ingest, dataset
import os

load_dotenv()


app = FastAPI()

app.include_router(dataset.router)
app.include_router(ingest.router)

@app.get("/")
async def func():
    return {"message": "Hello world"} 

@app.get("/greet/{name}")
async def func(name: str) -> dict :
    print(name)
    return {"message": "Hello world"} 


