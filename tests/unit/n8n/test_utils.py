"""Unit tests for utility functions."""

import pytest
from pathlib import Path
from datetime import datetime
import tempfile
import json

from enterprise_backup.n8n.utils import (
    generate_timestamp,
    get_hostname,
    calculate_sha256,
    calculate_directory_sha256,
    format_backup_path,
    validate_json_file,
    validate_json_structure,
    load_json_file,
    save_json_file,
)
from enterprise_backup.n8n.models import BackupType


class TestTimestampGeneration:
    """Test timestamp generation."""

    def test_generate_timestamp_format(self):
        """Test timestamp format is YYYYMMDD-HHMMSS."""
        timestamp = generate_timestamp()
        
        # Should be 15 characters: YYYYMMDD-HHMMSS
        assert len(timestamp) == 15
        assert timestamp[8] == "-"
        
        # Should be parseable as datetime
        dt = datetime.strptime(timestamp, "%Y%m%d-%H%M%S")
        assert isinstance(dt, datetime)

    def test_generate_timestamp_unique(self):
        """Test consecutive timestamps are different (or very close)."""
        timestamp1 = generate_timestamp()
        timestamp2 = generate_timestamp()
        
        # Should be same or sequential (if called within same second)
        assert timestamp1 <= timestamp2


class TestHostnameGeneration:
    """Test hostname generation."""

    def test_get_hostname_returns_string(self):
        """Test hostname is a non-empty string."""
        hostname = get_hostname()
        
        assert isinstance(hostname, str)
        assert len(hostname) > 0

    def test_get_hostname_sanitized(self):
        """Test hostname contains only alphanumeric and hyphen."""
        hostname = get_hostname()
        
        # Should only contain alphanumeric and hyphen
        assert all(c.isalnum() or c == "-" for c in hostname)


class TestSHA256Calculation:
    """Test SHA256 checksum calculation."""

    def test_calculate_sha256_empty_file(self):
        """Test SHA256 of empty file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_file = Path(f.name)
        
        try:
            checksum = calculate_sha256(temp_file)
            
            # SHA256 of empty file
            assert checksum == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        finally:
            temp_file.unlink()

    def test_calculate_sha256_with_content(self):
        """Test SHA256 of file with content."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_file = Path(f.name)
        
        try:
            checksum = calculate_sha256(temp_file)
            
            # Should be 64 character hex string
            assert len(checksum) == 64
            assert all(c in "0123456789abcdef" for c in checksum)
        finally:
            temp_file.unlink()

    def test_calculate_directory_sha256(self):
        """Test SHA256 of directory with multiple files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dir_path = Path(temp_dir)
            
            # Create test files
            (dir_path / "file1.txt").write_text("content1")
            (dir_path / "file2.txt").write_text("content2")
            
            checksum = calculate_directory_sha256(dir_path)
            
            # Should be 64 character hex string
            assert len(checksum) == 64
            assert all(c in "0123456789abcdef" for c in checksum)


class TestBackupPathFormatting:
    """Test backup path formatting."""

    def test_format_backup_path_full(self):
        """Test backup path formatting for full backup."""
        base_path = Path("/tmp/backups")
        timestamp = "20260120-143000"
        hostname = "server01"
        backup_type = BackupType.FULL
        
        path = format_backup_path(base_path, timestamp, hostname, backup_type)
        
        assert "20260120-143000" in str(path)
        assert "server01" in str(path)
        assert "full" in str(path)

    def test_format_backup_path_credentials(self):
        """Test backup path formatting for credentials."""
        base_path = Path("/tmp/backups")
        timestamp = "20260120-143000"
        hostname = "server01"
        backup_type = BackupType.CREDENTIALS
        
        path = format_backup_path(base_path, timestamp, hostname, backup_type)
        
        assert "credentials" in str(path)


class TestJSONValidation:
    """Test JSON validation functions."""

    def test_validate_json_file_valid(self):
        """Test validation of valid JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"key": "value"}, f)
            temp_file = Path(f.name)
        
        try:
            assert validate_json_file(temp_file) is True
        finally:
            temp_file.unlink()

    def test_validate_json_file_invalid(self):
        """Test validation of invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            temp_file = Path(f.name)
        
        try:
            assert validate_json_file(temp_file) is False
        finally:
            temp_file.unlink()

    def test_validate_json_structure_with_fields(self):
        """Test JSON structure validation with required fields."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"id": "123", "name": "test", "type": "credential"}, f)
            temp_file = Path(f.name)
        
        try:
            assert validate_json_structure(temp_file, ["id", "name", "type"]) is True
            assert validate_json_structure(temp_file, ["id", "missing_field"]) is False
        finally:
            temp_file.unlink()


class TestJSONFileOperations:
    """Test JSON file load/save operations."""

    def test_load_json_file(self):
        """Test loading JSON file."""
        test_data = {"key": "value", "number": 42}
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_file = Path(f.name)
        
        try:
            loaded_data = load_json_file(temp_file)
            
            assert loaded_data == test_data
            assert loaded_data["key"] == "value"
            assert loaded_data["number"] == 42
        finally:
            temp_file.unlink()

    def test_save_json_file(self):
        """Test saving JSON file."""
        test_data = {"key": "value", "list": [1, 2, 3]}
        
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_file = Path(f.name)
        
        try:
            save_json_file(test_data, temp_file)
            
            # Verify file was created and content is correct
            assert temp_file.exists()
            
            with open(temp_file) as f:
                loaded_data = json.load(f)
            
            assert loaded_data == test_data
        finally:
            if temp_file.exists():
                temp_file.unlink()

    def test_save_json_file_atomic(self):
        """Test atomic save (temp file + rename)."""
        test_data = {"atomic": True}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file = Path(temp_dir) / "test.json"
            
            save_json_file(test_data, temp_file)
            
            assert temp_file.exists()
            loaded_data = load_json_file(temp_file)
            assert loaded_data["atomic"] is True
