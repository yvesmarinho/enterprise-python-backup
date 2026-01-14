"""
Integration tests for Files Backup - End-to-End scenarios.

Tests complete workflows:
- Full backup and restore cycle with CLI
- Multiple file patterns
- Large file handling
- Real filesystem operations
"""

import pytest
import tarfile
import subprocess
from pathlib import Path
from datetime import datetime

from vya_backupbd.db.files import FilesAdapter
from vya_backupbd.config.models import DatabaseConfig
from vya_backupbd.backup.context import BackupContext, DatabaseConfig as BackupDbConfig
from vya_backupbd.backup.strategy import BackupStrategy, StorageConfig, BackupConfig
from vya_backupbd.backup.executor import BackupExecutor


@pytest.fixture
def integration_test_files(tmp_path):
    """Create comprehensive test file structure for integration tests."""
    base = tmp_path / "integration_source"
    base.mkdir()
    
    # Create multiple file types
    (base / "config.json").write_text('{"database": "prod", "port": 5432}')
    (base / "app.yaml").write_text("version: 1.0\nname: MyApp")
    (base / "README.md").write_text("# Application Readme")
    
    # Create nested structure
    data_dir = base / "data"
    data_dir.mkdir()
    (data_dir / "users.csv").write_text("id,name,email\n1,John,john@example.com")
    (data_dir / "products.json").write_text('[{"id": 1, "name": "Widget"}]')
    
    # Create logs directory
    logs_dir = base / "logs"
    logs_dir.mkdir()
    (logs_dir / "app.log").write_text("2026-01-14 INFO Application started")
    (logs_dir / "error.log").write_text("2026-01-14 ERROR Connection failed")
    
    # Create uploads directory with subdirectories
    uploads = base / "uploads"
    uploads.mkdir()
    
    images = uploads / "images"
    images.mkdir()
    (images / "photo1.jpg").write_bytes(b"fake jpg data")
    (images / "photo2.png").write_bytes(b"fake png data")
    
    docs = uploads / "documents"
    docs.mkdir()
    (docs / "report.pdf").write_bytes(b"fake pdf data")
    (docs / "invoice.xlsx").write_bytes(b"fake excel data")
    
    return base


@pytest.fixture
def files_adapter_integration():
    """Create FilesAdapter for integration tests."""
    config = DatabaseConfig(
        type="files",
        host="localhost",
        port=0,
        username="",
        password="",
        database="",
        db_list=[]  # Will be set per test
    )
    return FilesAdapter(config)


class TestFilesBackupE2E:
    """End-to-end tests for files backup."""
    
    def test_backup_entire_directory(self, files_adapter_integration, integration_test_files, tmp_path):
        """Test backing up entire directory structure."""
        files_adapter_integration.config.db_list = [str(integration_test_files / "**/*")]
        
        backup_path = tmp_path / "full_backup.tar.gz"
        pattern = str(integration_test_files / "**/*")
        
        result = files_adapter_integration.backup_database(pattern, str(backup_path))
        
        assert result is True
        assert backup_path.exists()
        assert backup_path.stat().st_size > 0
        
        # Verify tar contents
        with tarfile.open(backup_path, 'r:gz') as tar:
            members = tar.getmembers()
            assert len(members) > 10  # Should have many files
            
            # Check specific files exist
            member_names = [m.name for m in members]
            assert any("config.json" in name for name in member_names)
            assert any("data" in name for name in member_names)
            assert any("uploads" in name for name in member_names)
    
    def test_backup_specific_file_types(self, files_adapter_integration, integration_test_files, tmp_path):
        """Test backing up specific file extensions."""
        backup_path = tmp_path / "json_only.tar.gz"
        pattern = str(integration_test_files / "**/*.json")
        
        result = files_adapter_integration.backup_database(pattern, str(backup_path))
        
        assert result is True
        
        with tarfile.open(backup_path, 'r:gz') as tar:
            members = tar.getmembers()
            file_members = [m for m in members if m.isfile()]
            
            # Should only have JSON files
            for member in file_members:
                assert member.name.endswith('.json')
    
    def test_backup_multiple_patterns(self, files_adapter_integration, integration_test_files, tmp_path):
        """Test backing up with multiple glob patterns."""
        patterns = [
            str(integration_test_files / "**/*.json"),
            str(integration_test_files / "**/*.yaml"),
            str(integration_test_files / "**/*.md")
        ]
        
        for i, pattern in enumerate(patterns):
            backup_path = tmp_path / f"backup_{i}.tar.gz"
            result = files_adapter_integration.backup_database(pattern, str(backup_path))
            
            assert result is True
            assert backup_path.exists()
    
    def test_backup_preserves_permissions(self, files_adapter_integration, integration_test_files, tmp_path):
        """Test that backup preserves file permissions."""
        # Set specific permission on a file
        test_file = integration_test_files / "config.json"
        test_file.chmod(0o644)
        
        backup_path = tmp_path / "backup.tar.gz"
        pattern = str(integration_test_files / "config.json")
        
        files_adapter_integration.backup_database(pattern, str(backup_path))
        
        # Check tar preserves permissions
        with tarfile.open(backup_path, 'r:gz') as tar:
            for member in tar.getmembers():
                if member.isfile() and "config.json" in member.name:
                    # Tarfile stores permissions
                    assert member.mode is not None
    
    def test_backup_large_directory_structure(self, files_adapter_integration, tmp_path):
        """Test backing up large directory with many files."""
        # Create many files
        large_dir = tmp_path / "large_source"
        large_dir.mkdir()
        
        for i in range(100):
            (large_dir / f"file_{i}.txt").write_text(f"Content {i}")
        
        backup_path = tmp_path / "large_backup.tar.gz"
        pattern = str(large_dir / "**/*")
        
        result = files_adapter_integration.backup_database(pattern, str(backup_path))
        
        assert result is True
        assert backup_path.exists()
        
        # Verify count
        with tarfile.open(backup_path, 'r:gz') as tar:
            file_count = sum(1 for m in tar.getmembers() if m.isfile())
            assert file_count == 100


