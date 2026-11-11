import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the object-storage buckets (COGs, media) if missing. Idempotent."

    def handle(self, *args, **opts):
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name="us-east-1",
        )
        for bucket in (settings.S3_BUCKET_COG, settings.S3_BUCKET_MEDIA):
            try:
                s3.head_bucket(Bucket=bucket)
            except ClientError:
                s3.create_bucket(Bucket=bucket)
                self.stdout.write(f"created bucket {bucket}")
        self.stdout.write(self.style.SUCCESS("buckets ready"))
