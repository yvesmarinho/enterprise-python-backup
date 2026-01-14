"""
VYA BackupDB - CLI interface using Typer.

Provides command-line interface for backup, restore, and configuration operations.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from vya_backupbd import __version__
from vya_backupbd.config.loader import VyaBackupConfig, DatabaseConfig as DBEntry, load_config
from vya_backupbd.config.models import DatabaseConfig, StorageConfig, BackupConfig
from vya_backupbd.backup.context import BackupContext
from vya_backupbd.backup.executor import BackupExecutor
from vya_backupbd.restore.context import RestoreContext
from vya_backupbd.restore.executor import RestoreExecutor
from vya_backupbd.db.engine import get_connection_string
from vya_backupbd.db.mysql import MySQLAdapter
from vya_backupbd.db.postgresql import PostgreSQLAdapter
from vya_backupbd.db.files import FilesAdapter
from vya_backupbd.utils.logging_config import setup_logging
from vya_backupbd.utils.log_sanitizer import safe_repr
from vya_backupbd.utils.email_sender import EmailSender, EmailConfig as EmailCfg

# Initialize Typer app and Rich console
app = typer.Typer(
    name="vya-backupdb",
    help="VYA BackupDB - Enterprise Database Backup & Restore System",
    add_completion=False
)
console = Console()
logger = logging.getLogger(__name__)


def load_vya_config(config_path: Optional[str] = None) -> tuple[VyaBackupConfig, str]:
    """Load configuration from vya_backupbd.json and setup logging.
    
    Returns:
        Tuple of (config, log_file_path)
    """
    logger.debug(f"=== Função: load_vya_config ===")
    logger.debug(f"==> PARAM: config_path TYPE: {type(config_path)}, CONTENT: {config_path}")
    
    try:
        if config_path:
            config = VyaBackupConfig.from_file(Path(config_path))
        else:
            config = load_config(None)
        
        # Setup logging based on configuration
        log_file = setup_logging(
            console_level=config.log_settings.console_loglevel,
            file_level=config.log_settings.file_loglevel,
            log_dir=config.log_settings.log_dir
        )
        
        logger.debug(f"=== Término Função: load_vya_config ===")
        return config, log_file
    except FileNotFoundError:
        console.print("[red]Error:[/red] Configuration file not found")
        console.print("Searched in: ./vya_backupbd.json, project root, /etc/vya_backupdb/")
        logger.debug(f"=== Término Função: load_vya_config COM ERRO ===")
        raise typer.Exit(code=3)
    except Exception as e:
        console.print(f"[red]Error loading config:[/red] {e}")
        logger.debug(f"=== Término Função: load_vya_config COM ERRO ===")
        raise typer.Exit(code=3)
        raise typer.Exit(code=3)


def get_database_entry(config: VyaBackupConfig, instance_id: str) -> DBEntry:
    """Get database entry by ID."""
    logger.debug(f"=== Função: get_database_entry ===")
    logger.debug(f"==> PARAM: config TYPE: {type(config)}, CONTENT: {safe_repr(config)}")
    logger.debug(f"==> PARAM: instance_id TYPE: {type(instance_id)}, CONTENT: {instance_id}")
    
    db_entry = config.get_database_by_id(int(instance_id))
    if not db_entry:
        console.print(f"[red]Error:[/red] Instance '{instance_id}' not found")
        raise typer.Exit(code=3)
    
    if not db_entry.enabled:
        console.print(f"[yellow]Warning:[/yellow] Instance '{instance_id}' is disabled")
        logger.debug(f"=== Término Função: get_database_entry COM ERRO ===")
        raise typer.Exit(code=3)
    
    logger.debug(f"=== Término Função: get_database_entry ===")
    return db_entry


@app.command()
def version():
    """Show version information."""
    console.print(f"[bold]VYA BackupDB[/bold] version [cyan]{__version__}[/cyan]")
    console.print("Enterprise Database Backup & Restore System")


@app.command()
def backup(
    instance: Optional[str] = typer.Option(None, "--instance", "-i", help="Database instance ID"),
    database: Optional[str] = typer.Option(None, "--database", "-d", help="Specific database name"),
    all_instances: bool = typer.Option(False, "--all", "-a", help="Backup all enabled instances"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Test mode (no actual backup)"),
    compression: bool = typer.Option(False, "--compression", "-c", help="Enable ZIP compression"),
    config_path: Optional[str] = typer.Option(None, "--config", help="Path to config file"),
):
    """
    Execute database backup.
    
    Examples:
        vya-backupdb backup --instance 1
        vya-backupdb backup --instance 1 --database mydb
        vya-backupdb backup --all
        vya-backupdb backup --instance 1 --compression
        vya-backupdb backup --instance 1 --dry-run
    """
    logger.debug(f"=== Função: backup (CLI Command) ===")
    logger.debug(f"==> PARAM: instance TYPE: {type(instance)}, CONTENT: {instance}")
    logger.debug(f"==> PARAM: database TYPE: {type(database)}, CONTENT: {database}")
    logger.debug(f"==> PARAM: all_instances TYPE: {type(all_instances)}, CONTENT: {all_instances}")
    logger.debug(f"==> PARAM: dry_run TYPE: {type(dry_run)}, CONTENT: {dry_run}")
    logger.debug(f"==> PARAM: compression TYPE: {type(compression)}, CONTENT: {compression}")
    logger.debug(f"==> PARAM: config_path TYPE: {type(config_path)}, CONTENT: {config_path}")
    
    console.print("[bold blue]VYA BackupDB - Backup Operation[/bold blue]\n")
    
    # Start execution timer
    start_time = time.time()
    
    # Load configuration
    config, log_file = load_vya_config(config_path)
    console.print(f"Log: {log_file}\n")
    
    # Ensure backup directories exist
    Path(config.bkp_system.path_sql).mkdir(parents=True, exist_ok=True)
    Path(config.bkp_system.path_zip).mkdir(parents=True, exist_ok=True)
    Path(config.bkp_system.path_files).mkdir(parents=True, exist_ok=True)
    logger.debug(f"Backup directories ensured: sql={config.bkp_system.path_sql}, zip={config.bkp_system.path_zip}, files={config.bkp_system.path_files}")
    
    logger.info("=" * 80)
    logger.info("Starting backup operation")
    logger.info(f"Dry-run: {dry_run}, Compression: {compression}")
    
    # Determine which instances to backup
    if all_instances:
        instances = config.get_enabled_databases()
        logger.info(f"Backing up all instances: {len(instances)} found")
        if not instances:
            console.print("[yellow]No enabled instances found[/yellow]")
            logger.warning("No enabled instances found")
            raise typer.Exit(code=0)
    elif instance:
        instances = [get_database_entry(config, instance)]
        logger.info(f"Backing up instance: {instance}")
    else:
        console.print("[red]Error:[/red] Must specify --instance or --all")
        raise typer.Exit(code=1)
    
    # Execute backups
    success_count = 0
    fail_count = 0
    successful_databases = []
    failed_databases = {}
    backup_info = {'total_size_mb': 0.0, 'success_count': 0}
    current_instance = ""
    
    for db_entry in instances:
        console.print(f"\n[bold]Instance {db_entry.id_dbms}:[/bold] {db_entry.dbms}://{db_entry.host}:{db_entry.port}")
        logger.info(f"Processing instance {db_entry.id_dbms}: {db_entry.dbms}://{db_entry.host}:{db_entry.port}")
        current_instance = f"{db_entry.dbms}://{db_entry.host}:{db_entry.port}"
        
        if dry_run:
            console.print("[yellow]DRY-RUN MODE - No actual backup will be performed[/yellow]")
        
        # Determine databases to backup
        if database:
            # Backup single database
            databases_to_backup = [database]
        else:
            # Backup all databases (excluding db_ignore)
            try:
                if db_entry.dbms == "files":
                    # For files, use db_list patterns directly
                    databases_to_backup = db_entry.db_list if db_entry.db_list else []
                    console.print(f"[cyan]Found {len(databases_to_backup)} file patterns to backup[/cyan]")
                    logger.info(f"Found {len(databases_to_backup)} patterns: {', '.join(databases_to_backup)}")
                else:
                    # For MySQL/PostgreSQL: list databases via connection
                    list_db = "information_schema" if db_entry.dbms == "mysql" else "postgres"
                    temp_config = DatabaseConfig(
                        type=db_entry.dbms,
                        host=db_entry.host,
                        port=int(db_entry.port),
                        username=db_entry.user,
                        password=db_entry.secret,
                        database=list_db
                    )
                    from vya_backupbd.backup.strategy import get_database_adapter
                    temp_adapter = get_database_adapter(temp_config)
                    all_databases = temp_adapter.get_databases()
                    databases_to_backup = [db for db in all_databases if db not in db_entry.db_ignore]
                    console.print(f"[cyan]Found {len(databases_to_backup)} databases to backup[/cyan]")
                    logger.info(f"Found {len(databases_to_backup)} databases: {', '.join(databases_to_backup)}")
            except Exception as e:
                console.print(f"[red]Error listing databases:[/red] {e}")
                logger.error(f"Error listing databases for instance {db_entry.id_dbms}: {e}")
                fail_count += 1
                continue
        
        # Backup each database
        for db_name in databases_to_backup:
            try:
                console.print(f"\n[cyan]→ Backing up database:[/cyan] {db_name}")
                
                # Create database config
                db_config = DatabaseConfig(
                    type=db_entry.dbms,
                    host=db_entry.host,
                    port=int(db_entry.port),
                    username=db_entry.user,
                    password=db_entry.secret,
                    database=db_name
                )
                
                # Create storage config from config settings
                # Always use path_sql for SQL dumps (will be moved to path_zip if compressed)
                storage_config = StorageConfig(
                    type="local",
                    path=config.bkp_system.path_sql
                )
                
                # Create backup config with retention from config file
                backup_config = BackupConfig(
                    compression="zip" if compression else None,
                    retention_days=config.bkp_system.retention_files
                )
                
                # Create backup context
                context = BackupContext(
                    database_config=db_config,
                    storage_config=storage_config,
                    backup_config=backup_config
                )
                
                if dry_run:
                    console.print("[green]✓[/green] Configuration validated successfully")
                    console.print(f"  Database: {db_config.type}")
                    console.print(f"  Host: {db_config.host}:{db_config.port}")
                    console.print(f"  Storage: {storage_config.path}")
                    success_count += 1
                    continue
                
                # Execute backup
                executor = BackupExecutor(
                    strategy_name="full",
                    cleanup_temp=False  # Don't cleanup - files are in final location
                )
                
                result = executor.execute(context)
                
                if result:
                    console.print(f"  [green]✓[/green] {db_name}: {context.backup_size / (1024 * 1024):.2f} MB")
                    logger.info(f"Backup successful: {db_name} ({context.backup_size / (1024 * 1024):.2f} MB) - {context.storage_location}")
                    success_count += 1
                    successful_databases.append(db_name)
                    backup_info['total_size_mb'] += context.backup_size / (1024 * 1024)
                    backup_info['success_count'] += 1
                else:
                    console.print(f"  [red]✗[/red] {db_name}: Backup failed")
                    console.print(f"    Error: {context.error_message}")
                    logger.error(f"Backup failed: {db_name} - {context.error_message}")
                    fail_count += 1
                    failed_databases[db_name] = context.error_message
                    
            except Exception as e:
                console.print(f"  [red]✗[/red] {db_name}: {str(e)}")
                logger.error(f"Backup exception: {db_name} - {str(e)}", exc_info=True)
                fail_count += 1
                failed_databases[db_name] = str(e)
                continue
    
    # Summary
    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  Success: {success_count}")
    console.print(f"  Failed: {fail_count}")
    logger.info("=" * 80)
    logger.info(f"Backup operation completed - Success: {success_count}, Failed: {fail_count}")
    logger.info("=" * 80)
    
    # Send email notifications if configured
    if config.email_settings.enabled:
        try:
            logger.info("Preparing email notification")
            logger.debug(f"Email config from file: enabled={config.email_settings.enabled}, test_mode={config.email_settings.test_mode}, smtp_user='{config.email_settings.smtp_user}'")
            email_cfg = EmailCfg(
                enabled=config.email_settings.enabled,
                smtp_host=config.email_settings.smtp_host,
                smtp_port=config.email_settings.smtp_port,
                smtp_user=config.email_settings.smtp_user,
                smtp_password=config.email_settings.smtp_password,
                use_ssl=config.email_settings.use_ssl,
                use_tls=config.email_settings.use_tls,
                from_email=config.email_settings.from_email,
                success_recipients=config.email_settings.success_recipients,
                failure_recipients=config.email_settings.failure_recipients,
                test_mode=config.email_settings.test_mode
            )
            logger.debug(f"EmailCfg created: test_mode={email_cfg.test_mode}, smtp_user='{email_cfg.smtp_user}'")
            
            email_sender = EmailSender(email_cfg)
            
            if fail_count > 0:
                # Calculate execution time
                execution_time = time.time() - start_time
                execution_time_str = f"{int(execution_time // 60)}m {int(execution_time % 60)}s"
                
                # Prepare additional info
                additional_info = {
                    'total_attempted': success_count + fail_count,
                    'log_file': log_file,
                    'execution_time': execution_time_str
                }
                
                logger.info("Sending failure notification email")
                email_sender.send_failure_notification(
                    instance=current_instance,
                    failed_databases=list(failed_databases.keys()),
                    errors=failed_databases,
                    log_file=log_file,
                    additional_info=additional_info
                )
                console.print("[yellow]Failure notification email sent[/yellow]")
            elif success_count > 0:
                logger.info("Sending success notification email")
                email_sender.send_success_notification(
                    instance=current_instance,
                    databases=successful_databases,
                    backup_info=backup_info
                )
                console.print("[green]Success notification email sent[/green]")
                
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            console.print(f"[yellow]Warning: Could not send email notification: {e}[/yellow]")
    
    logger.debug(f"=== Término Função: backup (CLI Command) ===")
    
    if fail_count > 0:
        raise typer.Exit(code=1 if success_count > 0 else 2)


@app.command("restore-list")
def restore_list(
    instance: str = typer.Option(..., "--instance", "-i", help="Database instance ID"),
    database: Optional[str] = typer.Option(None, "--database", "-d", help="Filter by database name"),
    limit: int = typer.Option(10, "--limit", "-l", help="Number of backups to show"),
    config_path: Optional[str] = typer.Option(None, "--config", help="Path to config file"),
):
    """
    List available backup files.
    
    Examples:
        vya-backupdb restore-list --instance 1
        vya-backupdb restore-list --instance 1 --database mydb
        vya-backupdb restore-list --instance 1 --limit 20
    """
    from vya_backupbd.utils.backup_manager import BackupManager
    
    console.print("[bold blue]VYA BackupDB - Available Backups[/bold blue]\n")
    
    # Load configuration
    config, _ = load_vya_config(config_path)
    db_entry = get_database_entry(config, instance)
    
    # Get backup directory and ensure it exists
    backup_dir = Path(config.bkp_system.path_zip)
    backup_dir.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Backup directory ensured: {backup_dir}")
    
    # Use BackupManager to list backups
    manager = BackupManager(str(backup_dir))
    backups = manager.list_backups(
        database=database,
        dbms_type=db_entry.dbms.lower() if db_entry.dbms else None,
        limit=limit
    )
    
    if not backups:
        console.print("[yellow]No backups found[/yellow]")
        raise typer.Exit(code=0)
    
    # Display table
    table = Table(title=f"Backups for Instance {instance} ({db_entry.dbms})")
    table.add_column("Database", style="cyan")
    table.add_column("File", style="white")
    table.add_column("Size", justify="right", style="green")
    table.add_column("Type", justify="center", style="yellow")
    table.add_column("Date", style="blue")
    
    for backup in backups:
        table.add_row(
            backup.database,
            backup.filename,
            manager.format_size(backup.size_bytes),
            backup.extension.upper(),
            backup.date.strftime("%Y-%m-%d %H:%M:%S")
        )
    
    console.print(table)
    console.print(f"\n[dim]Total: {len(backups)} backup(s)[/dim]")


@app.command()
def restore(
    file: str = typer.Option(..., "--file", "-f", help="Backup file path"),
    instance_id: int = typer.Option(..., "--instance", "-i", help="Instance ID from config (id_dbms)"),
    target_database: Optional[str] = typer.Option(None, "--target", "-t", help="Target database name (extracted from filename if not provided)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Test mode (no actual restore)"),
    force: bool = typer.Option(False, "--force", help="Force restore without confirmation"),
    config_path: Optional[str] = typer.Option(None, "--config", help="Path to config file"),
):
    """
    Restore database from backup file.
    
    Examples:
        vya-backupdb restore --file /tmp/bkpzip/dns_db_20260113_155440.sql.zip --instance 1
        vya-backupdb restore -f backup.sql.gz -i 2 --target mydb_restored
        vya-backupdb restore -f backup.sql.gz -i 1 --dry-run
        vya-backupdb restore -f backup.sql.gz -i 1 --force
    """
    console.print("[bold blue]VYA BackupDB - Restore Operation[/bold blue]\n")
    
    # Validate file exists
    backup_path = Path(file)
    if not backup_path.exists():
        console.print(f"[red]Error:[/red] Backup file not found: {file}")
        raise typer.Exit(code=1)
    
    # Extract database name from filename if not provided
    if not target_database:
        # Expected format: YYYYMMDD_HHMMSS_dbms_database.zip or dbname_YYYYMMDD_HHMMSS.sql[.gz]
        filename = backup_path.stem  # Remove last extension
        if filename.endswith('.sql'):
            filename = filename[:-4]  # Remove .sql from .sql.gz
        parts = filename.split('_')
        
        # Try new format first: YYYYMMDD_HHMMSS_dbms_database
        if len(parts) >= 4 and parts[0].isdigit() and parts[1].isdigit():
            # New format: skip date, time, dbms - rest is database name
            target_database = '_'.join(parts[3:])
        # Try old format: database_YYYYMMDD_HHMMSS
        elif len(parts) >= 3:
            # Join all parts except last 2 (date and time)
            target_database = '_'.join(parts[:-2])
        else:
            console.print(f"[red]Error:[/red] Cannot extract database name from filename: {backup_path.name}")
            console.print("Please specify database name with --target option")
            raise typer.Exit(code=1)
    
    console.print(f"Backup file: {backup_path}")
    console.print(f"File size: {backup_path.stat().st_size / (1024 * 1024):.2f} MB")
    console.print(f"Target database: [cyan]{target_database}[/cyan]")
    console.print(f"Instance ID: {instance_id}")
    
    if dry_run:
        console.print("\n[yellow]DRY-RUN MODE - No actual restore will be performed[/yellow]")
        console.print("[green]✓[/green] Backup file validated successfully")
        console.print(f"[green]✓[/green] Would restore to database: {target_database}")
        raise typer.Exit(code=0)
    
    # Load configuration
    config, _ = load_vya_config(config_path)
    
    # Find the instance
    instance = None
    for db in config.db_config:
        if db.id_dbms == instance_id:
            instance = db
            break
    
    if not instance:
        console.print(f"[red]Error:[/red] Instance with id_dbms={instance_id} not found in config")
        raise typer.Exit(code=1)
    
    console.print(f"DBMS: {instance.dbms.upper()}")
    console.print(f"Host: {instance.host}:{instance.port}")
    
    # Confirm restore unless --force
    if not force:
        console.print(f"\n[yellow]⚠ Warning:[/yellow] This will restore database '[cyan]{target_database}[/cyan]'")
        console.print("This operation may overwrite existing data!")
        confirm = typer.confirm("Do you want to continue?")
        if not confirm:
            console.print("[yellow]Restore cancelled by user[/yellow]")
            raise typer.Exit(code=0)
    
    # Create database adapter
    try:
        if instance.dbms.lower() == "mysql":
            from vya_backupbd.db.mysql import MySQLAdapter
            from vya_backupbd.config.models import DatabaseConfig
            
            db_config = DatabaseConfig(
                type="mysql",
                host=instance.host,
                port=int(instance.port),
                username=instance.user,
                password=instance.secret
            )
            adapter = MySQLAdapter(db_config)
        elif instance.dbms.lower() == "postgresql":
            from vya_backupbd.db.postgresql import PostgreSQLAdapter
            from vya_backupbd.config.models import DatabaseConfig
            
            db_config = DatabaseConfig(
                type="postgresql",
                host=instance.host,
                port=int(instance.port),
                username=instance.user,
                password=instance.secret
            )
            adapter = PostgreSQLAdapter(db_config)
        else:
            console.print(f"[red]Error:[/red] Unsupported DBMS: {instance.dbms}")
            raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]Error creating database adapter:[/red] {e}")
        raise typer.Exit(code=1)
    
    # Execute restore
    console.print("\n[bold]Starting restore...[/bold]")
    try:
        success = adapter.restore_database(target_database, str(backup_path))
        
        if success:
            console.print(f"\n[green]✓ Success:[/green] Database '{target_database}' restored successfully")
            console.print(f"Source file: {backup_path}")
        else:
            console.print(f"\n[red]✗ Failed:[/red] Could not restore database '{target_database}'")
            console.print("Check logs for details")
            raise typer.Exit(code=1)
            
    except Exception as e:
        console.print(f"\n[red]✗ Error during restore:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("config-validate")
def config_validate(
    config_path: Optional[str] = typer.Option(None, "--config", help="Path to config file"),
):
    """
    Validate configuration file.
    
    Examples:
        vya-backupdb config-validate
        vya-backupdb config-validate --config /path/to/config.json
    """
    console.print("[bold blue]VYA BackupDB - Configuration Validation[/bold blue]\n")
    
    try:
        config, _ = load_vya_config(config_path)
        
        console.print("[green]✓ Configuration file loaded successfully[/green]")
        
        # Show enabled instances
        enabled = config.get_enabled_databases()
        console.print(f"\n[bold]Enabled Instances:[/bold] {len(enabled)}")
        
        for db_entry in enabled:
            console.print(f"  [{db_entry.id_dbms}] {db_entry.dbms}://{db_entry.host}:{db_entry.port}")
        
        console.print("\n[green]✓ Configuration is valid[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ Configuration validation failed:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("config-show")
def config_show(
    no_secrets: bool = typer.Option(True, "--no-secrets", help="Hide sensitive information"),
    format: str = typer.Option("table", "--format", help="Output format: table, json"),
    config_path: Optional[str] = typer.Option(None, "--config", help="Path to config file"),
):
    """
    Show configuration details.
    
    Examples:
        vya-backupdb config-show
        vya-backupdb config-show --format json
        vya-backupdb config-show --no-secrets=false
    """
    console.print("[bold blue]VYA BackupDB - Configuration[/bold blue]\n")
    
    config, _ = load_vya_config(config_path)
    databases = config.get_enabled_databases()
    
    if format == "json":
        data = []
        for db in databases:
            entry = {
                "id": db.id_dbms,
                "type": db.dbms,
                "host": db.host,
                "port": db.port,
                "user": db.user,
                "enabled": db.enabled
            }
            if not no_secrets:
                entry["password"] = db.secret
            data.append(entry)
        
        console.print_json(data=data)
    else:
        table = Table(title="Database Instances")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Host", style="green")
        table.add_column("Port", justify="right")
        table.add_column("User")
        if not no_secrets:
            table.add_column("Password", style="red")
        
        for db in databases:
            row = [
                str(db.id_dbms),
                db.dbms,
                db.host,
                str(db.port),
                db.user
            ]
            if not no_secrets:
                row.append(db.secret)
            table.add_row(*row)
        
        console.print(table)


@app.command("test-connection")
def test_connection(
    instance: str = typer.Option(..., "--instance", "-i", help="Database instance ID"),
    config_path: Optional[str] = typer.Option(None, "--config", help="Path to config file"),
):
    """
    Test database connection.
    
    Examples:
        vya-backupdb test-connection --instance 1
    """
    console.print("[bold blue]VYA BackupDB - Connection Test[/bold blue]\n")
    
    config, _ = load_vya_config(config_path)
    db_entry = get_database_entry(config, instance)
    
    console.print(f"Testing connection to:")
    console.print(f"  Type: {db_entry.dbms}")
    console.print(f"  Host: {db_entry.host}:{db_entry.port}")
    console.print(f"  User: {db_entry.user}\n")
    
    try:
        # Create database config for connection testing
        test_config = DatabaseConfig(
            type=db_entry.dbms,
            host=db_entry.host,
            port=int(db_entry.port),
            username=db_entry.user,
            password=db_entry.secret,
            database="information_schema" if db_entry.dbms == "mysql" else "postgres"
        )
        
        # Test connection using adapter
        if db_entry.dbms == "mysql":
            adapter = MySQLAdapter(test_config)
        elif db_entry.dbms == "postgresql":
            adapter = PostgreSQLAdapter(test_config)
        else:
            console.print(f"[red]Unsupported database type:[/red] {db_entry.dbms}")
            raise typer.Exit(code=1)
        
        databases = adapter.get_databases()
        
        console.print("[green]✓ Connection successful![/green]")
        console.print(f"\nAvailable databases: {len(databases)}")
        for db_name in databases[:10]:  # Show first 10
            console.print(f"  - {db_name}")
        
        if len(databases) > 10:
            console.print(f"  ... and {len(databases) - 10} more")
        
    except Exception as e:
        console.print(f"[red]✗ Connection failed:[/red] {e}")
        raise typer.Exit(code=1)


def main():
    """Main CLI entry point."""
    app()


if __name__ == "__main__":
    main()
