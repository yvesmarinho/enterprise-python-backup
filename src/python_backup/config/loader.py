"""
Configuration loader for vya_backupbd.json

Supports vault integration for secure credential management:
- Primary source: VaultManager (encrypted vault.json.enc)
- Fallback: JSON configuration file
- Logging indicates credential source (vault vs JSON)
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

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
    db_ignore: list[str]  # Databases to exclude
    database: list[str]  # Databases to include (empty = all) - renamed from db_list
    enabled: bool

    @classmethod
    def from_dict(cls, data: dict) -> 'DatabaseConfig':
        """Create DatabaseConfig from dictionary."""
        logger.debug("=== Função: from_dict (DatabaseConfig) ===")
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
        logger.debug("=== Término Função: from_dict (DatabaseConfig) ===")


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
    days_of_week: list[int]
    time: str
    timezone: str


@dataclass
class PrometheusConfig:
    """Prometheus monitoring configuration."""
    enabled: bool
    url: str | None = None
    job_name: str | None = None
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
    success_recipients: list[str] = None
    failure_recipients: list[str] = None
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
    service_settings: dict
    schedule_settings: ScheduleConfig
    prometheus_settings: PrometheusConfig
    email_settings: EmailSettings
    db_config: list[DatabaseConfig]
    bkp_system: BackupSystemConfig
    production: EnvironmentConfig | None = None
    develop: EnvironmentConfig | None = None
    _vault_manager: object | None = None  # Private: VaultManager instance

    @classmethod
    def from_file(cls, config_path: Path, vault_path: Path | None = None) -> 'VyaBackupConfig':
        """Load configuration from JSON file."""
        logger.debug("=== Função: from_file (VyaBackupConfig) ===")
        logger.debug(f"==> PARAM: config_path TYPE: {type(config_path)}, SIZE: {len(str(config_path))} chars, CONTENT: {config_path}")
        logger.debug(f"==> PARAM: vault_path TYPE: {type(vault_path)}, CONTENT: {vault_path}")

        # Initialize VaultManager if vault_path provided
        vault_manager = None
        if vault_path:
            try:
                from python_backup.security.vault import VaultManager
                vault_manager = VaultManager(vault_path)
                if vault_manager.load():
                    logger.info(f"VaultManager loaded successfully from {vault_path}")
                else:
                    logger.warning(f"VaultManager failed to load from {vault_path}, will use JSON fallback")
                    vault_manager = None
            except Exception as e:
                logger.warning(f"Failed to initialize VaultManager: {e}, will use JSON fallback")
                vault_manager = None

        with open(config_path, encoding='utf-8') as f:
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
            logger.debug("Loading email_settings from JSON")
            email_data = data['email_settings']
            logger.debug(f"Email data from JSON: enabled={email_data.get('enabled')}, test_mode={email_data.get('test_mode')}, smtp_user={email_data.get('smtp_user')}")

            smtp_port = email_data.get('smtp_port')
            if isinstance(smtp_port, str):
                smtp_port = int(smtp_port)

            # Try vault first for SMTP credentials
            smtp_user = email_data.get('smtp_user')
            smtp_password = email_data.get('smtp_password')

            if vault_manager and smtp_user:
                # Try to get SMTP credentials from vault
                vault_cred = vault_manager.get('smtp')
                if vault_cred:
                    smtp_user = vault_cred['username']
                    smtp_password = vault_cred['password']
                    logger.info("✓ SMTP credentials loaded from Vault")
                else:
                    logger.warning("⚠ SMTP credentials not found in Vault, using JSON fallback")

            email_settings = EmailSettings(
                enabled=email_data.get('enabled'),
                smtp_host=email_data.get('smtp_host'),
                smtp_port=smtp_port,
                smtp_user=smtp_user,
                smtp_password=smtp_password,
                use_ssl=email_data.get('use_ssl'),
                use_tls=email_data.get('use_tls'),
                from_email=email_data.get('from_email'),
                success_recipients=email_data.get('success_recipients'),
                failure_recipients=email_data.get('failure_recipients'),
                test_mode=email_data.get('test_mode')
            )
            logger.debug(f"Email settings loaded: enabled={email_settings.enabled}, smtp_host={email_settings.smtp_host}, smtp_port={email_settings.smtp_port}, use_ssl={email_settings.use_ssl}, test_mode={email_settings.test_mode}")
        else:
            logger.debug("No email_settings in JSON, using defaults")

        # Parse database configurations with Vault integration
        db_configs = []
        for db_data in data['db_config']:
            # Try vault first for database credentials
            db_id = db_data.get('id_dbms')
            vault_key = f"db_{db_id}"  # e.g., "db_1", "db_2"

            user = db_data.get('user')
            secret = db_data.get('secret')

            if vault_manager and db_id:
                vault_cred = vault_manager.get(vault_key)
                if vault_cred:
                    user = vault_cred['username']
                    secret = vault_cred['password']
                    logger.info(f"✓ Credentials for database ID {db_id} loaded from Vault")
                else:
                    logger.warning(f"⚠ Credentials for database ID {db_id} not found in Vault (key: {vault_key}), using JSON fallback")

            # Update db_data with credentials (vault or JSON fallback)
            db_data['user'] = user
            db_data['secret'] = secret

            db_configs.append(DatabaseConfig.from_dict(db_data))

        config = cls(
            log_settings=LogConfig(**data['log_settings']),
            service_settings=data['service_settings'],
            schedule_settings=ScheduleConfig(**data['schedule_settings']),
            prometheus_settings=PrometheusConfig(**data['prometheus_settings']),
            email_settings=email_settings,
            db_config=db_configs,
            bkp_system=BackupSystemConfig(**data['bkp_system']),
            production=production,
            develop=develop
        )

        # Store vault_manager reference in config
        config._vault_manager = vault_manager

        logger.debug("=== Término Função: from_file (VyaBackupConfig) ===")
        return config

    def get_enabled_databases(self, sort: bool = True) -> list[DatabaseConfig]:
        """
        Get list of enabled database configurations.

        Args:
            sort: If True, sort databases alphabetically by host then by dbms (default: True)

        Returns:
            List of enabled DatabaseConfig objects, optionally sorted
        """
        logger.debug("=== Função: get_enabled_databases ===")
        logger.debug(f"==> PARAM: sort TYPE: {type(sort)}, CONTENT: {sort}")

        result = [db for db in self.db_config if db.enabled]

        if sort:
            # Sort alphabetically by host (case-insensitive), then by dbms type
            result = sorted(result, key=lambda db: (db.host.lower(), db.dbms.lower()))
            logger.debug(f"==> RESULT: {len(result)} enabled databases (sorted)")
        else:
            logger.debug(f"==> RESULT: {len(result)} enabled databases (unsorted)")

        logger.debug("=== Término Função: get_enabled_databases ===")
        return result

    def get_database_by_id(self, id_dbms: int) -> DatabaseConfig | None:
        """Get database configuration by ID."""
        logger.debug("=== Função: get_database_by_id ===")
        logger.debug(f"==> PARAM: id_dbms TYPE: {type(id_dbms)}, CONTENT: {id_dbms}")

        for db in self.db_config:
            if db.id_dbms == id_dbms:
                logger.debug("=== Término Função: get_database_by_id ===")
                return db
        logger.debug("=== Término Função: get_database_by_id (NOT FOUND) ===")
        return None

    def get_active_environment(self) -> EnvironmentConfig | None:
        """Get currently active environment configuration."""
        logger.debug("=== Função: get_active_environment ===")

        if self.production and self.production.enable:
            logger.debug("=== Término Função: get_active_environment (PRODUCTION) ===")
            return self.production
        if self.develop and self.develop.enable:
            logger.debug("=== Término Função: get_active_environment (DEVELOP) ===")
            return self.develop
        logger.debug("=== Término Função: get_active_environment (NONE) ===")
        return None


def load_config(config_path: Path | None = None, vault_path: Path | None = None) -> VyaBackupConfig:
    """
    Load VYA Backup configuration from JSON file with Vault integration.

    Args:
        config_path: Path to vya_backupbd.json. If None, searches in:
                     1. Current directory
                     2. Project root
                     3. /etc/vya_backupdb/
        vault_path: Path to vault.json.enc. If None, defaults to .secrets/vault.json.enc

    Returns:
        VyaBackupConfig instance

    Raises:
        FileNotFoundError: If configuration file not found
    """
    logger.debug("=== Função: load_config ===")
    logger.debug(f"==> PARAM: config_path TYPE: {type(config_path)}, CONTENT: {config_path}")
    logger.debug(f"==> PARAM: vault_path TYPE: {type(vault_path)}, CONTENT: {vault_path}")

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
            logger.debug("=== Término Função: load_config COM ERRO ===")
            raise FileNotFoundError(
                "Configuration file vya_backupbd.json not found in standard locations"
            )

    # Default vault path if not specified
    if vault_path is None:
        vault_path = Path(".secrets/vault.json.enc")
        logger.debug(f"Using default vault path: {vault_path}")

    result = VyaBackupConfig.from_file(config_path, vault_path)
    logger.debug("=== Término Função: load_config ===")
    return result