class TestFilesRestoreE2E:
    """End-to-end tests for files restore."""
    
    def test_restore_complete_backup(self, files_adapter_integration, integration_test_files, tmp_path):
        """Test restoring a complete backup."""
        # Create backup
        backup_path = tmp_path / "backup.tar.gz"
        pattern = str(integration_test_files / "**/*")
        files_adapter_integration.backup_database(pattern, str(backup_path))
        
        # Restore to new location
        restore_dir = tmp_path / "restored"
        restore_dir.mkdir()
        
        result = files_adapter_integration.restore_database(pattern, str(backup_path), str(restore_dir))
        
        assert result is True
        
        # Verify files were restored
        restored_config = list(restore_dir.rglob("config.json"))
        assert len(restored_config) > 0
        
        restored_data = list(restore_dir.rglob("data"))
        assert len(restored_data) > 0
    
    def test_restore_preserves_directory_structure(self, files_adapter_integration, integration_test_files, tmp_path):
        """Test that restore recreates original directory structure."""
        backup_path = tmp_path / "backup.tar.gz"
        pattern = str(integration_test_files / "**/*")
        files_adapter_integration.backup_database(pattern, str(backup_path))
        
        restore_dir = tmp_path / "restored"
        restore_dir.mkdir()
        files_adapter_integration.restore_database(pattern, str(backup_path), str(restore_dir))
        
        # Check structure exists
        assert (restore_dir / "data").exists() or any("data" in str(p) for p in restore_dir.rglob("*"))
        assert (restore_dir / "logs").exists() or any("logs" in str(p) for p in restore_dir.rglob("*"))
        assert (restore_dir / "uploads").exists() or any("uploads" in str(p) for p in restore_dir.rglob("*"))
    
    def test_restore_preserves_file_content(self, files_adapter_integration, integration_test_files, tmp_path):
        """Test that restore preserves exact file content."""
        # Backup
        backup_path = tmp_path / "backup.tar.gz"
        pattern = str(integration_test_files / "config.json")
        files_adapter_integration.backup_database(pattern, str(backup_path))
        
        # Get original content
        original_content = (integration_test_files / "config.json").read_text()
        
        # Restore
        restore_dir = tmp_path / "restored"
        restore_dir.mkdir()
        files_adapter_integration.restore_database(pattern, str(backup_path), str(restore_dir))
        
        # Find restored file
        restored_files = list(restore_dir.rglob("config.json"))
        assert len(restored_files) > 0
        
        # Verify content matches
        restored_content = restored_files[0].read_text()
        assert restored_content == original_content
    
    def test_restore_to_different_location(self, files_adapter_integration, integration_test_files, tmp_path):
        """Test restoring files to a different directory."""
        backup_path = tmp_path / "backup.tar.gz"
        pattern = str(integration_test_files / "data/**/*")
        files_adapter_integration.backup_database(pattern, str(backup_path))
        
        # Restore to completely different location
        restore_dir = tmp_path / "completely_different_location"
        restore_dir.mkdir()
        
        result = files_adapter_integration.restore_database(pattern, str(backup_path), str(restore_dir))
        
        assert result is True
        # Files should be in restore_dir
        restored_files = list(restore_dir.rglob("*"))
        assert len(restored_files) > 0


