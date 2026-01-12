"""
Configuration loader for vya_backupbd.json
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    id_dbms: int
    dbms: str  # 'mysql' or 'postgresql'
    host: str
    port: int
    user: str
    secret: str  # password
    db_ignore: List[str]
    enabled: bool
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DatabaseConfig':
        """Create DatabaseConfig from dictionary."""
        # Parse db_ignore string to list
        db_ignore = []
        if 'db_ignore' in data and data['db_ignore']:
            db_ignore = [db.strip() for db in data['db_ignore'].split(',')]
        
        return cls(
            id_dbms=data['id_dbms'],
            dbms=data['dbms'],
            host=data['host'],
            port=int(data['port']),
            user=data['user'],
            secret=data['secret'],
            db_ignore=db_ignore,
            enabled=data.get('enabled', True)
        )


@dataclass
class BackupSystemConfig:
    """Backup system paths configuration."""
    path_sql: str
    path_zip: str


@dataclass
class ScheduleConfig:
    """Schedule configuration."""
    enabled: bool
    days_of_week: List[int]
    time: str
    timezone: str


@dataclass
class PrometheusConfig:
    """Prometheus monitoring configuration."""
    enabled: bool
    url: Optional[str] = None
    job_name: Optional[str] = None
    timeout: int = 30


@dataclass
class LogConfig:
    """Logging configuration."""
    console_loglevel: str
    file_loglevel: str


@dataclass
class EnvironmentConfig:
    """Environment-specific configuration."""
    enable: bool
    global_function_path: str
    path_log: str


@dataclass
class VyaBackupConfig:
    """Complete VYA Backup configuration."""
    log_settings: LogConfig
    production: EnvironmentConfig
    develop: EnvironmentConfig
    service_settings: Dict
    schedule_settings: ScheduleConfig
    prometheus_settings: PrometheusConfig
    db_config: List[DatabaseConfig]
    bkp_system: BackupSystemConfig
    
    @classmethod
    def from_file(cls, config_path: Path) -> 'VyaBackupConfig':
        """Load configuration from JSON file."""
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return cls(
            log_settings=LogConfig(**data['log_settings']),
            production=EnvironmentConfig(**data['production']),
            develop=EnvironmentConfig(**data['develop']),
            service_settings=data['service_settings'],
            schedule_settings=ScheduleConfig(**data['schedule_settings']),
            prometheus_settings=PrometheusConfig(**data['prometheus_settings']),
            db_config=[DatabaseConfig.from_dict(db) for db in data['db_config']],
            bkp_system=BackupSystemConfig(**data['bkp_system'])
        )
    
    def get_enabled_databases(self) -> List[DatabaseConfig]:
        """Get list of enabled database configurations."""
        return [db for db in self.db_config if db.enabled]
    
    def get_database_by_id(self, id_dbms: int) -> Optional[DatabaseConfig]:
        """Get database configuration by ID."""
        for db in self.db_config:
            if db.id_dbms == id_dbms:
                return db
        return None
    
    def get_active_environment(self) -> EnvironmentConfig:
        """Get currently active environment configuration."""
        if self.production.enable:
            return self.production
        return self.develop


def load_config(config_path: Optional[Path] = None) -> VyaBackupConfig:
    """
    Load VYA Backup configuration from JSON file.
    
    Args:
        config_path: Path to vya_backupbd.json. If None, searches in:
                     1. Current directory
                     2. Project root
                     3. /etc/vya_backupdb/
    
    Returns:
        VyaBackupConfig instance
    
    Raises:
        FileNotFoundError: If configuration file not found
    """
    if config_path is None:
        # Try common locations
        search_paths = [
            Path.cwd() / 'vya_backupbd.json',
            Path(__file__).parent.parent.parent / 'vya_backupbd.json',
            Path('/etc/vya_backupdb/vya_backupbd.json')
        ]
        
        for path in search_paths:
            if path.exists():
                config_path = path
                break
        
        if config_path is None:
            raise FileNotFoundError(
                "Configuration file vya_backupbd.json not found in standard locations"
            )
    
    return VyaBackupConfig.from_file(config_path)
