"""N8N CLI Commands.

User-facing CLI for N8N backup and restore operations.
Integrates with parent project's enterprise-backup CLI.
"""

import sys
from pathlib import Path
from typing import Optional

import click
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError

from .backup import N8NBackup
from .restore import N8NRestore
from .models import BackupType, OperationStatus
from .storage import LocalRepository
from .exceptions import (
    BackupError,
    RestoreError,
    ValidationError,
    DockerError,
    N8NError,
)
from . import setup_logging


# Exit codes for different error types
EXIT_SUCCESS = 0
EXIT_VALIDATION_ERROR = 1
EXIT_DOCKER_ERROR = 2
EXIT_N8N_ERROR = 3
EXIT_NETWORK_ERROR = 4
EXIT_INTEGRITY_ERROR = 5


class N8NConfig(BaseModel):
    """N8N backup/restore configuration."""

    container_name: str = Field(default="n8n", description="N8N Docker container name")
    backup_path: Path = Field(
        default=Path("/tmp/bkpfile/n8n"), description="Local backup storage path"
    )
    retention_days: int = Field(default=7, description="Backup retention in days")
    retention_count: Optional[int] = Field(
        default=10, description="Maximum number of backups to retain"
    )
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format (json or text)")
    docker_host: Optional[str] = Field(
        default=None, description="Docker daemon socket (default: unix:///var/run/docker.sock)"
    )


def load_config() -> N8NConfig:
    """Load configuration from environment variables.

    Returns:
        N8NConfig instance

    Raises:
        SystemExit: Configuration validation failed
    """
    import os

    try:
        config = N8NConfig(
            container_name=os.getenv("N8N_CONTAINER_NAME", "n8n"),
            backup_path=Path(os.getenv("BACKUP_PATH", "/tmp/bkpfile/n8n")),
            retention_days=int(os.getenv("RETENTION_DAYS", "7")),
            retention_count=int(os.getenv("RETENTION_COUNT", "10"))
            if os.getenv("RETENTION_COUNT")
            else None,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_format=os.getenv("LOG_FORMAT", "json"),
            docker_host=os.getenv("DOCKER_HOST"),
        )
        return config

    except PydanticValidationError as e:
        click.echo(f"Configuration validation error: {e}", err=True)
        sys.exit(EXIT_VALIDATION_ERROR)
    except Exception as e:
        click.echo(f"Failed to load configuration: {e}", err=True)
        sys.exit(EXIT_VALIDATION_ERROR)


@click.group(name="n8n")
@click.pass_context
def n8n_cli(ctx: click.Context) -> None:
    """N8N backup and restore operations.

    Enterprise-grade backup solution for N8N workflows and credentials.
    Preserves IDs, validates integrity, and supports selective operations.

    Examples:
        # Full backup
        enterprise-backup n8n backup

        # Credentials only
        enterprise-backup n8n backup --credentials-only

        # List backups
        enterprise-backup n8n list

        # Restore from backup
        enterprise-backup n8n restore <backup-id>

        # Validate backup integrity
        enterprise-backup n8n validate <backup-id>
    """
    # Load configuration and store in context
    config = load_config()
    ctx.ensure_object(dict)
    ctx.obj["config"] = config

    # Setup logging
    setup_logging(
        log_level=config.log_level,
        log_format=config.log_format,
    )


