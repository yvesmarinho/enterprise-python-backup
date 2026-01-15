"""
Unit tests for schedule.manager module.

Tests schedule management, persistence, and execution tracking.
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import json

from python_backup.schedule.manager import ScheduleManager, ScheduleExecution
from python_backup.schedule.config import ScheduleConfig


class TestScheduleExecution:
    """Test ScheduleExecution tracking."""

    def test_create_execution_record(self):
        """Test creating an execution record."""
        execution = ScheduleExecution(
            schedule_name="daily_backup",
            start_time=datetime.now(),
            status="running"
        )
        
        assert execution.schedule_name == "daily_backup"
        assert execution.status == "running"

    def test_execution_complete(self):
        """Test marking execution as complete."""
        execution = ScheduleExecution(
            schedule_name="test",
            start_time=datetime.now(),
            status="running"
        )
        
        execution.complete(backup_file="/tmp/backup.sql.gz", backup_size=1024)
        
        assert execution.status == "completed"
        assert execution.backup_file == "/tmp/backup.sql.gz"
        assert execution.backup_size == 1024
        assert execution.end_time is not None

    def test_execution_fail(self):
        """Test marking execution as failed."""
        execution = ScheduleExecution(
            schedule_name="test",
            start_time=datetime.now(),
            status="running"
        )
        
        execution.fail("Database connection error")
        
        assert execution.status == "failed"
        assert execution.error_message == "Database connection error"
        assert execution.end_time is not None

    def test_execution_duration(self):
        """Test calculating execution duration."""
        start = datetime.now()
        execution = ScheduleExecution(
            schedule_name="test",
            start_time=start,
            status="running"
        )
        
        execution.complete("/tmp/backup.sql", 512)
        
        duration = execution.get_duration()
        assert duration is not None
        assert duration.total_seconds() >= 0

    def test_execution_to_dict(self):
        """Test converting execution to dictionary."""
        execution = ScheduleExecution(
            schedule_name="test",
            start_time=datetime.now(),
            status="completed",
            backup_file="/tmp/backup.sql",
            backup_size=2048
        )
        
        data = execution.to_dict()
        
        assert data["schedule_name"] == "test"
        assert data["status"] == "completed"
        assert data["backup_size"] == 2048


class TestScheduleManagerCreation:
    """Test ScheduleManager initialization."""

    def test_create_manager(self):
        """Test creating schedule manager."""
        manager = ScheduleManager(config_dir="/tmp/schedules")
        
        assert manager.config_dir == Path("/tmp/schedules")

    def test_create_manager_creates_directory(self):
        """Test that manager creates config directory."""
        test_dir = Path("/tmp/test_schedules_123")
        
        if test_dir.exists():
            import shutil
            shutil.rmtree(test_dir)
        
        manager = ScheduleManager(config_dir=str(test_dir))
        
        assert test_dir.exists()
        
        # Cleanup
        import shutil
        shutil.rmtree(test_dir)

    def test_manager_with_default_directory(self):
        """Test manager uses default directory."""
        manager = ScheduleManager()
        
        assert manager.config_dir is not None


class TestScheduleManagerCRUD:
    """Test schedule CRUD operations."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create manager with temp directory."""
        return ScheduleManager(config_dir=str(tmp_path))

    @pytest.fixture
    def sample_schedule(self):
        """Create sample schedule config."""
        return ScheduleConfig(
            name="test_backup",
            cron_expression="0 2 * * *",
            database_id="db1"
        )

    def test_add_schedule(self, manager, sample_schedule):
        """Test adding a schedule."""
        manager.add_schedule(sample_schedule)
        
        schedules = manager.list_schedules()
        assert len(schedules) == 1
        assert schedules[0].name == "test_backup"

    def test_add_duplicate_schedule_raises_error(self, manager, sample_schedule):
        """Test that adding duplicate raises error."""
        manager.add_schedule(sample_schedule)
        
        with pytest.raises(ValueError):
            manager.add_schedule(sample_schedule)

    def test_get_schedule(self, manager, sample_schedule):
        """Test getting a schedule by name."""
        manager.add_schedule(sample_schedule)
        
        retrieved = manager.get_schedule("test_backup")
        
        assert retrieved is not None
        assert retrieved.name == "test_backup"

    def test_get_nonexistent_schedule(self, manager):
        """Test getting schedule that doesn't exist."""
        schedule = manager.get_schedule("nonexistent")
        
        assert schedule is None

    def test_update_schedule(self, manager, sample_schedule):
        """Test updating a schedule."""
        manager.add_schedule(sample_schedule)
        
        updated = ScheduleConfig(
            name="test_backup",
            cron_expression="0 3 * * *",  # Changed time
            database_id="db1"
        )
        
        manager.update_schedule(updated)
        
        retrieved = manager.get_schedule("test_backup")
        assert "3" in retrieved.cron_expression

    def test_update_nonexistent_schedule_raises_error(self, manager):
        """Test updating nonexistent schedule raises error."""
        config = ScheduleConfig(
            name="nonexistent",
            cron_expression="0 2 * * *",
            database_id="db1"
        )
        
        with pytest.raises(ValueError):
            manager.update_schedule(config)

    def test_delete_schedule(self, manager, sample_schedule):
        """Test deleting a schedule."""
        manager.add_schedule(sample_schedule)
        
        manager.delete_schedule("test_backup")
        
        schedules = manager.list_schedules()
        assert len(schedules) == 0

    def test_delete_nonexistent_schedule(self, manager):
        """Test deleting nonexistent schedule doesn't raise error."""
        manager.delete_schedule("nonexistent")  # Should not raise

    def test_list_schedules_empty(self, manager):
        """Test listing schedules when none exist."""
        schedules = manager.list_schedules()
        
        assert schedules == []

    def test_list_schedules_multiple(self, manager):
        """Test listing multiple schedules."""
        schedule1 = ScheduleConfig(
            name="backup1",
            cron_expression="0 2 * * *",
            database_id="db1"
        )
        schedule2 = ScheduleConfig(
            name="backup2",
            cron_expression="0 3 * * *",
            database_id="db2"
        )
        
        manager.add_schedule(schedule1)
        manager.add_schedule(schedule2)
        
        schedules = manager.list_schedules()
        assert len(schedules) == 2


