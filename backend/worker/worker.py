import redis
import fastexcel
from dotenv import load_dotenv
import os
import boto3
import io
import polars as pl
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from db.models import Dataset, IngestionStatus, ConnectionSource
import uuid

load_dotenv()

DB_URL = os.getenv("DB_URL")

if DB_URL and DB_URL.startswith("postgresql+asyncpg"):
    SYNC_DB_URL = DB_URL.replace("postgresql+asyncpg", "postgresql")
else:
    SYNC_DB_URL = DB_URL

sync_engine = create_engine(SYNC_DB_URL)
SyncSessionLocal = sessionmaker(bind=sync_engine)


BUCKET_NAME = os.getenv("BUCKET_NAME")
s3_client = boto3.client(
    's3',
    endpoint_url=os.getenv("S3_URL"),
    aws_access_key_id=os.getenv("S3_USER"),         # Default MinIO username
    aws_secret_access_key=os.getenv("S3_PASS"),     # Default MinIO password
    region_name=os.getenv("S3_REGION")                # Boto3 often requires a region name
)




r = redis.Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), decode_responses=True)

def refine_types(df: pl.DataFrame) -> pl.DataFrame:
    """
    Attempts to fix common type issues Polars might miss during initial inference.
    """
    new_cols = []
    for col in df.columns:
        series = df[col]
        
        if series.dtype == pl.String:
            try:
                parsed = series.str.to_date(strict=False)
                if parsed.null_count() < (len(series) * 0.8):
                    new_cols.append(parsed.alias(col))
                    continue
            except:
                pass
        
        new_cols.append(series)
    
    return pl.DataFrame(new_cols)

def run_ingestion_pipeline(id: str):
    with SyncSessionLocal() as db: 
        dataset = db.get(Dataset, id)
        if not dataset:
            print(f"❓ Dataset {id} not found in DB. Skipping.")
            return

        dataset.status = IngestionStatus.PROCESSING
        db.commit()
 
        if dataset.source_type in ['csv', 'parquet', 'xlsx', 'xls']:
                print(f"📥 Downloading file from S3: {dataset.s3_key}")
                s3_obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=dataset.s3_key)
                data_stream = io.BytesIO(s3_obj['Body'].read())

                if dataset.source_type == 'csv':
                    df = pl.read_csv(data_stream, 
                                    null_values=["NA", "N/A", "null", ""], 
                                    infer_schema_length=10000
                                    try_parse_dates=True)
                elif dataset.source_type == 'parquet':
                    df = pl.read_parquet(data_stream)
                elif dataset.source_type in ['xlsx', 'xls']:
                    df = pl.read_excel(data_stream, infer_schema_length=10000)
        elif dataset.source_type in ["postgres_table", "mysql_table", "clickhouse_table"]:
            source = db.get(ConnectionSource, dataset.source_id)
            query = f"SELECT * FROM {dataset.display_name}"
            try:
        # Convert SQLAlchemy URL to connectorx-compatible format
                clean_url = source.connection_url.strip()
        
        # Polars read_database uses connectorx which needs specific formats
                connectorx_url = clean_url
                if "mysql+pymysql://" in connectorx_url:
                    connectorx_url = connectorx_url.replace("mysql+pymysql://", "mysql://")
                elif "postgresql+asyncpg://" in connectorx_url:
                    connectorx_url = connectorx_url.replace("postgresql+asyncpg://", "postgresql://")
                elif "postgresql+psycopg2://" in connectorx_url:
                    connectorx_url = connectorx_url.replace("postgresql+psycopg2://", "postgresql://")
        
                print(f"🔗 Attempting to connect to: {connectorx_url}")
                df = pl.read_database_uri(
                        query=query, 
                        uri=connectorx_url  # Pass string, not engine
                    )
            except Exception as e:
                print(f"❌ Connection failed for {dataset.source_type}: {e}")
                dataset.status = IngestionStatus.FAILED
                db.commit()
                return
        else:
            print(f"❌ Unknown format: {dataset.source_type}")
            return

        df = refine_types(df)
        total_rows = df.height

        schema_profiling = {}

        for col in df.columns:
            series = df[col]
            dtype = series.dtype
            
            # Basic Stats
            null_count = int(series.null_count())
            unique_count = int(series.n_unique())
            
            stats = {
                "type": str(dtype),
                "null_count": null_count,
                "null_pct": round((null_count / total_rows) * 100, 2) if total_rows > 0 else 0,
                "unique_count": unique_count,
                "is_likely_id": unique_count == total_rows and dtype.is_integer(),
                "is_categorical": unique_count < 20 and unique_count < (total_rows * 0.1),
                "is_constant": unique_count == 1
            }

            # Numeric-specific inference (for outlier detection context)
            if dtype.is_numeric():
                stats["min"] = float(series.min()) if series.min() is not None else None
                stats["max"] = float(series.max()) if series.max() is not None else None
                stats["mean"] = float(series.mean()) if series.mean() is not None else None
            
            stats["sample"] = series.slice(0, 5).to_list()
            
            schema_profiling[col] = stats

        df.write_database(
            table_name=dataset.storage_table,
            connection=sync_engine,
            if_table_exists="replace"
        )

        dataset.status = IngestionStatus.COMPLETED
        dataset.row_count = df.height
        dataset.column_count = df.width
        dataset.schema_metadata = schema_profiling
        db.commit()
        print(f"✅ Dataset {id} is ready.")

def ingestion_worker():
    while True:
        _, dataset_id = r.brpop('datasource', 0)
        try:
            run_ingestion_pipeline(dataset_id)
        except Exception as e:
            print(f"❌ Failed to process {dataset_id}: {e}")



if __name__ == "__main__":
    ingestion_worker()