@n8n_cli.command(name="backup")
@click.option(
    "--credentials-only",
    is_flag=True,
    default=False,
    help="Backup only credentials (excludes workflows)",
)
@click.option(
    "--workflows-only",
    is_flag=True,
    default=False,
    help="Backup only workflows (excludes credentials)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Simulate backup without modifying data",
)
@click.option(
    "--skip-validation",
    is_flag=True,
    default=False,
    help="Skip JSON integrity validation (NOT RECOMMENDED)",
)
@click.pass_context
def backup_command(
    ctx: click.Context,
    credentials_only: bool,
    workflows_only: bool,
    dry_run: bool,
    skip_validation: bool,
) -> None:
    """Execute N8N backup operation.

    Creates a timestamped backup of N8N credentials and/or workflows.
    Preserves original IDs and validates integrity.

    Constitution Compliance:
        - Principle II: Uses --backup flag to preserve IDs
        - Principle III: Validates JSON integrity and checksums
        - Principle IV: Structured logging with audit trail

    Exit Codes:
        0: Success
        1: Validation error
        2: Docker error
        3: N8N error
        5: Integrity error
    """
    config: N8NConfig = ctx.obj["config"]

    # Determine backup type
    if credentials_only and workflows_only:
        click.echo("Error: Cannot specify both --credentials-only and --workflows-only", err=True)
        sys.exit(EXIT_VALIDATION_ERROR)

    if credentials_only:
        backup_type = BackupType.CREDENTIALS
    elif workflows_only:
        backup_type = BackupType.WORKFLOWS
    else:
        backup_type = BackupType.FULL

    if dry_run:
        click.echo(f"[DRY RUN] Would execute backup with type: {backup_type.value}")
        click.echo(f"[DRY RUN] Container: {config.container_name}")
        click.echo(f"[DRY RUN] Backup path: {config.backup_path}")
        click.echo(f"[DRY RUN] Validation: {'disabled' if skip_validation else 'enabled'}")
        sys.exit(EXIT_SUCCESS)

    try:
        # Initialize backup manager
        repository = LocalRepository(
            base_path=config.backup_path,
            retention_days=config.retention_days,
            retention_count=config.retention_count,
        )

        backup_manager = N8NBackup(
            container_name=config.container_name,
            backup_repository=repository,
        )

        # Execute backup
        click.echo(f"Starting {backup_type.value} backup...")
        operation = backup_manager.backup(
            backup_type=backup_type,
            validate_integrity=not skip_validation,
        )

        if operation.status == OperationStatus.COMPLETED:
            click.echo(f"✓ Backup completed successfully")
            click.echo(f"  Backup ID: {operation.id}")
            click.echo(f"  Files: {', '.join(operation.files)}")
            click.echo(f"  Duration: {operation.duration_seconds:.2f}s")
            click.echo(f"  Checksum: {operation.checksum_sha256[:16]}...")
            sys.exit(EXIT_SUCCESS)
        else:
            click.echo(f"✗ Backup failed with status: {operation.status}", err=True)
            if operation.error_message:
                click.echo(f"  Error: {operation.error_message}", err=True)
            sys.exit(EXIT_N8N_ERROR)

    except ValidationError as e:
        click.echo(f"✗ Validation error: {e}", err=True)
        sys.exit(EXIT_VALIDATION_ERROR)

    except DockerError as e:
        click.echo(f"✗ Docker error: {e}", err=True)
        sys.exit(EXIT_DOCKER_ERROR)

    except (BackupError, N8NError) as e:
        click.echo(f"✗ Backup error: {e}", err=True)
        sys.exit(EXIT_N8N_ERROR)

    except Exception as e:
        click.echo(f"✗ Unexpected error: {e}", err=True)
        sys.exit(EXIT_N8N_ERROR)


