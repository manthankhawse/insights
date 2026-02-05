import uuid
from typing import Dict, Optional, Any
from sqlmodel import SQLModel, Field
from sqlalchemy import JSON, Column
from schemas.uploads import SourceType


class DataSource(SQLModel, table=True):
    __tablename__ = "data_sources"
    id: uuid.UUID = Field(
        primary_key=True,
        default_factory=uuid.uuid4
    )
    dataset_name: str = Field(..., description="Unique name for this dataset")
    description: Optional[str] = Field(None, description="Natural language description")
    source_type: SourceType
    artifact_url: Optional[str] = None
    ingestion_config: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON)
    )
    connection_string: Optional[str] = Field(None, description="SQLAlchemy URL or Google Sheet ID")