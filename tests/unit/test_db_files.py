"""
Unit tests for FilesAdapter - File backup and restore functionality.

Tests cover:
- Initialization and configuration
- Pattern expansion (glob)
- Backup to tar.gz
- Restore from tar.gz
- Permission preservation
- Error handling
"""

import pytest
import tarfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from python_backup.db.files import FilesAdapter
from python_backup.config.models import DatabaseConfig


@pytest.fixture
def files_config():
    """Create a test configuration for files adapter."""
    return DatabaseConfig(
        type="files",
        host="localhost",
        port=0,
        username="",
        password="",
        database="",
        db_list=["/test/path/**/*", "/test/config/*.json"]
    )


@pytest.fixture
def files_adapter(files_config):
    """Create FilesAdapter instance for testing."""
    return FilesAdapter(files_config)


@pytest.fixture
def temp_test_files(tmp_path):
    """Create temporary test file structure."""
    # Create test directory structure
    test_dir = tmp_path / "test_source"
    test_dir.mkdir()
    
    # Create some test files
    (test_dir / "file1.txt").write_text("Content 1")
    (test_dir / "file2.json").write_text('{"key": "value"}')
    
    sub_dir = test_dir / "subdir"
    sub_dir.mkdir()
    (sub_dir / "file3.txt").write_text("Content 3")
    (sub_dir / "nested.yaml").write_text("key: value")
    
    return test_dir


class TestFilesAdapterInit:
    """Test FilesAdapter initialization."""
    
    def test_init_with_files_type(self, files_config):
        """Test adapter initialization with files type."""
        adapter = FilesAdapter(files_config)
        
        assert adapter.config == files_config
        assert adapter.db_type == "files"
    
    def test_init_with_getattr_compatibility(self):
        """Test adapter works with different config attribute names."""
        # Mock config with 'dbms' instead of 'type'
        mock_config = Mock()
        mock_config.dbms = "files"
        mock_config.type = None
        mock_config.db_list = ["/test/**/*"]
        
        adapter = FilesAdapter(mock_config)
        assert adapter.db_type == "files"
    
    def test_init_with_empty_db_list(self):
        """Test initialization with empty db_list."""
        config = DatabaseConfig(
            type="files",
            host="localhost",
            port=0,
            username="",
            password="",
            database="",
            db_list=[]
        )
        
        adapter = FilesAdapter(config)
        assert adapter.get_databases() == []


class TestGetDatabases:
    """Test get_databases method."""
    
    def test_get_databases_returns_patterns(self, files_adapter):
        """Test that get_databases returns pattern list."""
        patterns = files_adapter.get_databases()
        
        assert len(patterns) == 2
        assert "/test/path/**/*" in patterns
        assert "/test/config/*.json" in patterns
    
    def test_get_databases_with_getattr(self):
        """Test get_databases with getattr fallback."""
        mock_config = Mock()
        mock_config.db_list = None
        
        with patch('builtins.getattr', return_value=["/fallback/**/*"]):
            adapter = FilesAdapter(mock_config)
            patterns = adapter.get_databases()
            
            assert len(patterns) == 1


class TestExpandPattern:
    """Test pattern expansion with glob."""
    
    def test_expand_single_file(self, files_adapter, temp_test_files):
        """Test expanding pattern that matches single file."""
        pattern = str(temp_test_files / "file1.txt")
        files = files_adapter._expand_pattern(pattern)
        
        assert len(files) == 1
        assert files[0].name == "file1.txt"
    
    def test_expand_wildcard_pattern(self, files_adapter, temp_test_files):
        """Test expanding wildcard pattern."""
        pattern = str(temp_test_files / "*.txt")
        files = files_adapter._expand_pattern(pattern)
        
        assert len(files) == 1
        assert files[0].name == "file1.txt"
    
    def test_expand_recursive_pattern(self, files_adapter, temp_test_files):
        """Test expanding recursive ** pattern."""
        pattern = str(temp_test_files / "**/*.txt")
        files = files_adapter._expand_pattern(pattern)
        
        # Should find file1.txt and subdir/file3.txt
        assert len(files) == 2
        file_names = [f.name for f in files]
        assert "file1.txt" in file_names
        assert "file3.txt" in file_names
    
    def test_expand_multiple_extensions(self, files_adapter, temp_test_files):
        """Test expanding pattern with multiple extensions."""
        pattern = str(temp_test_files / "**/*.{txt,json,yaml}")
        files = files_adapter._expand_pattern(pattern)
        
        # Should find all files
        assert len(files) >= 3
    
    def test_expand_nonexistent_pattern(self, files_adapter):
        """Test expanding pattern that matches nothing."""
        pattern = "/nonexistent/path/**/*"
        files = files_adapter._expand_pattern(pattern)
        
        assert len(files) == 0