@n8n_cli.command(name="restore")
@click.argument("backup_id", type=str)
@click.option(
    "--credentials-only",
    is_flag=True,
    default=False,
    help="Restore only credentials (excludes workflows)",
)
@click.option(
    "--workflows-only",
    is_flag=True,
    default=False,
    help="Restore only workflows (excludes credentials)",
)
@click.option(
    "--skip-safety-backup",
    is_flag=True,
    default=False,
    help="Skip safety backup creation (NOT RECOMMENDED)",
)
@click.option(
    "--skip-validation",
    is_flag=True,
    default=False,
    help="Skip pre/post validation (NOT RECOMMENDED)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Simulate restore without modifying data",
)
@click.pass_context
def restore_command(
    ctx: click.Context,
    backup_id: str,
    credentials_only: bool,
    workflows_only: bool,
    skip_safety_backup: bool,
    skip_validation: bool,
    dry_run: bool,
) -> None:
    """Execute N8N restore operation.

    Restores credentials and/or workflows from a specific backup.
    Creates safety backup before changes and validates integrity.

    Constitution Compliance:
        - Principle II: Preserves original IDs from backup
        - Principle III: Safety backup + integrity validation
        - Principle IV: Structured logging with audit trail

    Exit Codes:
        0: Success
        1: Validation error
        2: Docker error
        3: N8N error
        5: Integrity error
    """
    config: N8NConfig = ctx.obj["config"]

    # Determine restore type
    if credentials_only and workflows_only:
        click.echo("Error: Cannot specify both --credentials-only and --workflows-only", err=True)
        sys.exit(EXIT_VALIDATION_ERROR)

    if credentials_only:
        restore_type = BackupType.CREDENTIALS
    elif workflows_only:
        restore_type = BackupType.WORKFLOWS
    else:
        restore_type = BackupType.FULL

    if dry_run:
        click.echo(f"[DRY RUN] Would execute restore with type: {restore_type.value}")
        click.echo(f"[DRY RUN] Backup ID: {backup_id}")
        click.echo(f"[DRY RUN] Container: {config.container_name}")
        click.echo(f"[DRY RUN] Safety backup: {'disabled' if skip_safety_backup else 'enabled'}")
        click.echo(f"[DRY RUN] Validation: {'disabled' if skip_validation else 'enabled'}")
        sys.exit(EXIT_SUCCESS)

    try:
        # Initialize restore manager
        repository = LocalRepository(
            base_path=config.backup_path,
            retention_days=config.retention_days,
            retention_count=config.retention_count,
        )

        restore_manager = N8NRestore(
            container_name=config.container_name,
            backup_repository=repository,
        )

        # Execute restore
        click.echo(f"Starting {restore_type.value} restore from backup {backup_id}...")

        if not skip_safety_backup:
            click.echo("⚠ Creating safety backup before restore...")

        operation = restore_manager.restore(
            backup_id=backup_id,
            restore_type=restore_type,
            skip_safety_backup=skip_safety_backup,
            skip_validation=skip_validation,
        )

        if operation.status == OperationStatus.COMPLETED:
            click.echo(f"✓ Restore completed successfully")
            click.echo(f"  Operation ID: {operation.id}")
            click.echo(f"  Files processed: {', '.join(operation.files_processed)}")
            click.echo(f"  Duration: {operation.duration_seconds:.2f}s")
            if operation.pre_restore_backup:
                click.echo(f"  Safety backup: {operation.pre_restore_backup}")
            sys.exit(EXIT_SUCCESS)

        elif operation.status == OperationStatus.ROLLED_BACK:
            click.echo(f"⚠ Restore failed and was rolled back", err=True)
            click.echo(f"  Safety backup restored: {operation.pre_restore_backup}")
            if operation.error_message:
                click.echo(f"  Error: {operation.error_message}", err=True)
            sys.exit(EXIT_N8N_ERROR)

        else:
            click.echo(f"✗ Restore failed with status: {operation.status}", err=True)
            if operation.error_message:
                click.echo(f"  Error: {operation.error_message}", err=True)
            sys.exit(EXIT_N8N_ERROR)

    except ValidationError as e:
        click.echo(f"✗ Validation error: {e}", err=True)
        sys.exit(EXIT_VALIDATION_ERROR)

    except DockerError as e:
        click.echo(f"✗ Docker error: {e}", err=True)
        sys.exit(EXIT_DOCKER_ERROR)

    except (RestoreError, N8NError) as e:
        click.echo(f"✗ Restore error: {e}", err=True)
        sys.exit(EXIT_N8N_ERROR)

    except Exception as e:
        click.echo(f"✗ Unexpected error: {e}", err=True)
        sys.exit(EXIT_N8N_ERROR)


@n8n_cli.command(name="list")
@click.option(
    "--format",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="Output format",
)
@click.pass_context
def list_command(ctx: click.Context, format: str) -> None:
    """List available backups.

    Displays all backups with metadata sorted chronologically (newest first).
    Shows backup ID, timestamp, type, file count, and size.

    Exit Codes:
        0: Success
        1: Validation error
        5: Integrity error
    """
    config: N8NConfig = ctx.obj["config"]

    try:
        repository = LocalRepository(
            base_path=config.backup_path,
            retention_days=config.retention_days,
            retention_count=config.retention_count,
        )

        backups = repository.list_backups()

        if not backups:
            click.echo("No backups found")
            sys.exit(EXIT_SUCCESS)

        if format == "json":
            import json

            backup_list = [
                {
                    "backup_id": str(backup.backup_id),
                    "created_at": backup.created_at.isoformat(),
                    "hostname": backup.hostname,
                    "type": backup.type.value,
                    "file_count": backup.file_count,
                    "size_bytes": backup.total_size_bytes,
                    "checksum": backup.checksum_sha256[:16] + "...",
                    "n8n_version": backup.n8n_version,
                }
                for backup in backups
            ]
            click.echo(json.dumps(backup_list, indent=2))

        else:  # table format
            click.echo("\nAvailable Backups:")
            click.echo("=" * 120)
            click.echo(
                f"{'Backup ID':<38} {'Timestamp':<20} {'Type':<12} {'Files':<6} {'Size':<12} {'N8N Version':<10}"
            )
            click.echo("-" * 120)

            for backup in backups:
                size_mb = backup.total_size_bytes / (1024 * 1024)
                timestamp = backup.created_at.strftime("%Y-%m-%d %H:%M:%S")

                click.echo(
                    f"{str(backup.backup_id):<38} {timestamp:<20} {backup.type.value:<12} "
                    f"{backup.file_count:<6} {size_mb:>8.2f} MB  {backup.n8n_version:<10}"
                )

            click.echo("=" * 120)
            click.echo(f"\nTotal backups: {len(backups)}")

        sys.exit(EXIT_SUCCESS)

    except Exception as e:
        click.echo(f"✗ Failed to list backups: {e}", err=True)
        sys.exit(EXIT_INTEGRITY_ERROR)


