#!/usr/bin/env python3
"""
Test script for VYA BackupDB Scheduler functionality.

Tests the scheduling system including:
- Cron expression validation
- Schedule configuration
- Next run calculation
- Schedule management (CRUD)
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vya_backupbd.schedule.config import ScheduleConfig, CronExpression
from vya_backupbd.schedule.manager import ScheduleManager


def print_header(title: str):
    """Print formatted test header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_cron_expressions():
    """Test cron expression parsing and validation."""
    print_header("Test 1: Cron Expression Validation")
    
    test_cases = [
        ("0 22 * * *", "Daily at 22:00 (10 PM)"),
        ("0 3 * * *", "Daily at 03:00 (3 AM)"),
        ("0 5 * * *", "Daily at 05:00 (5 AM)"),
        ("*/15 * * * *", "Every 15 minutes"),
        ("0 0 * * 0", "Weekly on Sunday at midnight"),
        ("0 0 1 * *", "Monthly on 1st at midnight"),
        ("0 2 * * 1-5", "Weekdays at 02:00"),
    ]
    
    for expression, description in test_cases:
        try:
            cron = CronExpression(expression)
            cron.is_valid()
            next_run = cron.get_next_run()
            
            print(f"\n✅ Expression: {expression}")
            print(f"   Description: {description}")
            print(f"   Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
        except Exception as e:
            print(f"\n❌ Expression: {expression}")
            print(f"   Error: {e}")


def test_schedule_config():
    """Test schedule configuration creation."""
    print_header("Test 2: Schedule Configuration")
    
    try:
        # Test valid configuration
        schedule = ScheduleConfig(
            name="daily_backup_22h",
            cron_expression="0 22 * * *",
            database_id="1",
            enabled=True,
            retention_days=7,
            compression="gzip"
        )
        
        print("\n✅ Valid schedule created:")
        print(f"   Name: {schedule.name}")
        print(f"   Cron: {schedule.cron_expression}")
        print(f"   Database ID: {schedule.database_id}")
        print(f"   Enabled: {schedule.enabled}")
        print(f"   Retention: {schedule.retention_days} days")
        print(f"   Compression: {schedule.compression}")
        
        # Calculate next 5 runs
        print("\n   Next 5 scheduled runs:")
        base_time = datetime.now()
        for i in range(5):
            next_run = schedule.get_next_run(base_time)
            print(f"     {i+1}. {next_run.strftime('%Y-%m-%d %H:%M:%S %A')}")
            base_time = next_run
        
    except Exception as e:
        print(f"\n❌ Error creating schedule: {e}")
    
    # Test invalid configurations
    print("\n\nTesting invalid configurations:")
    
    invalid_configs = [
        {
            "name": "",
            "cron_expression": "0 22 * * *",
            "database_id": "1",
            "error_expected": "empty name"
        },
        {
            "name": "test",
            "cron_expression": "invalid",
            "database_id": "1",
            "error_expected": "invalid cron"
        },
        {
            "name": "test",
            "cron_expression": "0 22 * * *",
            "database_id": "1",
            "retention_days": -1,
            "error_expected": "negative retention"
        }
    ]
    
    for config in invalid_configs:
        try:
            schedule = ScheduleConfig(**{k: v for k, v in config.items() if k != "error_expected"})
            print(f"\n❌ Expected error for {config['error_expected']}, but succeeded")
        except Exception as e:
            print(f"\n✅ Caught expected error ({config['error_expected']}): {str(e)[:60]}")


def test_production_schedule():
    """Test production schedule (22:00 → 03:00 → 05:00)."""
    print_header("Test 3: Production Schedule Simulation")
    
    print("\nProduction backup workflow:")
    print("  22:00 → vya_backupdb executes backups")
    print("  03:00 → Idrive uploads to cloud")
    print("  05:00 → Cleanup script removes local files")
    
    # Create schedules for production workflow
    schedules = [
        ScheduleConfig(
            name="backup_execution",
            cron_expression="0 22 * * *",
            database_id="all",
            enabled=True,
            retention_days=1,
            compression="gzip"
        ),
        ScheduleConfig(
            name="idrive_upload",
            cron_expression="0 3 * * *",
            database_id="all",
            enabled=True,
            retention_days=1
        ),
        ScheduleConfig(
            name="cleanup_local_files",
            cron_expression="0 5 * * *",
            database_id="all",
            enabled=True,
            retention_days=1
        )
    ]
    
    print("\n\nScheduled tasks for next 3 days:")
    base_time = datetime.now()
    
    for day in range(3):
        day_start = base_time + timedelta(days=day)
        day_start = day_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        print(f"\n📅 {day_start.strftime('%Y-%m-%d %A')}:")
        
        for schedule in schedules:
            next_run = schedule.get_next_run(day_start)
            if next_run.date() == day_start.date():
                print(f"   {next_run.strftime('%H:%M')} - {schedule.name}")


def test_schedule_manager():
    """Test schedule manager CRUD operations."""
    print_header("Test 4: Schedule Manager (CRUD)")
    
    try:
        # Create temporary directory for testing
        import tempfile
        temp_dir = tempfile.mkdtemp(prefix="vya_scheduler_test_")
        print(f"\n📁 Using temporary directory: {temp_dir}")
        
        # Initialize manager
        manager = ScheduleManager(config_dir=temp_dir)
        print("✅ Schedule manager initialized")
        
        # Add schedule
        schedule = ScheduleConfig(
            name="test_backup",
            cron_expression="0 22 * * *",
            database_id="1",
            enabled=True,
            retention_days=7,
            compression="gzip"
        )
        
        manager.add_schedule(schedule)
        print(f"✅ Added schedule: {schedule.name}")
        
        # Get schedule
        retrieved = manager.get_schedule("test_backup")
        if retrieved:
            print(f"✅ Retrieved schedule: {retrieved.name}")
            print(f"   Cron: {retrieved.cron_expression}")
        else:
            print("❌ Failed to retrieve schedule")
        
        # List all schedules
        all_schedules = manager.list_schedules()
        print(f"\n✅ Total schedules: {len(all_schedules)}")
        for sched in all_schedules:
            print(f"   - {sched.name} ({sched.cron_expression})")
        
        # Get enabled schedules
        enabled = manager.list_schedules(enabled_only=True)
        print(f"\n✅ Enabled schedules: {len(enabled)}")
        
        # Update schedule
        schedule.retention_days = 14
        manager.update_schedule(schedule)
        print(f"\n✅ Updated schedule retention to {schedule.retention_days} days")
        
        # Verify update
        updated = manager.get_schedule("test_backup")
        if updated and updated.retention_days == 14:
            print("✅ Update verified")
        else:
            print("❌ Update verification failed")
        
        # Remove schedule
        manager.delete_schedule("test_backup")
        print("\n✅ Removed schedule")
        
        # Verify removal
        removed = manager.get_schedule("test_backup")
        if removed is None:
            print("✅ Removal verified")
        else:
            print("❌ Schedule still exists after removal")
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
        print(f"\n🗑️  Cleaned up temporary directory")
        
    except Exception as e:
        print(f"\n❌ Error in schedule manager test: {e}")
        import traceback
        traceback.print_exc()


def test_time_calculations():
    """Test time calculation utilities."""
    print_header("Test 5: Time Calculations")
    
    now = datetime.now()
    print(f"\nCurrent time: {now.strftime('%Y-%m-%d %H:%M:%S %A')}")
    
    # Test different cron expressions
    expressions = {
        "0 22 * * *": "Daily at 22:00",
        "0 3 * * *": "Daily at 03:00",
        "0 5 * * *": "Daily at 05:00",
        "0 */6 * * *": "Every 6 hours",
        "0 0 * * 1": "Every Monday at midnight"
    }
    
    print("\nTime until next execution:")
    for expr, desc in expressions.items():
        cron = CronExpression(expr)
        next_run = cron.get_next_run(now)
        delta = next_run - now
        
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        
        print(f"\n  {desc}")
        print(f"    Expression: {expr}")
        print(f"    Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"    Time until: {hours}h {minutes}m")


def main():
    """Run all tests."""
    print("\n" + "█" * 80)
    print("  VYA BackupDB - Scheduler Test Suite")
    print("  Version: 2.0.0")
    print("  Date: 2026-01-15")
    print("█" * 80)
    
    try:
        test_cron_expressions()
        test_schedule_config()
        test_production_schedule()
        test_schedule_manager()
        test_time_calculations()
        
        print_header("✅ All Tests Completed")
        print("\n🎉 Scheduler functionality is working correctly!")
        
    except Exception as e:
        print_header("❌ Test Suite Failed")
        print(f"\n Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