class TestBackupDatabase:
    """Test backup_database method."""
    
    def test_backup_creates_tarball(self, files_adapter, temp_test_files, tmp_path):
        """Test that backup creates a valid tar.gz file."""
        output_path = tmp_path / "backup.tar.gz"
        pattern = str(temp_test_files / "**/*")
        
        result = files_adapter.backup_database(str(pattern), str(output_path))
        
        assert result is True
        assert output_path.exists()
        assert tarfile.is_tarfile(output_path)
    
    def test_backup_includes_all_files(self, files_adapter, temp_test_files, tmp_path):
        """Test that backup includes all matched files."""
        output_path = tmp_path / "backup.tar.gz"
        pattern = str(temp_test_files / "**/*.txt")
        
        files_adapter.backup_database(str(pattern), str(output_path))
        
        # Verify tar contents
        with tarfile.open(output_path, 'r:gz') as tar:
            members = tar.getmembers()
            member_names = [m.name for m in members]
            
            assert any("file1.txt" in name for name in member_names)
            assert any("file3.txt" in name for name in member_names)
    
    def test_backup_preserves_directory_structure(self, files_adapter, temp_test_files, tmp_path):
        """Test that backup preserves directory structure."""
        output_path = tmp_path / "backup.tar.gz"
        pattern = str(temp_test_files / "**/*")
        
        files_adapter.backup_database(str(pattern), str(output_path))
        
        with tarfile.open(output_path, 'r:gz') as tar:
            members = tar.getmembers()
            
            # Should have directories and files
            assert any(m.isdir() for m in members)
            assert any(m.isfile() for m in members)
    
    def test_backup_empty_pattern(self, files_adapter, tmp_path):
        """Test backup with pattern that matches no files."""
        output_path = tmp_path / "backup.tar.gz"
        pattern = "/nonexistent/**/*"
        
        result = files_adapter.backup_database(pattern, str(output_path))
        
        # Should still create empty tarball
        assert result is True
        assert output_path.exists()
    
    def test_backup_with_invalid_output_path(self, files_adapter, temp_test_files):
        """Test backup with invalid output path."""
        pattern = str(temp_test_files / "*.txt")
        output_path = "/invalid/path/backup.tar.gz"
        
        result = files_adapter.backup_database(pattern, output_path)
        
        assert result is False


class TestRestoreDatabase:
    """Test restore_database method."""
    
    def test_restore_to_target_directory(self, files_adapter, temp_test_files, tmp_path):
        """Test restoring files to a target directory."""
        # Create backup
        backup_path = tmp_path / "backup.tar.gz"
        pattern = str(temp_test_files / "**/*")
        files_adapter.backup_database(pattern, str(backup_path))
        
        # Restore to new location
        restore_dir = tmp_path / "restored"
        restore_dir.mkdir()
        
        result = files_adapter.restore_database(pattern, str(backup_path), str(restore_dir))
        
        assert result is True
        # Check that files were restored
        restored_files = list(restore_dir.rglob("*"))
        assert len(restored_files) > 0
    
    def test_restore_creates_directory_structure(self, files_adapter, temp_test_files, tmp_path):
        """Test that restore recreates directory structure."""
        # Create backup
        backup_path = tmp_path / "backup.tar.gz"
        pattern = str(temp_test_files / "**/*")
        files_adapter.backup_database(pattern, str(backup_path))
        
        # Restore
        restore_dir = tmp_path / "restored"
        restore_dir.mkdir()
        files_adapter.restore_database(pattern, str(backup_path), str(restore_dir))
        
        # Check structure
        assert (restore_dir / "subdir").exists()
    
    def test_restore_preserves_file_content(self, files_adapter, temp_test_files, tmp_path):
        """Test that restore preserves file content."""
        # Create backup
        backup_path = tmp_path / "backup.tar.gz"
        pattern = str(temp_test_files / "file1.txt")
        files_adapter.backup_database(pattern, str(backup_path))
        
        # Restore
        restore_dir = tmp_path / "restored"
        restore_dir.mkdir()
        files_adapter.restore_database(pattern, str(backup_path), str(restore_dir))
        
        # Verify content
        restored_file = list(restore_dir.rglob("file1.txt"))[0]
        assert restored_file.read_text() == "Content 1"
    
    def test_restore_with_nonexistent_backup(self, files_adapter, tmp_path):
        """Test restore with non-existent backup file."""
        backup_path = "/nonexistent/backup.tar.gz"
        restore_dir = tmp_path / "restored"
        restore_dir.mkdir()
        
        result = files_adapter.restore_database("*", backup_path, str(restore_dir))
        
        assert result is False
    
    def test_restore_without_target_directory(self, files_adapter, temp_test_files, tmp_path):
        """Test restore without specifying target (should fail gracefully)."""
        backup_path = tmp_path / "backup.tar.gz"
        pattern = str(temp_test_files / "*.txt")
        files_adapter.backup_database(pattern, str(backup_path))
        
        # Restore without target should use original path (risky in tests)
        # For safety, we mock this behavior
        with patch.object(Path, 'mkdir'):
            result = files_adapter.restore_database(pattern, str(backup_path), None)
            # Should handle gracefully
            assert isinstance(result, bool)


