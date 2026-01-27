import uuid
import enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, JSON, text
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlmodel import SQLModel, Field, Relationship


class IngestionStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class SourceType(str, enum.Enum):
    FILE = "file"
    POSTGRES = "postgres"
    MYSQL = "mysql"
    CLICKHOUSE = "clickhouse"

class ConnectionSource(SQLModel, table=True):
    
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4, 
        primary_key=True
    )
    name: str = Field(index=True)
    type: SourceType = Field(
        sa_column=Column(ENUM(SourceType, name="source_type_enum"))
    )
    connection_url: str 
    
    # Relationship to datasets
    datasets: List["Dataset"] = Relationship(back_populates="source")

class Dataset(SQLModel, table=True):

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(UUID(as_uuid=True), primary_key=True)
    )
    display_name: str
    filename: Optional[str] = None
    source_type: str 
    
    status: IngestionStatus = Field(
        default=IngestionStatus.PENDING,
        sa_column=Column(
            ENUM(IngestionStatus, name="ingestion_status_enum"),
            index=True
        )
    )

    # Storage pointers
    s3_key: Optional[str] = None
    storage_table: str = Field(unique=True, index=True)

    # Foreign Key to ConnectionSource
    source_id: Optional[uuid.UUID] = Field(
        default=None, 
        foreign_key=f"connectionsource.id"
    )
    source: Optional["ConnectionSource"] = Relationship(back_populates="datasets")

    # Profiling data
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    schema_metadata: Optional[Dict[str, Any]] = Field(
        default=None, 
        sa_column=Column(JSON)
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"onupdate": text("now()")}
    )