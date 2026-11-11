"""Object storage helpers (S3 API: SeaweedFS locally, any S3 in prod — ADR-009)."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

import boto3
from django.conf import settings


@cache
def s3():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name="us-east-1",
    )


def put_json(bucket: str, key: str, obj: Any) -> str:
    body = json.dumps(obj, indent=2, default=str).encode()
    s3().put_object(Bucket=bucket, Key=key, Body=body, ContentType="application/json")
    return f"s3://{bucket}/{key}"


def put_file(path: Path, bucket: str, key: str, content_type: str = "image/tiff") -> str:
    s3().upload_file(str(path), bucket, key, ExtraArgs={"ContentType": content_type})
    return f"s3://{bucket}/{key}"