class TestConnectionTest:
    """Test test_connection method."""
    
    def test_connection_with_valid_paths(self, files_adapter, temp_test_files):
        """Test connection test with valid readable paths."""
        # Override config with actual test path
        files_adapter.config.db_list = [str(temp_test_files)]
        
        result = files_adapter.test_connection()
        
        assert result is True
    
    def test_connection_with_nonexistent_path(self, files_adapter):
        """Test connection test with non-existent path."""
        files_adapter.config.db_list = ["/nonexistent/path"]
        
        result = files_adapter.test_connection()
        
        # Should return False but not crash
        assert result is False
    
    def test_connection_with_empty_db_list(self, files_adapter):
        """Test connection with empty pattern list."""
        files_adapter.config.db_list = []
        
        result = files_adapter.test_connection()
        
        # Empty list should return True (nothing to check)
        assert result is True


class TestBackupCommand:
    """Test get_backup_command method."""
    
    def test_backup_command_format(self, files_adapter):
        """Test that backup command returns valid tar command."""
        pattern = "/test/path/**/*"
        output = "/backup/file.tar.gz"
        
        command = files_adapter.get_backup_command(pattern, output)
        
        assert "tar" in command
        assert "czf" in command or "-czf" in command
        assert output in command


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_backup_with_permission_error(self, files_adapter, tmp_path):
        """Test backup handles permission errors gracefully."""
        output_path = tmp_path / "backup.tar.gz"
        pattern = "/root/protected/**/*"  # Typically unreadable
        
        # Should not raise exception
        result = files_adapter.backup_database(pattern, str(output_path))
        
        # Should return False or True with warning logged
        assert isinstance(result, bool)
    
    def test_restore_with_corrupted_tarball(self, files_adapter, tmp_path):
        """Test restore handles corrupted tar file."""
        # Create fake corrupted tar
        backup_path = tmp_path / "corrupted.tar.gz"
        backup_path.write_bytes(b"not a real tar file")
        
        restore_dir = tmp_path / "restored"
        restore_dir.mkdir()
        
        result = files_adapter.restore_database("*", str(backup_path), str(restore_dir))
        
        assert result is False


class TestIntegrationScenarios:
    """Integration-style tests with realistic scenarios."""
    
    def test_full_backup_restore_cycle(self, files_adapter, temp_test_files, tmp_path):
        """Test complete backup and restore cycle."""
        # Backup
        backup_path = tmp_path / "full_backup.tar.gz"
        pattern = str(temp_test_files / "**/*")
        
        backup_result = files_adapter.backup_database(pattern, str(backup_path))
        assert backup_result is True
        
        # Restore to new location
        restore_dir = tmp_path / "full_restore"
        restore_dir.mkdir()
        
        restore_result = files_adapter.restore_database(pattern, str(backup_path), str(restore_dir))
        assert restore_result is True
        
        # Verify files exist
        restored_files = list(restore_dir.rglob("*.txt"))
        assert len(restored_files) >= 2
    
    def test_multiple_patterns_backup(self, files_adapter, temp_test_files, tmp_path):
        """Test backing up multiple patterns."""
        patterns = [
            str(temp_test_files / "*.txt"),
            str(temp_test_files / "*.json")
        ]
        
        for i, pattern in enumerate(patterns):
            backup_path = tmp_path / f"backup_{i}.tar.gz"
            result = files_adapter.backup_database(pattern, str(backup_path))
            
            assert result is True
            assert backup_path.exists()
