from sqlalchemy import text, select
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import get_db  
import uuid
from db.models import Dataset, IngestionStatus, ConnectionSource, SourceType

router = APIRouter(prefix="/api/dataset")

@router.get("/")
async def list_datasets(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Dataset))
    return res.scalars().all()

@router.get("/{dataset_id}/preview")
async def get_dataset_preview(
    dataset_id: uuid.UUID, 
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
) -> dict:
    # 1. Fetch the metadata to find the internal table name
    dataset = await db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    if dataset.status != IngestionStatus.COMPLETED:
        return {
            "status": dataset.status,
            "message": "Dataset is still processing or failed.",
            "data": []
        }

    # 2. Dynamically query the storage table
    # We use text() for raw SQL, and quoting the table name to prevent injection
    query = text(f'SELECT * FROM "{dataset.storage_table}" LIMIT :limit')
    
    try:
        result = await db.execute(query, {"limit": limit})
        # Convert rows to a list of dictionaries for JSON response
        columns = result.keys()
        data = [dict(zip(columns, row)) for row in result.fetchall()]
        
        return {
            "id": dataset.id,
            "display_name": dataset.display_name,
            "columns": list(columns),
            "data": data,
            "total_rows": dataset.row_count,
            "schema": dataset.schema_metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch preview: {str(e)}")