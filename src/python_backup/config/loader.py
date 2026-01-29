"""
Configuration loader for vya_backupbd.json
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from python_backup.utils.log_sanitizer import safe_repr

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database connection configuration."""
    id_dbms: int
    dbms: str  # 'mysql' or 'postgresql'
    host: str
    port: int
    user: str
    secret: str  # password
    db_ignore: List[str]  # Databases to exclude
    database: List[str]  # Databases to include (empty = all) - renamed from db_list
    enabled: bool
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DatabaseConfig':
        """Create DatabaseConfig from dictionary."""
        logger.debug(f"=== Função: from_dict (DatabaseConfig) ===")
        logger.debug(f"==> PARAM: data TYPE: {type(data)}, CONTENT: {safe_repr(data)}")
        
        # Parse db_ignore (support both string and list)
        db_ignore = []
        if 'db_ignore' in data and data['db_ignore']:
            if isinstance(data['db_ignore'], list):
                db_ignore = data['db_ignore']
            elif isinstance(data['db_ignore'], str):
                db_ignore = [db.strip() for db in data['db_ignore'].split(',')]
        
        # Parse database/db_list (backward compatibility)
        # Priority: 'database' > 'db_list'
        database = []
        if 'database' in data:
            if isinstance(data['database'], list):
                database = data['database']
            elif isinstance(data['database'], str) and data['database']:
                database = [db.strip() for db in data['database'].split(',')]
        elif 'db_list' in data:
            # Backward compatibility with old field name
            if isinstance(data['db_list'], list):
                database = data['db_list']
            elif isinstance(data['db_list'], str) and data['db_list']:
                database = [db.strip() for db in data['db_list'].split(',')]
        
        # Validate dbms type
        valid_dbms = ['mysql', 'postgresql', 'files']
        if data['dbms'] not in valid_dbms:
            raise ValueError(f"Invalid dbms type: {data['dbms']}. Must be one of {valid_dbms}")
        
        return cls(
            id_dbms=data['id_dbms'],
            dbms=data['dbms'],
            host=data['host'],
            port=int(data['port']),
            user=data['user'],
            secret=data['secret'],
            db_ignore=db_ignore,
            database=database,
            enabled=data.get('enabled', True)
        )
        logger.debug(f"=== Término Função: from_dict (DatabaseConfig) ===")


@dataclass
class BackupSystemConfig:
    """Backup system paths configuration."""
    path_sql: str
    path_zip: str
    path_files: str = "/tmp/bkp_files/"
    retention_files: int = 7


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
    log_dir: str = "/var/log/enterprise"


