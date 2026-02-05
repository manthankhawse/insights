import boto3
from botocore.config import Config

MINIO_URL = 'http://localhost:9000' # Replace with your MinIO server address and port
ACCESS_KEY = 'minioadmin'       # Replace with your MinIO access key
SECRET_KEY = 'minioadmin'       # Replace with your MinIO secret key
REGION_NAME = 'us-east-1'

s3_client = boto3.client(
    's3',
    endpoint_url=MINIO_URL,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    config=Config(signature_version='s3v4'),
    region_name=REGION_NAME
)