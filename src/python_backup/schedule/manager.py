"""
Schedule manager for persisting and tracking backup schedules.
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from uuid import uuid4

from python_backup.schedule.config import ScheduleConfig

logger = logging.getLogger(__name__)


@dataclass
class ScheduleExecution:
    """Record of a schedule execution."""
    
    schedule_name: str
    start_time: datetime
    status: str  # running, completed, failed
    execution_id: str = field(default_factory=lambda: str(uuid4()))
    end_time: Optional[datetime] = None
    backup_file: Optional[str] = None
    backup_size: Optional[int] = None
    error_message: Optional[str] = None
    
    def complete(self, backup_file: str, backup_size: int) -> None:
        """Mark execution as completed."""
        self.status = "completed"
        self.end_time = datetime.now()
        self.backup_file = backup_file
        self.backup_size = backup_size
    
    def fail(self, error_message: str) -> None:
        """Mark execution as failed."""
        self.status = "failed"
        self.end_time = datetime.now()
        self.error_message = error_message
    
    def get_duration(self) -> Optional[timedelta]:
        """Get execution duration."""
        if self.start_time is None:
            return None
        
        end = self.end_time if self.end_time else datetime.now()
        return end - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert execution to dictionary."""
        result = {
            "execution_id": self.execution_id,
            "schedule_name": self.schedule_name,
            "status": self.status,
            "start_time": self.start_time.isoformat() if self.start_time else None,
        }
        
        if self.end_time:
            result["end_time"] = self.end_time.isoformat()
        
        if self.backup_file:
            result["backup_file"] = self.backup_file
        if self.backup_size:
            result["backup_size"] = self.backup_size
        if self.error_message:
            result["error_message"] = self.error_message
        
        duration = self.get_duration()
        if duration:
            result["duration"] = str(duration)
        
        return result


