"""
Schedule configuration for backup jobs.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Literal
from croniter import croniter


class CronExpression:
    """Wrapper for cron expression parsing and validation."""
    
    def __init__(self, expression: str):
        """
        Initialize cron expression.
        
        Args:
            expression: Cron expression string (5 fields)
        """
        self.expression = expression
        self._validate()
    
    def _validate(self) -> None:
        """Validate cron expression format."""
        fields = self.expression.split()
        if len(fields) != 5:
            raise ValueError(
                f"Invalid cron expression: {self.expression}. "
                "Expected 5 fields (minute hour day month weekday)"
            )
    
    def is_valid(self) -> bool:
        """Check if cron expression is valid."""
        try:
            croniter(self.expression)
            return True
        except Exception as e:
            raise ValueError(f"Invalid cron expression: {self.expression}") from e
    
    def get_next_run(self, base_time: Optional[datetime] = None) -> datetime:
        """
        Get next run time from cron expression.
        
        Args:
            base_time: Base time to calculate from (default: now)
            
        Returns:
            Next scheduled run time
        """
        if base_time is None:
            base_time = datetime.now()
        
        cron = croniter(self.expression, base_time)
        return cron.get_next(datetime)
    
    def get_description(self) -> str:
        """Get human-readable description of cron schedule."""
        try:
            from cron_descriptor import get_description
            return get_description(self.expression)
        except ImportError:
            # Fallback if cron_descriptor not available
            return self.expression


@dataclass
class ScheduleConfig:
    """
    Configuration for a scheduled backup job.
    """
    
    name: str
    cron_expression: str
    database_id: str
    enabled: bool = True
    retention_days: int = 7
    compression: Optional[Literal["gzip", "bzip2"]] = None
    storage_type: Optional[str] = None
    storage_location: Optional[str] = None
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.name:
            raise ValueError("Schedule name cannot be empty")
        
        if self.retention_days < 1:
            raise ValueError("Retention days must be positive")
        
        if self.compression and self.compression not in ["gzip", "bzip2"]:
            raise ValueError(f"Invalid compression type: {self.compression}")
        
        # Validate cron expression
        cron = CronExpression(self.cron_expression)
        cron.is_valid()
    
    def get_next_run(self, base_time: Optional[datetime] = None) -> datetime:
        """
        Get next scheduled run time.
        
        Args:
            base_time: Base time to calculate from (default: now)
            
        Returns:
            Next scheduled run time
        """
        cron = CronExpression(self.cron_expression)
        return cron.get_next_run(base_time)
    
    def is_due(self, current_time: Optional[datetime] = None) -> bool:
        """
        Check if schedule is due to run at current time.
        
        Args:
            current_time: Time to check (default: now)
            
        Returns:
            True if schedule should run now
        """
        if current_time is None:
            current_time = datetime.now()
        
        # Normalize to minute precision (remove seconds/microseconds)
        check_time = current_time.replace(second=0, microsecond=0)
        
        # Get the previous run time to check if we're in the scheduled minute
        cron = croniter(self.cron_expression, check_time - timedelta(minutes=1))
        prev_run = cron.get_next(datetime)
        
        # If previous run matches current minute, it's due
        return prev_run == check_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert schedule to dictionary."""
        return {
            "name": self.name,
            "cron_expression": self.cron_expression,
            "database_id": self.database_id,
            "enabled": self.enabled,
            "retention_days": self.retention_days,
            "compression": self.compression,
            "storage_type": self.storage_type,
            "storage_location": self.storage_location,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduleConfig":
        """Create schedule from dictionary."""
        return cls(**data)
    
    @classmethod
    def create_hourly(
        cls,
        name: str,
        database_id: str,
        minute: int = 0,
        **kwargs
    ) -> "ScheduleConfig":
        """
        Create hourly schedule preset.
        
        Args:
            name: Schedule name
            database_id: Database identifier
            minute: Minute to run (0-59)
            **kwargs: Additional schedule options
        """
        return cls(
            name=name,
            cron_expression=f"{minute} * * * *",
            database_id=database_id,
            **kwargs
        )
    
    @classmethod
    def create_daily(
        cls,
        name: str,
        database_id: str,
        hour: int = 2,
        minute: int = 0,
        **kwargs
    ) -> "ScheduleConfig":
        """
        Create daily schedule preset.
        
        Args:
            name: Schedule name
            database_id: Database identifier
            hour: Hour to run (0-23)
            minute: Minute to run (0-59)
            **kwargs: Additional schedule options
        """
        return cls(
            name=name,
            cron_expression=f"{minute} {hour} * * *",
            database_id=database_id,
            **kwargs
        )
    
    @classmethod
    def create_weekly(
        cls,
        name: str,
        database_id: str,
        day_of_week: int = 0,
        hour: int = 3,
        minute: int = 0,
        **kwargs
    ) -> "ScheduleConfig":
        """
        Create weekly schedule preset.
        
        Args:
            name: Schedule name
            database_id: Database identifier
            day_of_week: Day of week (0=Sunday, 6=Saturday)
            hour: Hour to run (0-23)
            minute: Minute to run (0-59)
            **kwargs: Additional schedule options
        """
        return cls(
            name=name,
            cron_expression=f"{minute} {hour} * * {day_of_week}",
            database_id=database_id,
            **kwargs
        )
    
    @classmethod
    def create_monthly(
        cls,
        name: str,
        database_id: str,
        day_of_month: int = 1,
        hour: int = 4,
        minute: int = 0,
        **kwargs
    ) -> "ScheduleConfig":
        """
        Create monthly schedule preset.
        
        Args:
            name: Schedule name
            database_id: Database identifier
            day_of_month: Day of month (1-31)
            hour: Hour to run (0-23)
            minute: Minute to run (0-59)
            **kwargs: Additional schedule options
        """
        return cls(
            name=name,
            cron_expression=f"{minute} {hour} {day_of_month} * *",
            database_id=database_id,
            **kwargs
        )
