"""
Unit tests for local storage operations.

Tests file system operations for backup storage, including upload, download,
listing, and deletion of backup files.
"""

import pytest
import os
from pathlib import Path
from datetime import datetime

from python_backup.storage.local import LocalStorage


@pytest.fixture
def storage_dir(tmp_path):
    """Create temporary storage directory."""
    storage = tmp_path / "backups"
    storage.mkdir()
    return storage


@pytest.fixture
def local_storage(storage_dir):
    """Create LocalStorage instance."""
    return LocalStorage(storage_dir)


@pytest.fixture
def sample_backup_file(tmp_path):
    """Create a sample backup file."""
    backup_file = tmp_path / "test_backup.sql"
    backup_file.write_text("SELECT * FROM users;")
    return backup_file


class TestLocalStorageInitialization:
    """Test LocalStorage initialization."""

    def test_storage_creation(self, storage_dir):
        """Test creating storage with valid directory."""
        storage = LocalStorage(storage_dir)
        
        assert storage.base_path == storage_dir
        assert storage.base_path.exists()

    def test_storage_creates_directory(self, tmp_path):
        """Test that storage creates directory if not exists."""
        new_dir = tmp_path / "new_storage"
        
        storage = LocalStorage(new_dir)
        
        assert new_dir.exists()
        assert storage.base_path == new_dir

    def test_storage_with_string_path(self, tmp_path):
        """Test creating storage with string path."""
        path_str = str(tmp_path / "string_storage")
        
        storage = LocalStorage(path_str)
        
        assert isinstance(storage.base_path, Path)
        assert storage.base_path.exists()

    def test_storage_nested_directory(self, tmp_path):
        """Test creating nested directory structure."""
        nested_path = tmp_path / "level1" / "level2" / "backups"
        
        storage = LocalStorage(nested_path)
        
        assert nested_path.exists()


class TestLocalStorageUpload:
    """Test uploading files to local storage."""

    def test_upload_file_success(self, local_storage, sample_backup_file):
        """Test successful file upload."""
        dest_name = "uploaded_backup.sql"
        
        result = local_storage.upload(sample_backup_file, dest_name)
        
        assert result is True
        uploaded_file = local_storage.base_path / dest_name
        assert uploaded_file.exists()
        assert uploaded_file.read_text() == sample_backup_file.read_text()

    def test_upload_preserves_content(self, local_storage, tmp_path):
        """Test that upload preserves file content."""
        content = "Important backup data\nWith multiple lines\n"
        source_file = tmp_path / "source.sql"
        source_file.write_text(content)
        
        local_storage.upload(source_file, "destination.sql")
        
        uploaded = local_storage.base_path / "destination.sql"
        assert uploaded.read_text() == content

    def test_upload_creates_subdirectories(self, local_storage, sample_backup_file):
        """Test that upload creates subdirectories if needed."""
        dest_path = "mysql/daily/backup.sql"
        
        result = local_storage.upload(sample_backup_file, dest_path)
        
        assert result is True
        uploaded_file = local_storage.base_path / dest_path
        assert uploaded_file.exists()

    def test_upload_overwrites_existing(self, local_storage, tmp_path):
        """Test that upload overwrites existing files."""
        dest_name = "backup.sql"
        
        # Create existing file
        existing = local_storage.base_path / dest_name
        existing.write_text("old content")
        
        # Upload new file
        new_file = tmp_path / "new.sql"
        new_file.write_text("new content")
        local_storage.upload(new_file, dest_name)
        
        # Verify overwrite
        assert existing.read_text() == "new content"

    def test_upload_nonexistent_source(self, local_storage, tmp_path):
        """Test uploading non-existent source file."""
        nonexistent = tmp_path / "does_not_exist.sql"
        
        result = local_storage.upload(nonexistent, "backup.sql")
        
        assert result is False


class TestLocalStorageDownload:
    """Test downloading files from local storage."""

    def test_download_file_success(self, local_storage, tmp_path):
        """Test successful file download."""
        # Upload a file first
        content = "Backup content"
        source_name = "backup.sql"
        source = local_storage.base_path / source_name
        source.write_text(content)
        
        # Download to new location
        dest_file = tmp_path / "downloaded.sql"
        result = local_storage.download(source_name, dest_file)
        
        assert result is True
        assert dest_file.exists()
        assert dest_file.read_text() == content

    def test_download_preserves_content(self, local_storage, tmp_path):
        """Test that download preserves content."""
        content = "Multi-line\nbackup\ndata\n"
        source_name = "multi.sql"
        (local_storage.base_path / source_name).write_text(content)
        
        dest = tmp_path / "dest.sql"
        local_storage.download(source_name, dest)
        
        assert dest.read_text() == content

    def test_download_nonexistent_file(self, local_storage, tmp_path):
        """Test downloading non-existent file."""
        dest = tmp_path / "dest.sql"
        
        result = local_storage.download("nonexistent.sql", dest)
        
        assert result is False
        assert not dest.exists()

    def test_download_creates_destination_dir(self, local_storage, tmp_path):
        """Test that download creates destination directory."""
        # Upload a file
        source_name = "backup.sql"
        (local_storage.base_path / source_name).write_text("content")
        
        # Download to nested path
        dest = tmp_path / "level1" / "level2" / "backup.sql"
        result = local_storage.download(source_name, dest)
        
        assert result is True
        assert dest.exists()


