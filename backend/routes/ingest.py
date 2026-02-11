import hashlib
import os
import shutil
import uuid

import duckdb
import pandas as pd
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from botocore.exceptions import ClientError
from sqlalchemy import select

from db.db import AsyncSessionLocal
from db.models.data_source import DataSource
from s3.client import s3_client
from schemas.uploads import DataIngestRequest, SourceType

router = APIRouter()

duckdb_con = duckdb.connect(database=':memory:')

def convert_csv_to_parquet(path: str, out: str):
    attempts = [
        "read_csv_auto('{p}', sample_size=-1, ignore_errors=true, null_padding=true)",
        "read_csv('{p}', delim=',', header=true, strict_mode=false, ignore_errors=true)",
        "read_csv('{p}', delim=';', header=true, strict_mode=false, ignore_errors=true)",
        "read_csv('{p}', delim='|', header=true, strict_mode=false, ignore_errors=true)",
    ]

    for expr in attempts:
        try:
            duckdb_con.execute(f"""
                COPY (
                  SELECT * FROM {expr.format(p=path)}
                )
                TO '{out}' (FORMAT 'PARQUET', CODEC 'SNAPPY')
            """)
            return
        except Exception:
            pass

    raise Exception("CSV parsing failed for all known dialects")


def save_upload_to_temp(file: UploadFile, filename: str) -> str:
    temp_dir = "temp_storage"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, filename)

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return temp_path


def convert_to_parquet(source_path: str, source_type: SourceType) -> str:
    parquet_path = source_path + ".parquet"

    if not os.path.exists(source_path):
        raise HTTPException(status_code=400, detail="File upload failed internally.")

    try:
        if source_type == SourceType.CSV:
            safe_path = source_path.replace("'", "''")
            safe_out = parquet_path.replace("'", "''")
            # query = f"COPY (SELECT * FROM read_csv_auto('{safe_path}', sample_size=-1, ignore_errors=true, null_padding=true)) TO '{safe_out}' (FORMAT 'PARQUET', CODEC 'SNAPPY')"
            # duckdb_con.execute(query)
            convert_csv_to_parquet(safe_path, safe_out)

        elif source_type == SourceType.JSON:
            safe_path = source_path.replace("'", "''")
            safe_out = parquet_path.replace("'", "''")
            query = f"COPY (SELECT * FROM read_json_auto('{safe_path}')) TO '{safe_out}' (FORMAT 'PARQUET', CODEC 'SNAPPY')"
            duckdb_con.execute(query)

        elif source_type == SourceType.EXCEL:
            df = pd.read_excel(source_path)
            df.to_parquet(parquet_path, index=False)

        return parquet_path

    except Exception as e:
        if os.path.exists(parquet_path):
            os.remove(parquet_path)
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


def process_ingestion(file_path: str, metadata: DataIngestRequest) -> str:
    """
    Hashes the file on disk and uploads to S3.
    """
    print(f"✅ Ready to ingest {metadata.dataset_name} from {file_path}")

    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256_hash.update(chunk)

    remote_file_name = f"{sha256_hash.hexdigest()}.parquet"
    bucket_name = 'raw-data'

    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError:
        try:
            s3_client.create_bucket(Bucket=bucket_name)
        except Exception as e:
            print(f"Error creating bucket: {e}")

    try:
        s3_client.upload_file(file_path, bucket_name, remote_file_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 Upload failed: {e}")

    return remote_file_name


@router.get("/data")
async def get_all_sources():
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(DataSource)

            # 2. Execute and fetch all scalar results
            result = await session.execute(stmt)
            sources = result.scalars().all()

            # 3. Serialize to JSON-friendly dictionaries
            return [
                {
                    "id": str(source.id),
                    "name": source.dataset_name,
                    "type": source.source_type.upper() if source.source_type else "FILE",
                    # Format the date nicely for the UI (fallback to "Recently" if missing)
                    "uploaded": source.created_at.strftime("%b %d, %Y") if hasattr(source,
                                                                                   'created_at') and source.created_at else "Recently",
                    "status": "Ready",
                    "rows": "Unknown",  # We'll calculate these dynamically in the Python sandbox later
                    "size": "--"
                }
                for source in sources
            ]

    except HTTPException as he:
        raise he


@router.get("/data/{source_id}")
async def get_all_sources(source_id: str):
    try:
        async with AsyncSessionLocal() as session:
            try:
                source_uuid = uuid.UUID(source_id)  # Using a new variable prevents overwrite bugs
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid source_id")

            source = await session.get(DataSource, source_uuid)

            return source
    except HTTPException as he:
        raise he


@router.post("/upload")
async def upload(
        file: UploadFile = File(None),
        metadata_json: str = Form(..., description="JSON string of DataIngestRequest model")
):
    try:
        req_data = DataIngestRequest.model_validate_json(metadata_json)
        artifact_url = ""

        if req_data.source_type in [SourceType.POSTGRES_DB, SourceType.MYSQL_DB]:
            if not req_data.connection_string:
                raise HTTPException(status_code=400, detail="Connection string required for Database Source")

            print(f"✅ Registered Database Source: {req_data.dataset_name}")

        else:
            if not file:
                raise HTTPException(status_code=400,
                                    detail=f"File upload required for source type {req_data.source_type}")

            raw_file_path = save_upload_to_temp(file, file.filename)
            final_path = raw_file_path

            try:
                if req_data.source_type != SourceType.PARQUET:
                    final_path = convert_to_parquet(raw_file_path, req_data.source_type)

                artifact_url = process_ingestion(final_path, req_data)

            finally:
                if os.path.exists(raw_file_path):
                    os.remove(raw_file_path)
                if final_path != raw_file_path and os.path.exists(final_path):
                    os.remove(final_path)

        async with AsyncSessionLocal() as session:
            new_source = DataSource(
                dataset_name=req_data.dataset_name,
                description=req_data.description,
                source_type=req_data.source_type,
                artifact_url=artifact_url,
                ingestion_config=req_data.ingestion_config,
                connection_string=req_data.connection_string
            )
            session.add(new_source)
            await session.commit()
            await session.refresh(new_source)

        return {
            "status": "success",
            "id": str(new_source.id),
            "type": req_data.source_type,
            "message": "Source registered successfully."
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))