class TestScheduleManagerPersistence:
    """Test schedule persistence to disk."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create manager with temp directory."""
        return ScheduleManager(config_dir=str(tmp_path))

    def test_schedules_persisted_to_disk(self, manager, tmp_path):
        """Test that schedules are saved to disk."""
        schedule = ScheduleConfig(
            name="persistent_backup",
            cron_expression="0 2 * * *",
            database_id="db1"
        )
        
        manager.add_schedule(schedule)
        
        # Check file exists
        schedule_file = tmp_path / "persistent_backup.json"
        assert schedule_file.exists()

    def test_load_schedules_from_disk(self, manager, tmp_path):
        """Test loading schedules from disk."""
        # Create schedule and save
        schedule = ScheduleConfig(
            name="test_backup",
            cron_expression="0 2 * * *",
            database_id="db1"
        )
        manager.add_schedule(schedule)
        
        # Create new manager instance
        new_manager = ScheduleManager(config_dir=str(tmp_path))
        
        schedules = new_manager.list_schedules()
        assert len(schedules) == 1
        assert schedules[0].name == "test_backup"

    def test_update_schedule_updates_file(self, manager, tmp_path):
        """Test that updating schedule updates the file."""
        schedule = ScheduleConfig(
            name="test_backup",
            cron_expression="0 2 * * *",
            database_id="db1",
            retention_days=7
        )
        manager.add_schedule(schedule)
        
        updated = ScheduleConfig(
            name="test_backup",
            cron_expression="0 2 * * *",
            database_id="db1",
            retention_days=30  # Changed
        )
        manager.update_schedule(updated)
        
        # Reload and check
        new_manager = ScheduleManager(config_dir=str(tmp_path))
        retrieved = new_manager.get_schedule("test_backup")
        assert retrieved.retention_days == 30

    def test_delete_schedule_removes_file(self, manager, tmp_path):
        """Test that deleting schedule removes the file."""
        schedule = ScheduleConfig(
            name="test_backup",
            cron_expression="0 2 * * *",
            database_id="db1"
        )
        manager.add_schedule(schedule)
        
        schedule_file = tmp_path / "test_backup.json"
        assert schedule_file.exists()
        
        manager.delete_schedule("test_backup")
        
        assert not schedule_file.exists()