class TestLocalStorageList:
    """Test listing files in storage."""

    def test_list_empty_storage(self, local_storage):
        """Test listing empty storage."""
        files = local_storage.list_files()
        
        assert files == []

    def test_list_files_in_root(self, local_storage):
        """Test listing files in root directory."""
        # Create files
        (local_storage.base_path / "backup1.sql").write_text("data1")
        (local_storage.base_path / "backup2.sql").write_text("data2")
        (local_storage.base_path / "backup3.sql").write_text("data3")
        
        files = local_storage.list_files()
        
        assert len(files) == 3
        assert "backup1.sql" in files
        assert "backup2.sql" in files
        assert "backup3.sql" in files

    def test_list_files_with_subdirectories(self, local_storage):
        """Test listing files in subdirectories."""
        # Create structure
        (local_storage.base_path / "mysql").mkdir()
        (local_storage.base_path / "mysql" / "backup1.sql").write_text("data")
        (local_storage.base_path / "postgres").mkdir()
        (local_storage.base_path / "postgres" / "backup2.sql").write_text("data")
        
        files = local_storage.list_files()
        
        assert len(files) == 2
        assert "mysql/backup1.sql" in files
        assert "postgres/backup2.sql" in files

    def test_list_files_recursive(self, local_storage):
        """Test recursive file listing."""
        # Create nested structure
        (local_storage.base_path / "a" / "b" / "c").mkdir(parents=True)
        (local_storage.base_path / "a" / "file1.sql").write_text("data")
        (local_storage.base_path / "a" / "b" / "file2.sql").write_text("data")
        (local_storage.base_path / "a" / "b" / "c" / "file3.sql").write_text("data")
        
        files = local_storage.list_files()
        
        assert len(files) == 3

    def test_list_files_with_pattern(self, local_storage):
        """Test listing files with pattern filter."""
        # Create various files
        (local_storage.base_path / "backup1.sql").write_text("data")
        (local_storage.base_path / "backup2.sql.gz").write_text("data")
        (local_storage.base_path / "data.txt").write_text("data")
        
        files = local_storage.list_files(pattern="*.sql")
        
        assert len(files) == 1
        assert "backup1.sql" in files

    def test_list_files_sorted_by_time(self, local_storage):
        """Test listing files sorted by modification time."""
        import time
        
        # Create files with different times
        file1 = local_storage.base_path / "old.sql"
        file1.write_text("data")
        time.sleep(0.01)
        
        file2 = local_storage.base_path / "new.sql"
        file2.write_text("data")
        
        files = local_storage.list_files(sort_by="time", reverse=True)
        
        # Most recent first
        assert files[0] == "new.sql"
        assert files[1] == "old.sql"


class TestLocalStorageDelete:
    """Test deleting files from storage."""

    def test_delete_file_success(self, local_storage):
        """Test successful file deletion."""
        filename = "backup.sql"
        file_path = local_storage.base_path / filename
        file_path.write_text("data")
        
        result = local_storage.delete(filename)
        
        assert result is True
        assert not file_path.exists()

    def test_delete_nonexistent_file(self, local_storage):
        """Test deleting non-existent file."""
        result = local_storage.delete("nonexistent.sql")
        
        assert result is False

    def test_delete_file_in_subdirectory(self, local_storage):
        """Test deleting file in subdirectory."""
        subdir = local_storage.base_path / "mysql"
        subdir.mkdir()
        file_path = subdir / "backup.sql"
        file_path.write_text("data")
        
        result = local_storage.delete("mysql/backup.sql")
        
        assert result is True
        assert not file_path.exists()
        assert subdir.exists()  # Directory should remain


class TestLocalStorageMetadata:
    """Test getting file metadata."""

    def test_get_file_size(self, local_storage):
        """Test getting file size."""
        filename = "backup.sql"
        content = "x" * 1000  # 1000 bytes
        (local_storage.base_path / filename).write_text(content)
        
        size = local_storage.get_size(filename)
        
        assert size == 1000

    def test_get_size_nonexistent_file(self, local_storage):
        """Test getting size of non-existent file."""
        size = local_storage.get_size("nonexistent.sql")
        
        assert size is None

    def test_file_exists_check(self, local_storage):
        """Test checking if file exists."""
        filename = "backup.sql"
        (local_storage.base_path / filename).write_text("data")
        
        assert local_storage.exists(filename) is True
        assert local_storage.exists("nonexistent.sql") is False

    def test_get_modification_time(self, local_storage):
        """Test getting file modification time."""
        filename = "backup.sql"
        file_path = local_storage.base_path / filename
        file_path.write_text("data")
        
        mtime = local_storage.get_modification_time(filename)
        
        assert mtime is not None
        assert isinstance(mtime, datetime)


class TestLocalStorageUtils:
    """Test utility methods."""

    def test_get_total_size(self, local_storage):
        """Test getting total storage size."""
        # Create files with known sizes
        (local_storage.base_path / "file1.sql").write_text("x" * 100)
        (local_storage.base_path / "file2.sql").write_text("x" * 200)
        (local_storage.base_path / "file3.sql").write_text("x" * 300)
        
        total = local_storage.get_total_size()
        
        assert total == 600

    def test_get_total_size_empty(self, local_storage):
        """Test total size of empty storage."""
        total = local_storage.get_total_size()
        
        assert total == 0

    def test_clean_empty_directories(self, local_storage):
        """Test cleaning empty directories."""
        # Create empty directories
        (local_storage.base_path / "empty1").mkdir()
        (local_storage.base_path / "empty2" / "nested").mkdir(parents=True)
        
        # Create directory with file
        (local_storage.base_path / "with_file").mkdir()
        (local_storage.base_path / "with_file" / "backup.sql").write_text("data")
        
        local_storage.clean_empty_directories()
        
        # Empty directories should be removed
        assert not (local_storage.base_path / "empty1").exists()
        assert not (local_storage.base_path / "empty2").exists()
        
        # Directory with file should remain
        assert (local_storage.base_path / "with_file").exists()
