"""
Unit tests for utility functions.

Tests compression and retention policy utilities.
"""

import pytest
import gzip
import bz2
from pathlib import Path
from datetime import datetime, timedelta

from vya_backupbd.utils.compression import compress_file, decompress_file, get_compression_ratio
from vya_backupbd.utils.retention import (
    RetentionPolicy,
    should_keep_backup,
    apply_retention_policy,
    parse_retention_string
)


class TestCompressionGzip:
    """Test gzip compression utilities."""

    def test_compress_file_gzip(self, tmp_path):
        """Test compressing file with gzip."""
        # Create source file
        source = tmp_path / "backup.sql"
        content = "SELECT * FROM users;\n" * 100
        source.write_text(content)
        
        # Compress
        compressed = tmp_path / "backup.sql.gz"
        result = compress_file(source, compressed, method="gzip")
        
        assert result is True
        assert compressed.exists()
        assert compressed.stat().st_size < source.stat().st_size

    def test_decompress_file_gzip(self, tmp_path):
        """Test decompressing gzip file."""
        # Create and compress file
        source = tmp_path / "backup.sql"
        content = "SELECT * FROM users;\n" * 100
        source.write_text(content)
        
        compressed = tmp_path / "backup.sql.gz"
        with gzip.open(compressed, 'wb') as f:
            f.write(content.encode())
        
        # Decompress
        decompressed = tmp_path / "restored.sql"
        result = decompress_file(compressed, decompressed, method="gzip")
        
        assert result is True
        assert decompressed.exists()
        assert decompressed.read_text() == content

    def test_compression_ratio_gzip(self, tmp_path):
        """Test calculating compression ratio."""
        source = tmp_path / "backup.sql"
        content = "SELECT * FROM users;\n" * 100
        source.write_text(content)
        
        compressed = tmp_path / "backup.sql.gz"
        compress_file(source, compressed, method="gzip")
        
        ratio = get_compression_ratio(source, compressed)
        
        assert ratio > 1.0  # Should be compressed


class TestCompressionBzip2:
    """Test bzip2 compression utilities."""

    def test_compress_file_bzip2(self, tmp_path):
        """Test compressing file with bzip2."""
        source = tmp_path / "backup.sql"
        content = "SELECT * FROM users;\n" * 100
        source.write_text(content)
        
        compressed = tmp_path / "backup.sql.bz2"
        result = compress_file(source, compressed, method="bzip2")
        
        assert result is True
        assert compressed.exists()
        assert compressed.stat().st_size < source.stat().st_size

    def test_decompress_file_bzip2(self, tmp_path):
        """Test decompressing bzip2 file."""
        source = tmp_path / "backup.sql"
        content = "SELECT * FROM users;\n" * 100
        source.write_text(content)
        
        compressed = tmp_path / "backup.sql.bz2"
        with bz2.open(compressed, 'wb') as f:
            f.write(content.encode())
        
        decompressed = tmp_path / "restored.sql"
        result = decompress_file(compressed, decompressed, method="bzip2")
        
        assert result is True
        assert decompressed.read_text() == content

    def test_bzip2_better_compression(self, tmp_path):
        """Test that bzip2 achieves better compression than gzip."""
        source = tmp_path / "backup.sql"
        content = "SELECT * FROM users;\n" * 1000
        source.write_text(content)
        
        gzip_file = tmp_path / "backup.sql.gz"
        bz2_file = tmp_path / "backup.sql.bz2"
        
        compress_file(source, gzip_file, method="gzip")
        compress_file(source, bz2_file, method="bzip2")
        
        # bzip2 should be smaller (for repetitive text)
        assert bz2_file.stat().st_size < gzip_file.stat().st_size


class TestCompressionEdgeCases:
    """Test compression edge cases."""

    def test_compress_empty_file(self, tmp_path):
        """Test compressing empty file."""
        source = tmp_path / "empty.sql"
        source.write_text("")
        
        compressed = tmp_path / "empty.sql.gz"
        result = compress_file(source, compressed)
        
        assert result is True
        assert compressed.exists()

    def test_compress_nonexistent_file(self, tmp_path):
        """Test compressing non-existent file."""
        source = tmp_path / "missing.sql"
        compressed = tmp_path / "missing.sql.gz"
        
        result = compress_file(source, compressed)
        
        assert result is False

    def test_decompress_invalid_file(self, tmp_path):
        """Test decompressing invalid gzip file."""
        invalid = tmp_path / "invalid.gz"
        invalid.write_text("not a gzip file")
        
        output = tmp_path / "output.sql"
        result = decompress_file(invalid, output)
        
        assert result is False

    def test_auto_detect_compression_method(self, tmp_path):
        """Test auto-detecting compression method from extension."""
        source = tmp_path / "backup.sql"
        source.write_text("data")
        
        # Should detect gzip from .gz extension
        gz_file = tmp_path / "backup.sql.gz"
        result = compress_file(source, gz_file)  # No method specified
        assert result is True
        
        # Should detect bzip2 from .bz2 extension
        bz2_file = tmp_path / "backup.sql.bz2"
        result = compress_file(source, bz2_file)  # No method specified
        assert result is True


