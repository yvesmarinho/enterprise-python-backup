"""Configuration models using Pydantic v2"""

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseModel):
    """Database instance configuration"""

    id: Optional[str] = Field(None, description="Unique database ID")
    type: Literal["mysql", "postgresql", "files"] = Field(..., description="Database type")
    host: str = Field(..., description="Database hostname")
    port: int = Field(ge=0, le=65535, description="Database port (0 for files)")
    username: Optional[str] = Field(None, description="Database username")
    password: Optional[str] = Field(None, description="Database password")
    database: Optional[str] = Field(None, description="Default database for connection")
    databases: list[str] = Field(
        default_factory=list, description="Databases to include in backup (empty = all)"
    )
    db_ignore: list[str] = Field(
        default_factory=list, description="Databases to exclude from backup"
    )
    credential_name: Optional[str] = Field(None, description="Credential name for encrypted credentials")
    enabled: bool = Field(default=True, description="Enable backup for this DB")
    ssl_enabled: bool = Field(default=False, description="Enable SSL/TLS")
    ssl_ca_cert: Optional[Path] = Field(None, description="SSL CA certificate path")

    @model_validator(mode="after")
    def add_system_databases(self) -> "DatabaseConfig":
        """Add default system databases to db_ignore if not present"""
        defaults = {
            "mysql": ["information_schema", "performance_schema", "mysql", "sys"],
            "postgresql": ["postgres", "template0", "template1"],
        }
        system_dbs = defaults.get(self.type, [])
        self.db_ignore = list(set(self.db_ignore + system_dbs))
        return self


class StorageConfig(BaseModel):
    """Storage configuration"""

    type: Literal["local", "s3"] = Field(default="local", description="Storage type")
    path: Optional[str] = Field(None, description="Local storage path")
    bucket: Optional[str] = Field(None, description="S3 bucket name")
    region: Optional[str] = Field(None, description="S3 region")
    access_key: Optional[str] = Field(None, description="S3 access key")
    secret_key: Optional[str] = Field(None, description="S3 secret key")
    prefix: Optional[str] = Field(None, description="S3 key prefix")
    
    base_path: Path = Field(
        default=Path("/var/backups/vya_backupdb"), description="Base path for backups"
    )
    structure: str = Field(
        default="{hostname}/{db_id}/{db_name}/{date}",
        description="Directory structure pattern",
    )
    compression_level: int = Field(
        ge=1, le=9, default=6, description="Gzip compression level (1-9)"
    )
    checksum_algorithm: Literal["md5", "sha256"] = Field(
        default="sha256", description="Checksum algorithm"
    )


class BackupConfig(BaseModel):
    """Backup operation configuration"""
    
    retention_days: int = Field(ge=1, default=7, description="Days to retain backups")
    compression: Optional[Literal["zip", "gzip", "bzip2"]] = Field(None, description="Compression method")


class RetentionConfig(BaseModel):
    """Retention policy configuration"""

    strategy: Literal["simple", "gfs"] = Field(default="gfs", description="Retention strategy")
    daily_keep: int = Field(ge=1, default=7, description="Keep last N daily backups")
    weekly_keep: int = Field(ge=1, default=4, description="Keep last N weekly backups")
    monthly_keep: int = Field(ge=1, default=12, description="Keep last N monthly backups")
    cleanup_enabled: bool = Field(default=True, description="Enable automatic cleanup")


class LoggingConfig(BaseModel):
    """Logging configuration"""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    format: Literal["json", "text"] = Field(default="json")
    output: Literal["console", "file", "both"] = Field(default="file")
    file_path: Path = Field(default=Path("/var/log/vya_backupdb/app.log"))


class EmailConfig(BaseModel):
    """Email notification configuration"""
    
    enabled: bool = Field(default=False, description="Enable email notifications")
    smtp_host: str = Field(default="smtp.gmail.com", description="SMTP server hostname")
    smtp_port: int = Field(ge=1, le=65535, default=587, description="SMTP server port")
    smtp_user: str = Field(default="", description="SMTP username")
    smtp_password: str = Field(default="", description="SMTP password")
    use_tls: bool = Field(default=True, description="Use TLS encryption")
    from_email: str = Field(default="backup@vya.digital", description="From email address")
    success_recipients: list[str] = Field(
        default_factory=lambda: ["atendimento@vya.digital"],
        description="Recipients for success notifications"
    )
    failure_recipients: list[str] = Field(
        default_factory=lambda: ["suporte@vya.digital"],
        description="Recipients for failure notifications"
    )
    test_mode: bool = Field(default=False, description="Add [TESTE] prefix to subject")


class AppConfig(BaseSettings):
    """Main application configuration"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="VYA_",
        case_sensitive=False,
    )

    application_name: str = Field(default="vya-backupdb")
    version: str = Field(default="2.0.0")
    environment: Literal["dev", "staging", "production"] = Field(default="production")

    databases: list[DatabaseConfig] = Field(..., description="Database instances")
    storage: StorageConfig = Field(default_factory=StorageConfig)
    retention: RetentionConfig = Field(default_factory=RetentionConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "AppConfig":
        """Load configuration from YAML file"""
        import yaml

        with open(yaml_path, "r") as f:
            config_dict = yaml.safe_load(f)
        return cls(**config_dict)