@dataclass
class EmailSettings:
    """Email notification settings."""
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    use_ssl: bool = False
    use_tls: bool = False
    from_email: str = ""
    success_recipients: List[str] = None
    failure_recipients: List[str] = None
    test_mode: bool = False
    
    def __post_init__(self):
        if self.success_recipients is None:
            self.success_recipients = []
        if self.failure_recipients is None:
            self.failure_recipients = []


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
    service_settings: Dict
    schedule_settings: ScheduleConfig
    prometheus_settings: PrometheusConfig
    email_settings: EmailSettings
    db_config: List[DatabaseConfig]
    bkp_system: BackupSystemConfig
    production: Optional[EnvironmentConfig] = None
    develop: Optional[EnvironmentConfig] = None
    
    @classmethod
    def from_file(cls, config_path: Path) -> 'VyaBackupConfig':
        """Load configuration from JSON file."""
        logger.debug(f"=== Função: from_file (VyaBackupConfig) ===")
        logger.debug(f"==> PARAM: config_path TYPE: {type(config_path)}, SIZE: {len(str(config_path))} chars, CONTENT: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Parse optional environment configs
        production = None
        develop = None
        if 'production' in data:
            production = EnvironmentConfig(**data['production'])
        if 'develop' in data:
            develop = EnvironmentConfig(**data['develop'])
        
        # Parse email settings with defaults
        email_settings = EmailSettings()
        if 'email_settings' in data:
            logger.debug(f"Loading email_settings from JSON")
            email_data = data['email_settings']
            logger.debug(f"Email data from JSON: enabled={email_data.get('enabled')}, test_mode={email_data.get('test_mode')}, smtp_user={email_data.get('smtp_user')}")
            
            smtp_port = email_data.get('smtp_port')
            if isinstance(smtp_port, str):
                smtp_port = int(smtp_port)
            
            email_settings = EmailSettings(
                enabled=email_data.get('enabled'),
                smtp_host=email_data.get('smtp_host'),
                smtp_port=smtp_port,
                smtp_user=email_data.get('smtp_user'),
                smtp_password=email_data.get('smtp_password'),
                use_ssl=email_data.get('use_ssl'),
                use_tls=email_data.get('use_tls'),
                from_email=email_data.get('from_email'),
                success_recipients=email_data.get('success_recipients'),
                failure_recipients=email_data.get('failure_recipients'),
                test_mode=email_data.get('test_mode')
            )
            logger.debug(f"Email settings loaded: enabled={email_settings.enabled}, smtp_host={email_settings.smtp_host}, smtp_port={email_settings.smtp_port}, use_ssl={email_settings.use_ssl}, test_mode={email_settings.test_mode}")
        else:
            logger.debug(f"No email_settings in JSON, using defaults")
        
        return cls(
            log_settings=LogConfig(**data['log_settings']),
            service_settings=data['service_settings'],
            schedule_settings=ScheduleConfig(**data['schedule_settings']),
            prometheus_settings=PrometheusConfig(**data['prometheus_settings']),
            email_settings=email_settings,
            db_config=[DatabaseConfig.from_dict(db) for db in data['db_config']],
            bkp_system=BackupSystemConfig(**data['bkp_system']),
            production=production,
            develop=develop
        )
        logger.debug(f"=== Término Função: from_file (VyaBackupConfig) ===")
    
    def get_enabled_databases(self, sort: bool = True) -> List[DatabaseConfig]:
        """
        Get list of enabled database configurations.
        
        Args:
            sort: If True, sort databases alphabetically by host then by dbms (default: True)
        
        Returns:
            List of enabled DatabaseConfig objects, optionally sorted
        """
        logger.debug(f"=== Função: get_enabled_databases ===")
        logger.debug(f"==> PARAM: sort TYPE: {type(sort)}, CONTENT: {sort}")
        
        result = [db for db in self.db_config if db.enabled]
        
        if sort:
            # Sort alphabetically by host (case-insensitive), then by dbms type
            result = sorted(result, key=lambda db: (db.host.lower(), db.dbms.lower()))
            logger.debug(f"==> RESULT: {len(result)} enabled databases (sorted)")
        else:
            logger.debug(f"==> RESULT: {len(result)} enabled databases (unsorted)")
        
        logger.debug(f"=== Término Função: get_enabled_databases ===")
        return result
    
    def get_database_by_id(self, id_dbms: int) -> Optional[DatabaseConfig]:
        """Get database configuration by ID."""
        logger.debug(f"=== Função: get_database_by_id ===")
        logger.debug(f"==> PARAM: id_dbms TYPE: {type(id_dbms)}, CONTENT: {id_dbms}")
        
        for db in self.db_config:
            if db.id_dbms == id_dbms:
                logger.debug(f"=== Término Função: get_database_by_id ===")
                return db
        logger.debug(f"=== Término Função: get_database_by_id (NOT FOUND) ===")
        return None
    
    def get_active_environment(self) -> Optional[EnvironmentConfig]:
        """Get currently active environment configuration."""
        logger.debug(f"=== Função: get_active_environment ===")
        
        if self.production and self.production.enable:
            logger.debug(f"=== Término Função: get_active_environment (PRODUCTION) ===")
            return self.production
        if self.develop and self.develop.enable:
            logger.debug(f"=== Término Função: get_active_environment (DEVELOP) ===")
            return self.develop
        logger.debug(f"=== Término Função: get_active_environment (NONE) ===")
        return None


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
    logger.debug(f"=== Função: load_config ===")
    logger.debug(f"==> PARAM: config_path TYPE: {type(config_path)}, CONTENT: {config_path}")
    
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
            logger.debug(f"=== Término Função: load_config COM ERRO ===")
            raise FileNotFoundError(
                "Configuration file vya_backupbd.json not found in standard locations"
            )
    
    result = VyaBackupConfig.from_file(config_path)
    logger.debug(f"=== Término Função: load_config ===")
    return result
