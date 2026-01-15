"""
Unit tests for schedule.config module.

Tests schedule configuration and cron expression handling.
"""

import pytest
from datetime import datetime, timedelta
from python_backup.schedule.config import ScheduleConfig, CronExpression


class TestCronExpression:
    """Test CronExpression parsing and validation."""

    def test_create_cron_expression(self):
        """Test creating a cron expression."""
        cron = CronExpression("0 2 * * *")
        assert cron.expression == "0 2 * * *"

    def test_parse_hourly_cron(self):
        """Test parsing hourly cron expression."""
        cron = CronExpression("0 * * * *")
        assert cron.is_valid() is True

    def test_parse_daily_cron(self):
        """Test parsing daily cron expression."""
        cron = CronExpression("0 2 * * *")
        assert cron.is_valid() is True

    def test_parse_weekly_cron(self):
        """Test parsing weekly cron expression."""
        cron = CronExpression("0 3 * * 0")  # Sunday at 3am
        assert cron.is_valid() is True

    def test_parse_monthly_cron(self):
        """Test parsing monthly cron expression."""
        cron = CronExpression("0 4 1 * *")  # 1st day at 4am
        assert cron.is_valid() is True

    def test_invalid_cron_expression(self):
        """Test that invalid cron raises error."""
        with pytest.raises(ValueError):
            cron = CronExpression("invalid")
            cron.is_valid()

    def test_cron_with_too_many_fields(self):
        """Test cron with wrong number of fields."""
        with pytest.raises(ValueError):
            cron = CronExpression("0 2 * * * *")  # 6 fields instead of 5
            cron.is_valid()

    def test_get_next_run_time(self):
        """Test calculating next run time from cron."""
        cron = CronExpression("0 2 * * *")  # Daily at 2am
        base_time = datetime(2026, 1, 12, 1, 0, 0)
        
        next_run = cron.get_next_run(base_time)
        
        assert next_run.hour == 2
        assert next_run.minute == 0

    def test_get_next_run_after_time(self):
        """Test next run when base time is after schedule."""
        cron = CronExpression("0 2 * * *")  # Daily at 2am
        base_time = datetime(2026, 1, 12, 3, 0, 0)  # 3am
        
        next_run = cron.get_next_run(base_time)
        
        # Should be tomorrow at 2am
        assert next_run.day == 13
        assert next_run.hour == 2

    def test_cron_description(self):
        """Test getting human-readable description."""
        cron = CronExpression("0 2 * * *")
        description = cron.get_description()
        
        # cron-descriptor returns "At 02:00"
        assert "02:00" in description or "2:00" in description