@n8n_cli.command(name="validate")
@click.argument("backup_id", type=str)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Show detailed validation results",
)
@click.pass_context
def validate_command(ctx: click.Context, backup_id: str, verbose: bool) -> None:
    """Validate backup integrity.

    Checks backup integrity without restoring:
    - JSON syntax validation
    - Required field validation
    - Checksum verification
    - Metadata consistency

    Exit Codes:
        0: Validation passed
        1: Validation failed
        5: Integrity error
    """
    config: N8NConfig = ctx.obj["config"]

    try:
        repository = LocalRepository(
            base_path=config.backup_path,
            retention_days=config.retention_days,
            retention_count=config.retention_count,
        )

        click.echo(f"Validating backup {backup_id}...")

        # Verify backup exists
        if not repository.verify_backup_integrity(backup_id):
            click.echo(f"✗ Backup integrity check failed", err=True)
            sys.exit(EXIT_INTEGRITY_ERROR)

        # Download and validate
        from .validators import validate_backup_integrity

        backup_path = config.backup_path / backup_id
        result = validate_backup_integrity(backup_path)

        if result.passed:
            click.echo(f"✓ Backup validation passed")

            if verbose:
                click.echo("\nValidation Details:")
                if result.warnings:
                    for warning in result.warnings:
                        click.echo(f"  ⚠ {warning}")
                else:
                    click.echo("  No warnings")

            sys.exit(EXIT_SUCCESS)

        else:
            click.echo(f"✗ Backup validation failed", err=True)

            if verbose or result.errors:
                click.echo("\nValidation Errors:")
                for error in result.errors:
                    click.echo(f"  ✗ {error}", err=True)

            if verbose and result.warnings:
                click.echo("\nValidation Warnings:")
                for warning in result.warnings:
                    click.echo(f"  ⚠ {warning}")

            sys.exit(EXIT_VALIDATION_ERROR)

    except Exception as e:
        click.echo(f"✗ Validation error: {e}", err=True)
        sys.exit(EXIT_INTEGRITY_ERROR)


@n8n_cli.command(name="cleanup")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be deleted without deleting",
)
@click.pass_context
def cleanup_command(ctx: click.Context, dry_run: bool) -> None:
    """Clean up old backups according to retention policy.

    Removes backups older than retention_days and keeps only retention_count recent backups.
    Uses configuration from environment variables (RETENTION_DAYS, RETENTION_COUNT).

    Exit Codes:
        0: Success
        5: Cleanup error
    """
    config: N8NConfig = ctx.obj["config"]

    try:
        repository = LocalRepository(
            base_path=config.backup_path,
            retention_days=config.retention_days,
            retention_count=config.retention_count,
        )

        if dry_run:
            click.echo("[DRY RUN] Would execute cleanup with:")
            click.echo(f"  Retention days: {config.retention_days}")
            click.echo(f"  Retention count: {config.retention_count}")
            click.echo(f"  Backup path: {config.backup_path}")
            sys.exit(EXIT_SUCCESS)

        click.echo("Cleaning up old backups...")
        repository.cleanup_old_backups()
        click.echo("✓ Cleanup completed")

        sys.exit(EXIT_SUCCESS)

    except Exception as e:
        click.echo(f"✗ Cleanup error: {e}", err=True)
        sys.exit(EXIT_INTEGRITY_ERROR)


if __name__ == "__main__":
    n8n_cli()