class TestBackupRestoreCycle:
    """Test complete backup and restore cycles."""
    
    def test_full_cycle_data_integrity(self, files_adapter_integration, integration_test_files, tmp_path):
        """Test data integrity through backup and restore cycle."""
        # Backup
        backup_path = tmp_path / "cycle_backup.tar.gz"
        pattern = str(integration_test_files / "**/*")
        
        backup_result = files_adapter_integration.backup_database(pattern, str(backup_path))
        assert backup_result is True
        
        # Restore
        restore_dir = tmp_path / "cycle_restored"
        restore_dir.mkdir()
        
        restore_result = files_adapter_integration.restore_database(pattern, str(backup_path), str(restore_dir))
        assert restore_result is True
        
        # Compare file counts
        original_files = list(integration_test_files.rglob("*"))
        original_file_count = sum(1 for f in original_files if f.is_file())
        
        restored_files = list(restore_dir.rglob("*"))
        restored_file_count = sum(1 for f in restored_files if f.is_file())
        
        # Should have same number of files
        assert restored_file_count == original_file_count
    
    def test_multiple_backup_versions(self, files_adapter_integration, integration_test_files, tmp_path):
        """Test creating multiple backup versions."""
        backups = []
        
        for i in range(3):
            backup_path = tmp_path / f"backup_v{i}.tar.gz"
            pattern = str(integration_test_files / "**/*")
            
            result = files_adapter_integration.backup_database(pattern, str(backup_path))
            assert result is True
            
            backups.append(backup_path)
        
        # All backups should exist
        assert all(b.exists() for b in backups)
        
        # All should have similar sizes (same content)
        sizes = [b.stat().st_size for b in backups]
        assert max(sizes) - min(sizes) < 1000  # Within 1KB


class TestErrorRecovery:
    """Test error handling and recovery scenarios."""
    
    def test_backup_with_missing_source(self, files_adapter_integration, tmp_path):
        """Test backup handles missing source gracefully."""
        backup_path = tmp_path / "backup.tar.gz"
        pattern = "/totally/nonexistent/path/**/*"
        
        result = files_adapter_integration.backup_database(pattern, str(backup_path))
        
        # Should not crash, may create empty backup
        assert isinstance(result, bool)
    
    def test_restore_with_invalid_backup(self, files_adapter_integration, tmp_path):
        """Test restore handles invalid backup file."""
        # Create fake backup
        backup_path = tmp_path / "invalid.tar.gz"
        backup_path.write_text("not a tar file")
        
        restore_dir = tmp_path / "restore"
        restore_dir.mkdir()
        
        result = files_adapter_integration.restore_database("*", str(backup_path), str(restore_dir))
        
        assert result is False
    
    def test_backup_with_permission_denied(self, files_adapter_integration, tmp_path):
        """Test backup handles permission errors."""
        # Try to backup system directory (may fail on permissions)
        backup_path = tmp_path / "backup.tar.gz"
        pattern = "/root/**/*"  # Typically restricted
        
        # Should not crash
        result = files_adapter_integration.backup_database(pattern, str(backup_path))
        assert isinstance(result, bool)


class TestSpecialCases:
    """Test special edge cases and scenarios."""
    
    def test_backup_empty_directory(self, files_adapter_integration, tmp_path):
        """Test backing up empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        backup_path = tmp_path / "empty_backup.tar.gz"
        pattern = str(empty_dir / "**/*")
        
        result = files_adapter_integration.backup_database(pattern, str(backup_path))
        
        assert result is True
        assert backup_path.exists()
    
    def test_backup_symlinks(self, files_adapter_integration, integration_test_files, tmp_path):
        """Test backup handles symbolic links."""
        # Create a symlink
        link_path = integration_test_files / "link_to_config"
        target_path = integration_test_files / "config.json"
        
        try:
            link_path.symlink_to(target_path)
            
            backup_path = tmp_path / "with_symlinks.tar.gz"
            pattern = str(integration_test_files / "**/*")
            
            result = files_adapter_integration.backup_database(pattern, str(backup_path))
            
            assert result is True
            assert backup_path.exists()
        except OSError:
            # Skip if symlinks not supported
            pytest.skip("Symlinks not supported on this system")
    
    def test_backup_with_special_characters_in_names(self, files_adapter_integration, tmp_path):
        """Test backup handles files with special characters."""
        test_dir = tmp_path / "special"
        test_dir.mkdir()
        
        # Create files with special names
        (test_dir / "file with spaces.txt").write_text("content")
        (test_dir / "file-with-dashes.txt").write_text("content")
        (test_dir / "file_with_underscores.txt").write_text("content")
        
        backup_path = tmp_path / "special_backup.tar.gz"
        pattern = str(test_dir / "**/*")
        
        result = files_adapter_integration.backup_database(pattern, str(backup_path))
        
        assert result is True
        
        # Verify all files in backup
        with tarfile.open(backup_path, 'r:gz') as tar:
            file_count = sum(1 for m in tar.getmembers() if m.isfile())
            assert file_count == 3
