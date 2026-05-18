import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from fastapi import UploadFile
from app.core.config import settings
import logging
import os
import shutil

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.s3 = boto3.client('s3',
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY
        )
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        try:
            self.s3.head_bucket(Bucket=settings.S3_BUCKET_NAME)
        except ClientError:
            try:
                self.s3.create_bucket(Bucket=settings.S3_BUCKET_NAME)
                logger.info(f"Created bucket: {settings.S3_BUCKET_NAME}")
            except Exception as e:
                logger.error(f"Failed to create bucket: {e}")

    def clear_storage(self):
        """
        Clears all objects in the S3 bucket and local temp folder on server reload.
        """
        try:
            # 1. Clear S3 Bucket
            response = self.s3.list_objects_v2(Bucket=settings.S3_BUCKET_NAME)
            if 'Contents' in response:
                objects_to_delete = [{'Key': obj['Key']} for obj in response['Contents']]
                self.s3.delete_objects(
                    Bucket=settings.S3_BUCKET_NAME,
                    Delete={'Objects': objects_to_delete}
                )
                logger.info(f"Cleared {len(objects_to_delete)} files from S3 bucket: {settings.S3_BUCKET_NAME}")
                
            # 2. Clear Local Temp Files (DuckDB artifacts)
            # Use absolute path relative to project root
            temp_dir = "/home/vn-78/Projects/code/Entropy/test/temp"
            if os.path.exists(temp_dir):
                for filename in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete {file_path}. Reason: {e}")
                logger.info("Cleared local temp artifact directory.")
        except Exception as e:
            logger.error(f"Failed to clear storage: {e}")

    async def upload_file(self, file: UploadFile, object_name: str) -> str:
        """
        Uploads a file to S3/MinIO and returns the s3:// URI.
        """
        try:
            self.s3.upload_fileobj(file.file, settings.S3_BUCKET_NAME, object_name)
            # Return standard s3 URI format
            return f"s3://{settings.S3_BUCKET_NAME}/{object_name}"
        except NoCredentialsError:
            raise Exception("S3 Credentials not available")
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise Exception(f"Upload failed: {str(e)}")

storage_service = StorageService()