class TestRetentionPolicy:
    """Test retention policy class."""

    def test_policy_creation_hourly(self):
        """Test creating hourly retention policy."""
        policy = RetentionPolicy(
            hourly=24,
            daily=7,
            weekly=4,
            monthly=12
        )
        
        assert policy.hourly == 24
        assert policy.daily == 7
        assert policy.weekly == 4
        assert policy.monthly == 12

    def test_policy_from_dict(self):
        """Test creating policy from dictionary."""
        config = {
            "hourly": 48,
            "daily": 14,
            "weekly": 8,
            "monthly": 6
        }
        
        policy = RetentionPolicy(**config)
        
        assert policy.hourly == 48
        assert policy.daily == 14

    def test_parse_retention_string(self):
        """Test parsing retention string."""
        retention_str = "7d,4w,12m"
        
        policy = parse_retention_string(retention_str)
        
        assert policy.daily == 7
        assert policy.weekly == 4
        assert policy.monthly == 12


class TestRetentionPolicyLogic:
    """Test retention policy logic."""

    def test_keep_recent_backups(self):
        """Test keeping recent backups (within hourly window)."""
        policy = RetentionPolicy(hourly=24, daily=7, weekly=4, monthly=12)
        
        # Backup from 2 hours ago
        backup_time = datetime.now() - timedelta(hours=2)
        
        result = should_keep_backup(backup_time, policy, datetime.now())
        
        assert result is True

    def test_keep_daily_backups(self):
        """Test keeping daily backups."""
        policy = RetentionPolicy(hourly=24, daily=7, weekly=4, monthly=12)
        
        # Backup from 3 days ago (within daily retention)
        backup_time = datetime.now() - timedelta(days=3)
        
        result = should_keep_backup(backup_time, policy, datetime.now())
        
        assert result is True

    def test_discard_old_backup(self):
        """Test discarding old backup outside retention."""
        policy = RetentionPolicy(hourly=24, daily=7, weekly=4, monthly=12)
        
        # Backup from 13 months ago (outside all retention)
        backup_time = datetime.now() - timedelta(days=400)
        
        result = should_keep_backup(backup_time, policy, datetime.now())
        
        assert result is False

    def test_keep_weekly_backups(self):
        """Test keeping weekly backups."""
        policy = RetentionPolicy(hourly=0, daily=0, weekly=4, monthly=0)
        
        # Backup from 2 weeks ago
        backup_time = datetime.now() - timedelta(weeks=2)
        
        result = should_keep_backup(backup_time, policy, datetime.now())
        
        assert result is True

    def test_keep_monthly_backups(self):
        """Test keeping monthly backups."""
        policy = RetentionPolicy(hourly=0, daily=0, weekly=0, monthly=6)
        
        # Backup from 3 months ago
        backup_time = datetime.now() - timedelta(days=90)
        
        result = should_keep_backup(backup_time, policy, datetime.now())
        
        assert result is True


