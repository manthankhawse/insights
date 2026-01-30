import uuid
import boto3
from fastapi import APIRouter, HTTPException, File, UploadFile, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy import create_engine, inspect
from db.models import Dataset, IngestionStatus, ConnectionSource, SourceType
from db.database import get_db  
from utils.process_dataset import process_dataset
import os
from pydantic import BaseModel

class ConnectionRequest(BaseModel):
    name: str
    connection_url: str

router = APIRouter(prefix="/api/ingest")
 
BUCKET_NAME = os.getenv("BUCKET_NAME")
s3_client = boto3.client(
    's3',
    endpoint_url=os.getenv("S3_URL"),
    aws_access_key_id=os.getenv("S3_USER"),         # Default MinIO username
    aws_secret_access_key=os.getenv("S3_PASS"),     # Default MinIO password
    region_name=os.getenv("S3_REGION")                # Boto3 often requires a region name
)

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...), 
    db: AsyncSession = Depends(get_db)
) -> dict: 
    filename = file.filename or "unknown"
    ext = filename.split('.')[-1].lower()
    if ext not in ['csv', 'xlsx', 'xls', 'parquet']:
        raise HTTPException(status_code=400, detail="Unsupported File Format")

    dataset_id = uuid.uuid4()
    s3_key = f"raw/{dataset_id}/{filename}"
 
    try: 
        s3_client.upload_fileobj(file.file, BUCKET_NAME, s3_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 Upload failed: {str(e)}")
 
    internal_table = f"data_{str(dataset_id).replace('-', '_')}"

    new_dataset = Dataset(
        id=dataset_id,
        display_name=filename,
        filename=filename,
        source_type=ext,
        s3_key=s3_key,            
        storage_table=internal_table,
        status=IngestionStatus.PENDING
    )
 
    try:
        db.add(new_dataset)
        await db.commit()
        await db.refresh(new_dataset)
        process_dataset(str(dataset_id))


    except Exception as e: 
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
 

    return {
        "id": str(new_dataset.id),
        "status": new_dataset.status,
        "storage_table": internal_table 
    }


@router.post("/connect-db")
async def connect_external_db(
    payload : ConnectionRequest,
    db: AsyncSession = Depends(get_db)
) -> dict:
    source_id = uuid.uuid4()

    s_type = SourceType.POSTGRES
    if "mysql" in payload.connection_url:
        s_type = SourceType.MYSQL
    
    new_source = ConnectionSource(
        id=source_id,
        name=payload.name,
        type=s_type,
        connection_url=payload.connection_url.strip()
    )
    
    db.add(new_source)
    await db.commit()
    return {"source_id": source_id, "status": "source_registered"}


@router.post("/mirror-table")
async def mirror_table(
    source_id: uuid.UUID,
    table_name: str,
    db: AsyncSession = Depends(get_db)
):
    dataset_id = uuid.uuid4()
    internal_table = f"data_{str(dataset_id).replace('-', '_')}"

    source = await db.get(ConnectionSource, source_id) 
    source_type = "mysql_table" if "mysql" in source.connection_url else "postgres_table"
    
    new_dataset = Dataset(
        id=dataset_id,
        display_name=table_name,
        source_id=source_id,
        source_type=source_type,
        storage_table=internal_table,
        status=IngestionStatus.PENDING
    )
    
    db.add(new_dataset)
    await db.commit()
    
    process_dataset(str(dataset_id))
    
    return {"dataset_id": dataset_id, "internal_table": internal_table}


@router.get("/connect-db/{source_id}/tables")
async def list_source_tables(source_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    source = await db.get(ConnectionSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    try:
        # Inject the appropriate driver into the connection URL
        connection_url = source.connection_url
        
        if connection_url.startswith("postgresql://"):
            connection_url = connection_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        elif connection_url.startswith("mysql://"):
            connection_url = connection_url.replace("mysql://", "mysql+pymysql://", 1)
        
        print(f"Original URL: {source.connection_url}")
        print(f"Modified URL: {connection_url}")
        
        temp_engine = create_engine(connection_url)
        inspector = inspect(temp_engine)
        tables = inspector.get_table_names()
        temp_engine.dispose()
        return {"tables": tables}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch tables: {str(e)}")