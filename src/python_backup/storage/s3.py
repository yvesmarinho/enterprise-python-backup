"""
AWS S3 storage implementation.

Handles backup storage operations on AWS S3 including upload, download,
listing, and deletion of backup files.
"""

import logging
import boto3
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import fnmatch

logger = logging.getLogger(__name__)


class S3Storage:
    """
    AWS S3 storage for backups.
    
    Provides methods to store, retrieve, list, and delete backup files
    on AWS S3.
    """
    
    def __init__(self, bucket: str, region: str, access_key: str, 
                 secret_key: str, prefix: str = ""):
        """
        Initialize S3 storage.
        
        Args:
            bucket: S3 bucket name
            region: AWS region
            access_key: AWS access key ID
            secret_key: AWS secret access key
            prefix: Optional prefix for all keys (folder path)
        """
        self.bucket = bucket
        self.region = region
        self.prefix = prefix.rstrip("/") + "/" if prefix else ""
        
        # Initialize S3 client
        self.client = boto3.client(
            's3',
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        
        logger.info(f"Initialized S3Storage: bucket={bucket}, region={region}, prefix={self.prefix}")
    
    def upload(self, source_file: str | Path, dest_name: str, 
               extra_args: Optional[Dict[str, Any]] = None) -> bool:
        """
        Upload a file to S3.
        
        Args:
            source_file: Source file path
            dest_name: Destination file name (relative to prefix)
            extra_args: Optional extra arguments for S3 (encryption, etc.)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            source = Path(source_file)
            if not source.exists():
                logger.error(f"Source file not found: {source}")
                return False
            
            key = self.prefix + dest_name
            
            self.client.upload_file(
                str(source),
                self.bucket,
                key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"Uploaded {source} to s3://{self.bucket}/{key}")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading to S3: {e}")
            return False
    
    def download(self, source_name: str, dest_file: str | Path) -> bool:
        """
        Download a file from S3.
        
        Args:
            source_name: Source file name (relative to prefix)
            dest_file: Destination file path
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            key = self.prefix + source_name
            dest = Path(dest_file)
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            self.client.download_file(
                self.bucket,
                key,
                str(dest)
            )
            
            logger.info(f"Downloaded s3://{self.bucket}/{key} to {dest}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading from S3: {e}")
            return False
    
    def list_files(self, pattern: Optional[str] = None) -> List[str]:
        """
        List files in S3.
        
        Args:
            pattern: Optional glob pattern to filter files
            
        Returns:
            list: List of file names (relative to prefix)
        """
        try:
            files = []
            
            # Use list_objects_v2 directly with pagination token
            continuation_token = None
            while True:
                params = {
                    'Bucket': self.bucket,
                    'Prefix': self.prefix
                }
                if continuation_token:
                    params['ContinuationToken'] = continuation_token
                
                response = self.client.list_objects_v2(**params)
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        key = obj['Key']
                        # Remove prefix from key
                        if key.startswith(self.prefix):
                            relative_key = key[len(self.prefix):]
                            
                            # Apply pattern filter
                            if pattern:
                                filename = relative_key.split('/')[-1]
                                if fnmatch.fnmatch(filename, pattern):
                                    files.append(relative_key)
                            else:
                                files.append(relative_key)
                
                # Check if there are more results
                if not response.get('IsTruncated', False):
                    break
                continuation_token = response.get('NextContinuationToken')
            
            logger.debug(f"Listed {len(files)} files from S3")
            return files
            
        except Exception as e:
            logger.error(f"Error listing S3 files: {e}")
            return []
    
    def delete(self, file_name: str) -> bool:
        """
        Delete a file from S3.
        
        Args:
            file_name: File name (relative to prefix)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            key = self.prefix + file_name
            
            self.client.delete_object(
                Bucket=self.bucket,
                Key=key
            )
            
            logger.info(f"Deleted s3://{self.bucket}/{key}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting from S3: {e}")
            return False
    
    def delete_multiple(self, file_names: List[str]) -> bool:
        """
        Delete multiple files from S3.
        
        Args:
            file_names: List of file names (relative to prefix)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            objects = [{"Key": self.prefix + name} for name in file_names]
            
            self.client.delete_objects(
                Bucket=self.bucket,
                Delete={"Objects": objects}
            )
            
            logger.info(f"Deleted {len(file_names)} files from S3")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting multiple files from S3: {e}")
            return False
    
    def exists(self, file_name: str) -> bool:
        """
        Check if a file exists in S3.
        
        Args:
            file_name: File name (relative to prefix)
            
        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            key = self.prefix + file_name
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except:
            return False
    
    def get_size(self, file_name: str) -> Optional[int]:
        """
        Get file size in bytes.
        
        Args:
            file_name: File name (relative to prefix)
            
        Returns:
            int: File size in bytes, or None if file doesn't exist
        """
        try:
            key = self.prefix + file_name
            response = self.client.head_object(Bucket=self.bucket, Key=key)
            return response['ContentLength']
            
        except Exception as e:
            logger.error(f"Error getting S3 file size: {e}")
            return None
    
    def get_modification_time(self, file_name: str) -> Optional[datetime]:
        """
        Get file modification time.
        
        Args:
            file_name: File name (relative to prefix)
            
        Returns:
            datetime: Modification time, or None if file doesn't exist
        """
        try:
            key = self.prefix + file_name
            response = self.client.head_object(Bucket=self.bucket, Key=key)
            return response['LastModified']
            
        except Exception as e:
            logger.error(f"Error getting S3 modification time: {e}")
            return None
    
    def get_total_size(self) -> int:
        """
        Get total size of all files in storage.
        
        Returns:
            int: Total size in bytes
        """
        try:
            total = 0
            continuation_token = None
            
            while True:
                params = {
                    'Bucket': self.bucket,
                    'Prefix': self.prefix
                }
                if continuation_token:
                    params['ContinuationToken'] = continuation_token
                
                response = self.client.list_objects_v2(**params)
                
                if 'Contents' in response:
                    for obj in response['Contents']:
                        total += obj['Size']
                
                if not response.get('IsTruncated', False):
                    break
                continuation_token = response.get('NextContinuationToken')
            
            logger.debug(f"Total S3 storage size: {total} bytes")
            return total
            
        except Exception as e:
            logger.error(f"Error calculating S3 total size: {e}")
            return 0
    
    def generate_presigned_url(self, file_name: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate presigned URL for temporary file access.
        
        Args:
            file_name: File name (relative to prefix)
            expiration: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            str: Presigned URL, or None on error
        """
        try:
            key = self.prefix + file_name
            
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=expiration
            )
            
            logger.info(f"Generated presigned URL for {key}")
            return url
            
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None
    
    def set_lifecycle_policy(self, policy: Dict[str, Any]) -> bool:
        """
        Set bucket lifecycle policy.
        
        Args:
            policy: Lifecycle policy configuration
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.client.put_bucket_lifecycle_configuration(
                Bucket=self.bucket,
                LifecycleConfiguration=policy
            )
            
            logger.info(f"Set lifecycle policy for bucket {self.bucket}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting lifecycle policy: {e}")
            return False
