from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any
from app.models import IngestionStatus

class DatasetBase(BaseModel):
    """Shared properties for Dataset"""
    display_name: str
    filename: Optional[str] = None

class DatasetCreate(DatasetBase):
    """Properties to receive on dataset creation (if not via file upload)"""
    source_id: Optional[UUID] = None
    source_type: str

class DatasetUpdate(BaseModel):
    """Properties to allow editing (e.g., renaming a dataset)"""
    display_name: Optional[str] = None
    status: Optional[IngestionStatus] = None

class DatasetModel(DatasetBase):
    """The public schema returned to the React frontend"""
    id: UUID
    status: IngestionStatus
    source_type: str
    
    # Metadata extracted by the Ingestion Engine
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    schema_metadata: Optional[Dict[str, Any]] = None 
    
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)