class ScheduleManager:
    """
    Manager for backup schedules.
    
    Handles schedule CRUD operations, persistence, and execution tracking.
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize schedule manager.
        
        Args:
            config_dir: Directory for schedule configuration files
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path.home() / ".vya_backupdb" / "schedules"
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self._schedules: Dict[str, ScheduleConfig] = {}
        self._executions: Dict[str, ScheduleExecution] = {}
        
        self._load_schedules()
    
    def _load_schedules(self) -> None:
        """Load schedules from disk."""
        for schedule_file in self.config_dir.glob("*.json"):
            try:
                with open(schedule_file, 'r') as f:
                    data = json.load(f)
                    schedule = ScheduleConfig.from_dict(data)
                    self._schedules[schedule.name] = schedule
                    logger.info(f"Loaded schedule: {schedule.name}")
            except Exception as e:
                logger.error(f"Failed to load schedule from {schedule_file}: {e}")
    
    def _save_schedule(self, schedule: ScheduleConfig) -> None:
        """Save schedule to disk."""
        schedule_file = self.config_dir / f"{schedule.name}.json"
        with open(schedule_file, 'w') as f:
            json.dump(schedule.to_dict(), f, indent=2)
    
    def _delete_schedule_file(self, schedule_name: str) -> None:
        """Delete schedule file from disk."""
        schedule_file = self.config_dir / f"{schedule_name}.json"
        if schedule_file.exists():
            schedule_file.unlink()
    
    def add_schedule(self, schedule: ScheduleConfig) -> None:
        """
        Add a new schedule.
        
        Args:
            schedule: Schedule configuration
            
        Raises:
            ValueError: If schedule with same name exists
        """
        if schedule.name in self._schedules:
            raise ValueError(f"Schedule already exists: {schedule.name}")
        
        self._schedules[schedule.name] = schedule
        self._save_schedule(schedule)
        logger.info(f"Added schedule: {schedule.name}")
    
    def get_schedule(self, name: str) -> Optional[ScheduleConfig]:
        """
        Get schedule by name.
        
        Args:
            name: Schedule name
            
        Returns:
            Schedule configuration or None
        """
        return self._schedules.get(name)
    
    def update_schedule(self, schedule: ScheduleConfig) -> None:
        """
        Update existing schedule.
        
        Args:
            schedule: Updated schedule configuration
            
        Raises:
            ValueError: If schedule doesn't exist
        """
        if schedule.name not in self._schedules:
            raise ValueError(f"Schedule not found: {schedule.name}")
        
        self._schedules[schedule.name] = schedule
        self._save_schedule(schedule)
        logger.info(f"Updated schedule: {schedule.name}")
    
    def delete_schedule(self, name: str) -> None:
        """
        Delete schedule.
        
        Args:
            name: Schedule name
        """
        if name in self._schedules:
            del self._schedules[name]
            self._delete_schedule_file(name)
            logger.info(f"Deleted schedule: {name}")
    
    def list_schedules(self, enabled_only: bool = False) -> List[ScheduleConfig]:
        """
        List all schedules.
        
        Args:
            enabled_only: Only return enabled schedules
            
        Returns:
            List of schedule configurations
        """
        schedules = list(self._schedules.values())
        
        if enabled_only:
            schedules = [s for s in schedules if s.enabled]
        
        return schedules
    
    def get_due_schedules(
        self,
        current_time: Optional[datetime] = None
    ) -> List[ScheduleConfig]:
        """
        Get schedules that are due to run.
        
        Args:
            current_time: Time to check (default: now)
            
        Returns:
            List of due schedules
        """
        if current_time is None:
            current_time = datetime.now()
        
        due_schedules = []
        
        for schedule in self.list_schedules(enabled_only=True):
            if schedule.is_due(current_time):
                due_schedules.append(schedule)
        
        return due_schedules
    
    def record_execution_start(self, schedule_name: str) -> str:
        """
        Record start of schedule execution.
        
        Args:
            schedule_name: Name of schedule being executed
            
        Returns:
            Execution ID
        """
        execution = ScheduleExecution(
            schedule_name=schedule_name,
            start_time=datetime.now(),
            status="running"
        )
        
        self._executions[execution.execution_id] = execution
        logger.info(f"Started execution {execution.execution_id} for {schedule_name}")
        
        return execution.execution_id
    
    def record_execution_complete(
        self,
        execution_id: str,
        backup_file: str,
        backup_size: int
    ) -> None:
        """
        Record successful execution completion.
        
        Args:
            execution_id: Execution identifier
            backup_file: Path to backup file
            backup_size: Size of backup in bytes
        """
        if execution_id in self._executions:
            execution = self._executions[execution_id]
            execution.complete(backup_file, backup_size)
            logger.info(f"Completed execution {execution_id}")
    
    def record_execution_fail(
        self,
        execution_id: str,
        error_message: str
    ) -> None:
        """
        Record failed execution.
        
        Args:
            execution_id: Execution identifier
            error_message: Error description
        """
        if execution_id in self._executions:
            execution = self._executions[execution_id]
            execution.fail(error_message)
            logger.error(f"Failed execution {execution_id}: {error_message}")
    
    def get_execution(self, execution_id: str) -> Optional[ScheduleExecution]:
        """
        Get execution record by ID.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            Execution record or None
        """
        return self._executions.get(execution_id)
    
    def get_schedule_history(
        self,
        schedule_name: str,
        limit: Optional[int] = None
    ) -> List[ScheduleExecution]:
        """
        Get execution history for a schedule.
        
        Args:
            schedule_name: Schedule name
            limit: Maximum number of records to return
            
        Returns:
            List of execution records
        """
        history = [
            ex for ex in self._executions.values()
            if ex.schedule_name == schedule_name
        ]
        
        # Sort by start time (newest first)
        history.sort(key=lambda x: x.start_time, reverse=True)
        
        if limit:
            history = history[:limit]
        
        return history
    
    def get_last_execution(
        self,
        schedule_name: str
    ) -> Optional[ScheduleExecution]:
        """
        Get last execution for a schedule.
        
        Args:
            schedule_name: Schedule name
            
        Returns:
            Last execution record or None
        """
        history = self.get_schedule_history(schedule_name, limit=1)
        return history[0] if history else None