class TestScheduleManagerExecution:
    """Test schedule execution tracking."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create manager with temp directory."""
        return ScheduleManager(config_dir=str(tmp_path))

    def test_record_execution_start(self, manager):
        """Test recording execution start."""
        execution_id = manager.record_execution_start("test_backup")
        
        assert execution_id is not None
        
        execution = manager.get_execution(execution_id)
        assert execution.status == "running"

    def test_record_execution_complete(self, manager):
        """Test recording execution completion."""
        execution_id = manager.record_execution_start("test_backup")
        
        manager.record_execution_complete(
            execution_id,
            backup_file="/tmp/backup.sql",
            backup_size=1024
        )
        
        execution = manager.get_execution(execution_id)
        assert execution.status == "completed"
        assert execution.backup_size == 1024

    def test_record_execution_fail(self, manager):
        """Test recording execution failure."""
        execution_id = manager.record_execution_start("test_backup")
        
        manager.record_execution_fail(execution_id, "Database error")
        
        execution = manager.get_execution(execution_id)
        assert execution.status == "failed"
        assert "Database error" in execution.error_message

    def test_get_schedule_history(self, manager):
        """Test getting execution history for schedule."""
        # Record multiple executions
        exec1 = manager.record_execution_start("test_backup")
        manager.record_execution_complete(exec1, "/tmp/backup1.sql", 1024)
        
        exec2 = manager.record_execution_start("test_backup")
        manager.record_execution_fail(exec2, "Error")
        
        history = manager.get_schedule_history("test_backup")
        
        assert len(history) == 2

    def test_get_last_execution(self, manager):
        """Test getting last execution for schedule."""
        exec1 = manager.record_execution_start("test_backup")
        manager.record_execution_complete(exec1, "/tmp/backup1.sql", 1024)
        
        exec2 = manager.record_execution_start("test_backup")
        manager.record_execution_complete(exec2, "/tmp/backup2.sql", 2048)
        
        last = manager.get_last_execution("test_backup")
        
        assert last is not None
        assert last.backup_size == 2048


class TestScheduleManagerDueChecking:
    """Test checking for due schedules."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create manager with temp directory."""
        return ScheduleManager(config_dir=str(tmp_path))

    def test_get_due_schedules_empty(self, manager):
        """Test getting due schedules when none exist."""
        due = manager.get_due_schedules()
        
        assert due == []

    def test_get_due_schedules_none_due(self, manager):
        """Test when schedules exist but none are due."""
        # Schedule for 2am
        schedule = ScheduleConfig(
            name="backup",
            cron_expression="0 2 * * *",
            database_id="db1"
        )
        manager.add_schedule(schedule)
        
        # Check at 1am
        test_time = datetime.now().replace(hour=1, minute=0, second=0, microsecond=0)
        due = manager.get_due_schedules(current_time=test_time)
        
        assert len(due) == 0

    def test_get_due_schedules_with_disabled(self, manager):
        """Test that disabled schedules are not returned."""
        schedule = ScheduleConfig(
            name="backup",
            cron_expression="0 2 * * *",
            database_id="db1",
            enabled=False
        )
        manager.add_schedule(schedule)
        
        test_time = datetime.now().replace(hour=2, minute=0, second=0, microsecond=0)
        due = manager.get_due_schedules(current_time=test_time)
        
        assert len(due) == 0
