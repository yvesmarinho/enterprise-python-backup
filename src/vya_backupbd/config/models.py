"""Configuration models using Pydantic v2"""

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseModel):
    """Database instance configuration"""

    id: str = Field(..., description="Unique database ID")
    type: Literal["mysql", "postgresql"] = Field(..., description="Database type")
    host: str = Field(..., description="Database hostname")
    port: int = Field(ge=1, le=65535, description="Database port")
    enabled: bool = Field(default=True, description="Enable backup for this DB")
    exclude_databases: list[str] = Field(
        default_factory=list, description="Databases to exclude from backup"
    )
    ssl_enabled: bool = Field(default=False, description="Enable SSL/TLS")
    ssl_ca_cert: Optional[Path] = Field(None, description="SSL CA certificate path")

    @model_validator(mode="after")
    def add_system_databases(self) -> "DatabaseConfig":
        """Add default system databases if not present"""
        defaults = {
            "mysql": ["information_schema", "performance_schema", "mysql", "sys"],
            "postgresql": ["postgres", "template0", "template1"],
        }
        system_dbs = defaults.get(self.type, [])
        self.exclude_databases = list(set(self.exclude_databases + system_dbs))
        return self


class StorageConfig(BaseModel):
    """Storage configuration"""

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

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "AppConfig":
        """Load configuration from YAML file"""
        import yaml

        with open(yaml_path, "r") as f:
            config_dict = yaml.safe_load(f)
        return cls(**config_dict)
