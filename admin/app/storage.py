import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import settings


def get_minio_client():
    protocol = "https" if settings.minio_use_ssl else "http"
    return boto3.client(
        "s3",
        endpoint_url=f"{protocol}://{settings.minio_endpoint}",
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket_exists(client, bucket: str):
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError:
        client.create_bucket(Bucket=bucket)
