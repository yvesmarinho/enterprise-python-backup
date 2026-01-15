"""
Unit tests for S3 storage operations.

Tests AWS S3 operations for backup storage using moto for mocking.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path

from python_backup.storage.s3 import S3Storage


@pytest.fixture
def s3_config():
    """S3 configuration."""
    return {
        "bucket": "test-backup-bucket",
        "region": "us-east-1",
        "access_key": "test_access_key",
        "secret_key": "test_secret_key",
        "prefix": "backups/"
    }


@pytest.fixture
def mock_s3_client():
    """Mock boto3 S3 client."""
    with patch('boto3.client') as mock_boto:
        client = MagicMock()
        mock_boto.return_value = client
        yield client


@pytest.fixture
def s3_storage(s3_config, mock_s3_client):
    """Create S3Storage instance with mocked client."""
    return S3Storage(**s3_config)


@pytest.fixture
def sample_file(tmp_path):
    """Create sample backup file."""
    file = tmp_path / "backup.sql"
    file.write_text("SELECT * FROM users;")
    return file


class TestS3StorageInitialization:
    """Test S3Storage initialization."""

    def test_storage_creation(self, s3_config, mock_s3_client):
        """Test creating S3 storage."""
        storage = S3Storage(**s3_config)
        
        assert storage.bucket == "test-backup-bucket"
        assert storage.region == "us-east-1"
        assert storage.prefix == "backups/"

    def test_storage_without_prefix(self, mock_s3_client):
        """Test creating storage without prefix."""
        storage = S3Storage(
            bucket="test-bucket",
            region="us-west-2",
            access_key="key",
            secret_key="secret"
        )
        
        assert storage.prefix == ""

    def test_storage_normalizes_prefix(self, mock_s3_client):
        """Test that prefix is normalized with trailing slash."""
        storage = S3Storage(
            bucket="test-bucket",
            region="us-west-2",
            access_key="key",
            secret_key="secret",
            prefix="my-backups"
        )
        
        assert storage.prefix == "my-backups/"


class TestS3StorageUpload:
    """Test uploading files to S3."""

    def test_upload_file_success(self, s3_storage, sample_file, mock_s3_client):
        """Test successful file upload."""
        dest_name = "backup.sql"
        
        result = s3_storage.upload(sample_file, dest_name)
        
        assert result is True
        mock_s3_client.upload_file.assert_called_once()
        
        # Check upload parameters
        call_args = mock_s3_client.upload_file.call_args
        assert call_args[0][0] == str(sample_file)
        assert call_args[0][1] == "test-backup-bucket"
        assert call_args[0][2] == "backups/backup.sql"

    def test_upload_with_nested_path(self, s3_storage, sample_file, mock_s3_client):
        """Test upload with nested destination path."""
        dest_name = "mysql/daily/backup.sql"
        
        s3_storage.upload(sample_file, dest_name)
        
        call_args = mock_s3_client.upload_file.call_args
        assert call_args[0][2] == "backups/mysql/daily/backup.sql"

    def test_upload_nonexistent_file(self, s3_storage, tmp_path, mock_s3_client):
        """Test uploading non-existent file."""
        nonexistent = tmp_path / "missing.sql"
        
        result = s3_storage.upload(nonexistent, "backup.sql")
        
        assert result is False
        mock_s3_client.upload_file.assert_not_called()

    def test_upload_handles_s3_error(self, s3_storage, sample_file, mock_s3_client):
        """Test handling S3 upload errors."""
        mock_s3_client.upload_file.side_effect = Exception("S3 Error")
        
        result = s3_storage.upload(sample_file, "backup.sql")
        
        assert result is False

    def test_upload_with_extra_args(self, s3_storage, sample_file, mock_s3_client):
        """Test upload with extra arguments (encryption, etc)."""
        s3_storage.upload(
            sample_file, 
            "backup.sql",
            extra_args={"ServerSideEncryption": "AES256"}
        )
        
        call_args = mock_s3_client.upload_file.call_args
        assert "ExtraArgs" in call_args[1]
        assert call_args[1]["ExtraArgs"]["ServerSideEncryption"] == "AES256"


class TestS3StorageDownload:
    """Test downloading files from S3."""

    def test_download_file_success(self, s3_storage, tmp_path, mock_s3_client):
        """Test successful file download."""
        source_name = "backup.sql"
        dest_file = tmp_path / "downloaded.sql"
        
        result = s3_storage.download(source_name, dest_file)
        
        assert result is True
        mock_s3_client.download_file.assert_called_once()
        
        # Check download parameters
        call_args = mock_s3_client.download_file.call_args
        assert call_args[0][0] == "test-backup-bucket"
        assert call_args[0][1] == "backups/backup.sql"
        assert call_args[0][2] == str(dest_file)

    def test_download_creates_destination_dir(self, s3_storage, tmp_path, mock_s3_client):
        """Test that download creates destination directory."""
        dest = tmp_path / "level1" / "level2" / "backup.sql"
        
        s3_storage.download("backup.sql", dest)
        
        assert dest.parent.exists()

    def test_download_handles_s3_error(self, s3_storage, tmp_path, mock_s3_client):
        """Test handling S3 download errors."""
        mock_s3_client.download_file.side_effect = Exception("S3 Error")
        dest = tmp_path / "backup.sql"
        
        result = s3_storage.download("backup.sql", dest)
        
        assert result is False


class TestS3StorageList:
    """Test listing files in S3."""

    def test_list_empty_bucket(self, s3_storage, mock_s3_client):
        """Test listing empty bucket."""
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": []
        }
        
        files = s3_storage.list_files()
        
        assert files == []

    def test_list_files_success(self, s3_storage, mock_s3_client):
        """Test listing files in bucket."""
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "backups/backup1.sql", "Size": 1000, "LastModified": datetime.now()},
                {"Key": "backups/backup2.sql", "Size": 2000, "LastModified": datetime.now()},
                {"Key": "backups/backup3.sql", "Size": 3000, "LastModified": datetime.now()},
            ]
        }
        
        files = s3_storage.list_files()
        
        assert len(files) == 3
        assert "backup1.sql" in files
        assert "backup2.sql" in files
        assert "backup3.sql" in files

    def test_list_files_with_prefix(self, s3_storage, mock_s3_client):
        """Test listing files with prefix."""
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "backups/mysql/backup1.sql", "Size": 1000, "LastModified": datetime.now()},
                {"Key": "backups/postgres/backup2.sql", "Size": 2000, "LastModified": datetime.now()},
            ]
        }
        
        files = s3_storage.list_files()
        
        assert len(files) == 2
        assert "mysql/backup1.sql" in files
        assert "postgres/backup2.sql" in files

    def test_list_files_pagination(self, s3_storage, mock_s3_client):
        """Test listing files with pagination."""
        # First page
        mock_s3_client.list_objects_v2.side_effect = [
            {
                "Contents": [
                    {"Key": "backups/backup1.sql", "Size": 1000, "LastModified": datetime.now()},
                ],
                "IsTruncated": True,
                "NextContinuationToken": "token123"
            },
            # Second page
            {
                "Contents": [
                    {"Key": "backups/backup2.sql", "Size": 2000, "LastModified": datetime.now()},
                ],
                "IsTruncated": False
            }
        ]
        
        files = s3_storage.list_files()
        
        assert len(files) == 2
        assert mock_s3_client.list_objects_v2.call_count == 2

    def test_list_files_with_pattern(self, s3_storage, mock_s3_client):
        """Test listing files with pattern filter."""
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "backups/backup1.sql", "Size": 1000, "LastModified": datetime.now()},
                {"Key": "backups/backup2.sql.gz", "Size": 500, "LastModified": datetime.now()},
                {"Key": "backups/data.txt", "Size": 100, "LastModified": datetime.now()},
            ]
        }
        
        files = s3_storage.list_files(pattern="*.sql")
        
        assert len(files) == 1
        assert "backup1.sql" in files


class TestS3StorageDelete:
    """Test deleting files from S3."""

    def test_delete_file_success(self, s3_storage, mock_s3_client):
        """Test successful file deletion."""
        filename = "backup.sql"
        
        result = s3_storage.delete(filename)
        
        assert result is True
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket="test-backup-bucket",
            Key="backups/backup.sql"
        )

    def test_delete_handles_s3_error(self, s3_storage, mock_s3_client):
        """Test handling S3 deletion errors."""
        mock_s3_client.delete_object.side_effect = Exception("S3 Error")
        
        result = s3_storage.delete("backup.sql")
        
        assert result is False

    def test_delete_multiple_files(self, s3_storage, mock_s3_client):
        """Test deleting multiple files at once."""
        files = ["backup1.sql", "backup2.sql", "backup3.sql"]
        
        result = s3_storage.delete_multiple(files)
        
        assert result is True
        mock_s3_client.delete_objects.assert_called_once()
        
        call_args = mock_s3_client.delete_objects.call_args
        delete_list = call_args[1]["Delete"]["Objects"]
        assert len(delete_list) == 3


class TestS3StorageMetadata:
    """Test getting file metadata from S3."""

    def test_get_file_size(self, s3_storage, mock_s3_client):
        """Test getting file size."""
        mock_s3_client.head_object.return_value = {
            "ContentLength": 1024
        }
        
        size = s3_storage.get_size("backup.sql")
        
        assert size == 1024

    def test_get_size_nonexistent_file(self, s3_storage, mock_s3_client):
        """Test getting size of non-existent file."""
        mock_s3_client.head_object.side_effect = Exception("Not Found")
        
        size = s3_storage.get_size("nonexistent.sql")
        
        assert size is None

    def test_file_exists_check(self, s3_storage, mock_s3_client):
        """Test checking if file exists."""
        # File exists
        mock_s3_client.head_object.return_value = {"ContentLength": 1000}
        assert s3_storage.exists("backup.sql") is True
        
        # File doesn't exist
        mock_s3_client.head_object.side_effect = Exception("Not Found")
        assert s3_storage.exists("nonexistent.sql") is False

    def test_get_modification_time(self, s3_storage, mock_s3_client):
        """Test getting file modification time."""
        test_time = datetime(2026, 1, 12, 10, 30, 0)
        mock_s3_client.head_object.return_value = {
            "LastModified": test_time
        }
        
        mtime = s3_storage.get_modification_time("backup.sql")
        
        assert mtime == test_time


class TestS3StorageUtils:
    """Test S3 utility methods."""

    def test_get_total_size(self, s3_storage, mock_s3_client):
        """Test getting total storage size."""
        mock_s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "backups/file1.sql", "Size": 100, "LastModified": datetime.now()},
                {"Key": "backups/file2.sql", "Size": 200, "LastModified": datetime.now()},
                {"Key": "backups/file3.sql", "Size": 300, "LastModified": datetime.now()},
            ]
        }
        
        total = s3_storage.get_total_size()
        
        assert total == 600

    def test_generate_presigned_url(self, s3_storage, mock_s3_client):
        """Test generating presigned URL."""
        mock_s3_client.generate_presigned_url.return_value = "https://s3.amazonaws.com/..."
        
        url = s3_storage.generate_presigned_url("backup.sql", expiration=3600)
        
        assert url is not None
        assert url.startswith("https://")
        mock_s3_client.generate_presigned_url.assert_called_once()

    def test_set_bucket_lifecycle(self, s3_storage, mock_s3_client):
        """Test setting bucket lifecycle policy."""
        policy = {
            "Rules": [
                {
                    "Id": "DeleteOldBackups",
                    "Status": "Enabled",
                    "Expiration": {"Days": 30}
                }
            ]
        }
        
        result = s3_storage.set_lifecycle_policy(policy)
        
        assert result is True
        mock_s3_client.put_bucket_lifecycle_configuration.assert_called_once()
