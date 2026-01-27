import redis
import fastexcel
from dotenv import load_dotenv
import os
import boto3
import io
import polars as pl
from sqlalchemy import create_engine 
from sqlalchemy.orm import sessionmaker
from db.models import Dataset, IngestionStatus, ConnectionSource

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
                    df = pl.read_csv(data_stream)
                elif dataset.source_type == 'parquet':
                    df = pl.read_parquet(data_stream)
                elif dataset.source_type in ['xlsx', 'xls']:
                    df = pl.read_excel(data_stream)
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
 
        schema_profiling = {
            col: {
                "type": str(dtype),
                "null_count": int(df[col].null_count()),
                "unique_count": int(df[col].n_unique())
            } for col, dtype in df.schema.items()
        }

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