class TestScheduleConfig:
    """Test ScheduleConfig model."""

    def test_create_schedule_config(self):
        """Test creating a schedule configuration."""
        config = ScheduleConfig(
            name="daily_backup",
            cron_expression="0 2 * * *",
            database_id="db1",
            enabled=True
        )
        
        assert config.name == "daily_backup"
        assert config.database_id == "db1"
        assert config.enabled is True

    def test_schedule_config_with_retention(self):
        """Test schedule with retention policy."""
        config = ScheduleConfig(
            name="weekly_backup",
            cron_expression="0 3 * * 0",
            database_id="db2",
            retention_days=30
        )
        
        assert config.retention_days == 30

    def test_schedule_config_with_compression(self):
        """Test schedule with compression."""
        config = ScheduleConfig(
            name="compressed_backup",
            cron_expression="0 4 * * *",
            database_id="db3",
            compression="gzip"
        )
        
        assert config.compression == "gzip"

    def test_schedule_config_with_storage_location(self):
        """Test schedule with custom storage."""
        config = ScheduleConfig(
            name="s3_backup",
            cron_expression="0 5 * * *",
            database_id="db4",
            storage_type="s3",
            storage_location="s3://my-bucket/backups"
        )
        
        assert config.storage_type == "s3"
        assert config.storage_location == "s3://my-bucket/backups"

    def test_schedule_config_disabled(self):
        """Test creating disabled schedule."""
        config = ScheduleConfig(
            name="disabled_backup",
            cron_expression="0 6 * * *",
            database_id="db5",
            enabled=False
        )
        
        assert config.enabled is False

    def test_get_next_run_time(self):
        """Test getting next scheduled run time."""
        config = ScheduleConfig(
            name="test_backup",
            cron_expression="0 2 * * *",
            database_id="db1"
        )
        
        next_run = config.get_next_run()
        
        assert isinstance(next_run, datetime)
        assert next_run > datetime.now()

    def test_is_due(self):
        """Test checking if schedule is due to run."""
        # Create schedule for 2am
        config = ScheduleConfig(
            name="test_backup",
            cron_expression="0 2 * * *",
            database_id="db1"
        )
        
        # Test at 1am (not due)
        test_time = datetime.now().replace(hour=1, minute=0, second=0)
        assert config.is_due(test_time) is False
        
        # Test at 2am (due)
        test_time = datetime.now().replace(hour=2, minute=0, second=0)
        assert config.is_due(test_time) is True

    def test_schedule_to_dict(self):
        """Test converting schedule to dictionary."""
        config = ScheduleConfig(
            name="test_backup",
            cron_expression="0 2 * * *",
            database_id="db1",
            retention_days=7,
            compression="gzip"
        )
        
        data = config.to_dict()
        
        assert data["name"] == "test_backup"
        assert data["cron_expression"] == "0 2 * * *"
        assert data["database_id"] == "db1"
        assert data["retention_days"] == 7
        assert data["compression"] == "gzip"

    def test_schedule_validation_missing_name(self):
        """Test that missing name raises error."""
        with pytest.raises(ValueError):
            ScheduleConfig(
                name="",
                cron_expression="0 2 * * *",
                database_id="db1"
            )

    def test_schedule_validation_invalid_cron(self):
        """Test that invalid cron raises error."""
        with pytest.raises(ValueError):
            ScheduleConfig(
                name="test",
                cron_expression="invalid",
                database_id="db1"
            )

    def test_schedule_validation_invalid_compression(self):
        """Test that invalid compression type raises error."""
        with pytest.raises(ValueError):
            ScheduleConfig(
                name="test",
                cron_expression="0 2 * * *",
                database_id="db1",
                compression="invalid"
            )

    def test_schedule_validation_negative_retention(self):
        """Test that negative retention raises error."""
        with pytest.raises(ValueError):
            ScheduleConfig(
                name="test",
                cron_expression="0 2 * * *",
                database_id="db1",
                retention_days=-1
            )


class TestScheduleConfigPresets:
    """Test schedule configuration presets."""

    def test_create_hourly_schedule(self):
        """Test creating hourly schedule preset."""
        config = ScheduleConfig.create_hourly("hourly_backup", "db1")
        
        assert config.name == "hourly_backup"
        assert config.cron_expression == "0 * * * *"

    def test_create_daily_schedule(self):
        """Test creating daily schedule preset."""
        config = ScheduleConfig.create_daily("daily_backup", "db1", hour=2)
        
        assert config.name == "daily_backup"
        assert "2" in config.cron_expression

    def test_create_weekly_schedule(self):
        """Test creating weekly schedule preset."""
        config = ScheduleConfig.create_weekly(
            "weekly_backup", 
            "db1", 
            day_of_week=0,  # Sunday
            hour=3
        )
        
        assert config.name == "weekly_backup"
        assert "0" in config.cron_expression  # Sunday

    def test_create_monthly_schedule(self):
        """Test creating monthly schedule preset."""
        config = ScheduleConfig.create_monthly(
            "monthly_backup",
            "db1",
            day_of_month=1,
            hour=4
        )
        
        assert config.name == "monthly_backup"
        assert "1" in config.cron_expression