class TestRetentionPolicyApplication:
    """Test applying retention policy to backups."""

    def test_apply_retention_policy(self):
        """Test applying retention policy to list of backups."""
        policy = RetentionPolicy(hourly=24, daily=7, weekly=4, monthly=12)
        now = datetime.now()
        
        # Create list of backups with timestamps
        backups = [
            {"file": "backup1.sql", "timestamp": now - timedelta(hours=1)},
            {"file": "backup2.sql", "timestamp": now - timedelta(days=3)},
            {"file": "backup3.sql", "timestamp": now - timedelta(days=400)},
            {"file": "backup4.sql", "timestamp": now - timedelta(weeks=2)},
        ]
        
        to_keep, to_delete = apply_retention_policy(backups, policy, now)
        
        # First 3 should be kept, last one (400 days) should be deleted
        assert len(to_keep) == 3
        assert len(to_delete) == 1
        assert to_delete[0]["file"] == "backup3.sql"

    def test_apply_policy_keeps_all_recent(self):
        """Test that policy keeps all recent backups."""
        policy = RetentionPolicy(hourly=24, daily=7, weekly=4, monthly=12)
        now = datetime.now()
        
        # All backups within last 24 hours
        backups = [
            {"file": f"backup{i}.sql", "timestamp": now - timedelta(hours=i)}
            for i in range(1, 20)
        ]
        
        to_keep, to_delete = apply_retention_policy(backups, policy, now)
        
        assert len(to_keep) == 19
        assert len(to_delete) == 0

    def test_apply_policy_granular_retention(self):
        """Test granular retention (different frequencies)."""
        policy = RetentionPolicy(hourly=6, daily=3, weekly=2, monthly=1)
        now = datetime.now()
        
        backups = [
            {"file": "hourly.sql", "timestamp": now - timedelta(hours=3)},
            {"file": "daily.sql", "timestamp": now - timedelta(days=2)},
            {"file": "weekly.sql", "timestamp": now - timedelta(weeks=1)},
            {"file": "monthly.sql", "timestamp": now - timedelta(days=20)},
            {"file": "old.sql", "timestamp": now - timedelta(days=100)},
        ]
        
        to_keep, to_delete = apply_retention_policy(backups, policy, now)
        
        # Should keep first 4, delete last one
        assert len(to_keep) == 4
        assert len(to_delete) == 1


class TestRetentionPolicyEdgeCases:
    """Test retention policy edge cases."""

    def test_zero_retention(self):
        """Test policy with zero retention (keep nothing)."""
        policy = RetentionPolicy(hourly=0, daily=0, weekly=0, monthly=0)
        
        backup_time = datetime.now() - timedelta(hours=1)
        result = should_keep_backup(backup_time, policy, datetime.now())
        
        # With zero retention, should not keep any backups
        assert result is False

    def test_infinite_retention(self):
        """Test policy with very large retention."""
        policy = RetentionPolicy(hourly=0, daily=0, weekly=0, monthly=9999)
        
        # Very old backup
        backup_time = datetime.now() - timedelta(days=3000)
        result = should_keep_backup(backup_time, policy, datetime.now())
        
        assert result is True

    def test_empty_backup_list(self):
        """Test applying policy to empty backup list."""
        policy = RetentionPolicy(hourly=24, daily=7, weekly=4, monthly=12)
        
        to_keep, to_delete = apply_retention_policy([], policy, datetime.now())
        
        assert to_keep == []
        assert to_delete == []


class TestRetentionPolicyIntegration:
    """Integration tests for retention policy."""

    def test_realistic_retention_scenario(self):
        """Test realistic retention scenario."""
        # Keep: 24 hourly, 7 daily, 4 weekly, 12 monthly
        policy = RetentionPolicy(hourly=24, daily=7, weekly=4, monthly=12)
        now = datetime.now()
        
        # Simulate backups taken every hour for last 30 days
        backups = []
        for hours_ago in range(0, 30 * 24):  # 30 days of hourly backups
            backups.append({
                "file": f"backup_{hours_ago}.sql",
                "timestamp": now - timedelta(hours=hours_ago)
            })
        
        to_keep, to_delete = apply_retention_policy(backups, policy, now)
        
        # Policy keeps ALL backups within each retention window
        # - All backups within last 24 hours (24 backups)
        # - All backups within last 7 days (168 backups)
        # - All backups within last 4 weeks (672 backups)
        # - All backups within last 12 months (720 backups for 30 days)
        # Since 30 days is within 12 months, ALL 720 backups should be kept
        assert len(to_keep) == 720  # All backups within retention
        assert len(to_delete) == 0  # None outside retention

    def test_retention_with_missing_backups(self):
        """Test retention with gaps in backup schedule."""
        policy = RetentionPolicy(hourly=24, daily=7, weekly=4, monthly=12)
        now = datetime.now()
        
        # Irregular backup times (missed some backups)
        backups = [
            {"file": "backup1.sql", "timestamp": now - timedelta(hours=1)},
            {"file": "backup2.sql", "timestamp": now - timedelta(hours=5)},
            {"file": "backup3.sql", "timestamp": now - timedelta(days=2)},
            {"file": "backup4.sql", "timestamp": now - timedelta(days=6)},
            {"file": "backup5.sql", "timestamp": now - timedelta(weeks=3)},
        ]
        
        to_keep, to_delete = apply_retention_policy(backups, policy, now)
        
        # All should be kept as they're within retention periods
        assert len(to_keep) == 5
        assert len(to_delete) == 0
