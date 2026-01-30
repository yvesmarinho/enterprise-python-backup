"""
VYA BackupDB - CLI interface using Typer.

Provides command-line interface for backup, restore, and configuration operations.
"""

import sys
import json
import logging
import time
from pathlib import Path
from typing import Optional, List
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from python_backup import __version__
from python_backup.config.loader import VyaBackupConfig, DatabaseConfig as DBEntry, load_config
from python_backup.config.models import DatabaseConfig, StorageConfig, BackupConfig, AppConfig
from python_backup.backup.context import BackupContext
from python_backup.backup.executor import BackupExecutor
from python_backup.restore.context import RestoreContext
from python_backup.restore.executor import RestoreExecutor
from python_backup.db.engine import get_connection_string
from python_backup.db.mysql import MySQLAdapter
from python_backup.db.postgresql import PostgreSQLAdapter
from python_backup.db.files import FilesAdapter
from python_backup.backup.strategy import get_database_adapter
from python_backup.security.vault import VaultManager
from python_backup.utils.logging_config import setup_logging
from python_backup.utils.log_sanitizer import safe_repr
from python_backup.utils.email_sender import EmailSender, EmailConfig as EmailCfg

# Initialize Typer app and Rich console
app = typer.Typer(
    name="vya-backupdb",
    help="VYA BackupDB - Enterprise Database Backup & Restore System",
    add_completion=False
)
console = Console()
logger = logging.getLogger(__name__)


def load_vya_config(config_path: Optional[str] = None) -> tuple[VyaBackupConfig, str]:
    """Load configuration from config file and setup logging.
    
    Returns:
        Tuple of (config, log_file_path)
    """
    logger.debug(f"=== Função: load_vya_config ===")
    logger.debug(f"==> PARAM: config_path TYPE: {type(config_path)}, CONTENT: {config_path}")
    
    try:
        # Try loading new format first (config.yaml with AppConfig)
        if config_path:
            config_file = Path(config_path)
        else:
            # Search for config.yaml
            search_paths = [
                Path(__file__).parent.parent.parent / 'config' / 'config.yaml',
                Path.cwd() / 'config' / 'config.yaml',
                Path.cwd() / 'config.yaml',
            ]
            config_file = None
            for path in search_paths:
                if path.exists() and path.suffix in ['.yaml', '.yml']:
                    config_file = path
                    break
        
        # If YAML config found, we'll use vault directly - return None to signal this
        if config_file and config_file.exists() and config_file.suffix in ['.yaml', '.yml']:
            logger.info(f"Found YAML config: {config_file}, will use Vault for credentials")
            # Setup basic logging
            log_file = setup_logging(
                console_level='INFO',
                file_level='DEBUG',
                log_dir=Path('logs')
            )
            return None, log_file
        
        # Fall back to old format (vya_backupbd.json)
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
        console.print("Searched in: config/config.yaml, ./config.yaml, project root, /etc/vya_backupdb/")
        logger.debug(f"=== Término Função: load_vya_config COM ERRO ===")
        raise typer.Exit(code=3)
    except Exception as e:
        console.print(f"[red]Error loading config:[/red] {e}")
        logger.debug(f"=== Término Função: load_vya_config COM ERRO ===")
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
    
    try:
        # Load configuration
        config, log_file = load_vya_config(config_path)
        
        # If config is None, we're using new YAML format with vault
        if config is None:
            if not instance:
                console.print("[red]Error:[/red] Must specify --instance when using YAML config")
                raise typer.Exit(code=1)
            
            # Load YAML config
            config_file = Path(__file__).parent.parent.parent / 'config' / 'config.yaml'
            if not config_file.exists():
                console.print(f"[red]Error:[/red] Config file not found: {config_file}")
                raise typer.Exit(code=1)
            
            app_config = AppConfig.from_yaml(config_file)
            
            # Find database config by id
            db_entry = None
            for db in app_config.databases:
                if db.id == instance:
                    db_entry = db
                    break
            
            if not db_entry:
                console.print(f"[red]Error:[/red] Database '{instance}' not found in config")
                raise typer.Exit(code=1)
            
            if not db_entry.enabled:
                console.print(f"[yellow]Warning:[/yellow] Database '{instance}' is disabled")
                raise typer.Exit(code=3)
            
            # Load credentials from vault
            vault_manager = VaultManager(Path(".secrets/vault.json.enc"))
            if not vault_manager.load():
                console.print("[red]Error:[/red] Failed to load vault")
                raise typer.Exit(code=1)
            
            # Get username/password from vault
            credential = vault_manager.get(db_entry.credential_name)
            if not credential:
                console.print(f"[red]Error:[/red] Credential '{db_entry.credential_name}' not found in vault")
                raise typer.Exit(code=1)
            
            # Combine config + credentials
            db_config = DatabaseConfig(
                type=db_entry.type,
                host=db_entry.host,
                port=db_entry.port,
                username=credential['username'],
                password=credential['password'],
                database=database or db_entry.database,
                databases=[db_entry.database] if db_entry.database else [],
                db_ignore=db_entry.db_ignore,
                ssl_enabled=db_entry.ssl_enabled if hasattr(db_entry, 'ssl_enabled') else False,
                ssl_ca_cert=db_entry.ssl_ca_cert if hasattr(db_entry, 'ssl_ca_cert') else None
            )
            
            console.print(f"[cyan]Database ID:[/cyan] {instance}")
            console.print(f"[cyan]Type:[/cyan] {db_config.type}")
            console.print(f"[cyan]Host:[/cyan] {db_config.host}:{db_config.port}")
            console.print(f"[cyan]Database:[/cyan] {database}")
            console.print(f"[cyan]Output:[/cyan] /tmp/bkp_test/")
            
            # Execute backup directly
            from python_backup.backup.strategy import get_database_adapter
            adapter = get_database_adapter(db_config)
            
            output_dir = Path("/tmp/bkp_test")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            db_name = database or "backup"
            output_file = output_dir / f"{db_name}_{timestamp}.sql.gz"
            
            console.print(f"\n[bold]Starting backup...[/bold]")
            success = adapter.backup_database(database or db_name, str(output_file))
            
            if success:
                size = output_file.stat().st_size / 1024 / 1024
                console.print(f"[green]✓ Backup completed:[/green] {output_file} ({size:.2f} MB)")
                logger.info(f"Backup completed successfully in {time.time() - start_time:.2f} seconds")
                raise typer.Exit(code=0)
            else:
                console.print(f"[red]✗ Backup failed[/red]")
                logger.error("Backup operation failed")
                raise typer.Exit(code=1)
    
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        console.print(f"\n[yellow]⚠ Backup interrupted by user after {elapsed:.1f} seconds[/yellow]")
        logger.warning(f"Backup interrupted by user (Ctrl+C) after {elapsed:.2f} seconds")
        logger.info("=" * 80)
        raise typer.Exit(code=130)  # Standard exit code for SIGINT
    
    console.print(f"Log: {log_file}\n")
    
    # Ensure backup directories exist
    Path(config.bkp_system.path_sql).mkdir(parents=True, exist_ok=True)
    Path(config.bkp_system.path_zip).mkdir(parents=True, exist_ok=True)
    Path(config.bkp_system.path_files).mkdir(parents=True, exist_ok=True)
    logger.debug(f"Backup directories ensured: sql={config.bkp_system.path_sql}, zip={config.bkp_system.path_zip}, files={config.bkp_system.path_files}")
    
    logger.info("=" * 80)
    logger.info("Starting backup operation")
    logger.info(f"Dry-run: {dry_run}, Compression: {compression}")
    
    # Validate mutually exclusive options
    if instance and all_instances:
        console.print("[red]Error:[/red] Cannot use --instance and --all together")
        console.print("[yellow]Choose one:[/yellow]")
        console.print("  • vya backup --instance 1  (single instance)")
        console.print("  • vya backup --all         (all instances)")
        logger.error("Mutually exclusive options: --instance and --all used together")
        raise typer.Exit(code=1)
    
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
        logger.error("Missing required option: must specify --instance or --all")
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
            # Backup single database (CLI override)
            databases_to_backup = [database]
        else:
            # Backup databases according to filter rules
            try:
                if db_entry.dbms == "files":
                    # For files, use database patterns directly (backward compat: db_list -> database)
                    databases_to_backup = getattr(db_entry, 'database', []) or getattr(db_entry, 'db_list', []) or []
                    console.print(f"[cyan]Found {len(databases_to_backup)} file patterns to backup[/cyan]")
                    logger.info(f"Found {len(databases_to_backup)} patterns: {', '.join(databases_to_backup)}")
                else:
                    # For MySQL/PostgreSQL: list databases and apply filters
                    list_db = "information_schema" if db_entry.dbms == "mysql" else "postgres"
                    temp_config = DatabaseConfig(
                        type=db_entry.dbms,
                        host=db_entry.host,
                        port=int(db_entry.port),
                        username=db_entry.user,
                        password=db_entry.secret,
                        database=list_db,
                        databases=getattr(db_entry, 'database', []),  # New field
                        db_ignore=db_entry.db_ignore  # Already a list
                    )
                    from python_backup.backup.strategy import get_database_adapter
                    temp_adapter = get_database_adapter(temp_config)
                    all_databases = temp_adapter.get_databases()
                    
                    # Use new filtering method with precedence rules
                    databases_to_backup = temp_adapter.get_filtered_databases(all_databases)
                    
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
    from python_backup.utils.backup_manager import BackupManager
    
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
    instance_id: str = typer.Option(..., "--instance", "-i", help="Instance ID (vault credential ID or numeric id_dbms)"),
    target_database: Optional[str] = typer.Option(None, "--target", "-t", help="Target database name (extracted from filename if not provided)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Test mode (no actual restore)"),
    force: bool = typer.Option(False, "--force", help="Force restore without confirmation"),
    config_path: Optional[str] = typer.Option(None, "--config", help="Path to config file"),
):
    """
    Restore database from backup file.
    
    Examples:
        vya-backupdb restore --file /tmp/bkpzip/dns_db_20260113_155440.sql.zip --instance 1
        vya-backupdb restore -f backup.sql.gz -i home011-postgres --target mydb_restored
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
    
    # Check if using new YAML format (config is None) or instance_id is a string
    if config is None or not instance_id.isdigit():
        # Load YAML config
        config_file = Path(__file__).parent.parent.parent / 'config' / 'config.yaml'
        if not config_file.exists():
            console.print(f"[red]Error:[/red] Config file not found: {config_file}")
            raise typer.Exit(code=1)
        
        app_config = AppConfig.from_yaml(config_file)
        
        # Find database config by id
        db_entry = None
        for db in app_config.databases:
            if db.id == instance_id:
                db_entry = db
                break
        
        if not db_entry:
            console.print(f"[red]Error:[/red] Database '{instance_id}' not found in config")
            raise typer.Exit(code=1)
        
        if not db_entry.enabled:
            console.print(f"[yellow]Warning:[/yellow] Database '{instance_id}' is disabled")
            raise typer.Exit(code=3)
        
        # Load credentials from vault
        from python_backup.security.vault import VaultManager
        vault_manager = VaultManager(Path(".secrets/vault.json.enc"))
        if not vault_manager.load():
            console.print("[red]Error:[/red] Failed to load vault")
            raise typer.Exit(code=1)
        
        # Get username/password from vault
        credential = vault_manager.get(db_entry.credential_name)
        if not credential:
            console.print(f"[red]Error:[/red] Credential '{db_entry.credential_name}' not found in vault")
            raise typer.Exit(code=1)
        
        console.print(f"DBMS: {db_entry.type.upper()}")
        console.print(f"Host: {db_entry.host}:{db_entry.port}")
        
        # Confirm restore unless --force
        if not force:
            console.print(f"\n[yellow]⚠ Warning:[/yellow] This will restore database '[cyan]{target_database}[/cyan]'")
            console.print("This operation may overwrite existing data!")
            confirm = typer.confirm("Do you want to continue?")
            if not confirm:
                console.print("[yellow]Restore cancelled by user[/yellow]")
                raise typer.Exit(code=0)
        
        # Create database config combining YAML + vault
        db_config = DatabaseConfig(
            type=db_entry.type,
            host=db_entry.host,
            port=db_entry.port,
            username=credential['username'],
            password=credential['password'],
            database=target_database
        )
        
        from python_backup.backup.strategy import get_database_adapter
        adapter = get_database_adapter(db_config)
        
        # Execute restore
        console.print(f"\n[bold]Starting restore...[/bold]")
        success = adapter.restore_database(target_database, str(backup_path))
        
        if success:
            console.print(f"[green]✓ Restore completed successfully[/green]")
            raise typer.Exit(code=0)
        else:
            console.print(f"[red]✗ Restore failed[/red]")
            raise typer.Exit(code=1)
    
    # Old path: use legacy config file
    # Find the instance
    instance = None
    for db in config.db_config:
        if db.id_dbms == int(instance_id):
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
            db_config = DatabaseConfig(
                type="mysql",
                host=instance.host,
                port=int(instance.port),
                username=instance.user,
                password=instance.secret
            )
            adapter = MySQLAdapter(db_config)
        elif instance.dbms.lower() == "postgresql":
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
    instance: str = typer.Option(..., "--instance", "-i", help="Database instance ID (string identifier from config.yaml)"),
    config_file: Optional[str] = typer.Option("config/config.yaml", "--config", help="Path to config.yaml file"),
):
    """
    Test database connection using config.yaml + vault.
    
    Examples:
        vya-backupdb test-connection --instance app_workforce-postgres-azure
        vya-backupdb test-connection --instance wfdb02-postgres
    """
    console.print("[bold blue]VYA BackupDB - Connection Test[/bold blue]\n")
    
    try:
        # Load config.yaml
        config_path = Path(config_file)
        if not config_path.exists():
            console.print(f"[red]Error:[/red] Config file not found: {config_file}")
            raise typer.Exit(code=1)
        
        app_config = AppConfig.from_yaml(config_path)
        
        # Find database entry
        db_entry = None
        for db in app_config.databases:
            if db.id == instance:
                db_entry = db
                break
        
        if not db_entry:
            console.print(f"[red]Error:[/red] Instance '{instance}' not found in {config_file}")
            raise typer.Exit(code=3)
        
        # Load credentials from vault
        vault_manager = VaultManager(Path(".secrets/vault.json.enc"))
        if not vault_manager.load():
            console.print("[red]Error:[/red] Failed to load vault")
            raise typer.Exit(code=1)
        
        # Get username/password from vault
        credential = vault_manager.get(db_entry.credential_name)
        if not credential:
            console.print(f"[red]Error:[/red] Credential '{db_entry.credential_name}' not found in vault")
            raise typer.Exit(code=1)
        
        console.print(f"Testing connection to:")
        console.print(f"  ID: {db_entry.id}")
        console.print(f"  Type: {db_entry.type}")
        console.print(f"  Host: {db_entry.host}:{db_entry.port}")
        console.print(f"  User: {credential['username']}")
        console.print(f"  SSL: {getattr(db_entry, 'ssl_enabled', False)}\n")
        
        # Create database config for connection testing
        test_database = db_entry.database if db_entry.database else ("information_schema" if db_entry.type == "mysql" else "postgres")
        
        test_config = DatabaseConfig(
            type=db_entry.type,
            host=db_entry.host,
            port=db_entry.port,
            username=credential['username'],
            password=credential['password'],
            database=test_database,
            ssl_enabled=getattr(db_entry, 'ssl_enabled', False),
            ssl_ca_cert=getattr(db_entry, 'ssl_ca_cert', None)
        )
        
        # Test connection using adapter
        adapter = get_database_adapter(test_config)
        databases = adapter.get_databases()
        
        console.print("[green]✓ Connection successful![/green]")
        console.print(f"\nAvailable databases: {len(databases)}")
        for db_name in databases[:10]:  # Show first 10
            console.print(f"  - {db_name}")
        
        if len(databases) > 10:
            console.print(f"  ... and {len(databases) - 10} more")
        
    except Exception as e:
        console.print(f"[red]✗ Connection failed:[/red] {e}")
        import traceback
        traceback.print_exc()
        raise typer.Exit(code=1)


# ============================================================
# Vault Management Commands
# ============================================================

@app.command("vault-add")
def vault_add(
    credential_id: Optional[str] = typer.Option(None, "--id", help="Credential identifier (e.g., mysql-prod)"),
    username: Optional[str] = typer.Option(None, "--username", "-u", help="Username"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Password"),
    description: str = typer.Option("", "--description", "-d", help="Optional description"),
    from_file: Optional[str] = typer.Option(None, "--from-file", "-f", help="Import credentials from JSON file"),
    vault_path: str = typer.Option(".secrets/vault.json.enc", "--vault", help="Path to vault file"),
):
    """
    Add or update credential in vault.
    
    Examples:
        # Single credential
        vya-backupdb vault-add --id mysql-prod --username root --password MyP@ss123
        vya-backupdb vault-add --id smtp-server --username user@domain.com --password xxx --description "SMTP Server"
        
        # Multiple credentials from JSON file
        vya-backupdb vault-add --from-file credentials.json
    
    JSON file format:
        [
            {
                "id": "mysql-prod",
                "username": "root",
                "password": "MyP@ss123",
                "description": "Production MySQL"
            },
            {
                "id": "postgresql-prod",
                "username": "postgres",
                "password": "SecureP@ss",
                "description": "Production PostgreSQL"
            }
        ]
    """
    from python_backup.security.vault import VaultManager
    
    console.print("[bold blue]VYA BackupDB - Vault Add Credential[/bold blue]\n")
    
    try:
        vault = VaultManager(vault_path)
        vault.load()
        
        # Import from JSON file
        if from_file:
            import_path = Path(from_file)
            if not import_path.exists():
                console.print(f"[red]✗ File not found:[/red] {from_file}")
                raise typer.Exit(code=1)
            
            console.print(f"Importing credentials from '[cyan]{from_file}[/cyan]'...\n")
            
            try:
                with open(import_path, 'r') as f:
                    credentials = json.load(f)
                
                if not isinstance(credentials, list):
                    console.print("[red]✗ JSON file must contain an array of credentials[/red]")
                    raise typer.Exit(code=1)
                
                added_count = 0
                updated_count = 0
                failed_count = 0
                
                for idx, cred in enumerate(credentials, 1):
                    # Validate required fields
                    required_fields = ['id', 'username', 'password']
                    if not all(k in cred for k in required_fields):
                        console.print(f"[yellow]⚠ Skipping entry {idx}: Missing required fields (id, username, password)[/yellow]")
                        failed_count += 1
                        continue
                    
                    cred_id = cred['id']
                    exists = vault.exists(cred_id)
                    action = "Updating" if exists else "Adding"
                    
                    console.print(f"{action} credential '[cyan]{cred_id}[/cyan]'...")
                    
                    # Check if full credential format (has type, host, port)
                    if 'type' in cred and 'host' in cred and 'port' in cred:
                        # Use set_full for complete credential
                        success = vault.set_full(cred_id, cred)
                    else:
                        # Use set for simple username/password
                        cred_user = cred['username']
                        cred_pass = cred['password']
                        cred_desc = cred.get('description', '')
                        success = vault.set(cred_id, cred_user, cred_pass, cred_desc)
                    
                    if success:
                        if exists:
                            updated_count += 1
                        else:
                            added_count += 1
                    else:
                        console.print(f"[red]  ✗ Failed to set credential '{cred_id}'[/red]")
                        failed_count += 1
                
                # Save vault
                if not vault.save():
                    console.print(f"[red]✗ Failed to save vault[/red]")
                    raise typer.Exit(code=1)
                
                # Summary
                console.print(f"\n[bold]Import Summary:[/bold]")
                console.print(f"  [green]Added:[/green] {added_count}")
                console.print(f"  [blue]Updated:[/blue] {updated_count}")
                if failed_count > 0:
                    console.print(f"  [red]Failed:[/red] {failed_count}")
                console.print(f"  Vault: {vault_path}")
                
                if failed_count > 0:
                    raise typer.Exit(code=1)
                
            except json.JSONDecodeError as e:
                console.print(f"[red]✗ Invalid JSON file:[/red] {e}")
                raise typer.Exit(code=1)
        
        # Single credential mode
        else:
            # Validate required parameters for single mode
            if not credential_id or not username or not password:
                console.print("[red]✗ Error:[/red] Either provide --from-file or all of --id, --username, and --password")
                console.print("\nUsage:")
                console.print("  Single: vya-backupdb vault-add --id ID --username USER --password PASS")
                console.print("  Batch:  vya-backupdb vault-add --from-file credentials.json")
                raise typer.Exit(code=1)
            
            exists = vault.exists(credential_id)
            action = "Updating" if exists else "Adding"
            
            console.print(f"{action} credential '[cyan]{credential_id}[/cyan]'...")
            
            success = vault.set(credential_id, username, password, description)
            
            if not success:
                console.print(f"[red]✗ Failed to set credential[/red]")
                raise typer.Exit(code=1)
            
            if not vault.save():
                console.print(f"[red]✗ Failed to save vault[/red]")
                raise typer.Exit(code=1)
            
            action_past = "Updated" if exists else "Added"
            console.print(f"[green]✓ {action_past}:[/green] Credential '{credential_id}'")
            console.print(f"  Username: {username}")
            if description:
                console.print(f"  Description: {description}")
            console.print(f"  Vault: {vault_path}")
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("vault-get")
def vault_get(
    credential_id: str = typer.Option(..., "--id", help="Credential identifier"),
    show_password: bool = typer.Option(False, "--show-password", help="Display password"),
    vault_path: str = typer.Option(".secrets/vault.json.enc", "--vault", help="Path to vault file"),
):
    """
    Retrieve credential from vault.
    
    Examples:
        vya-backupdb vault-get --id mysql-prod
        vya-backupdb vault-get --id mysql-prod --show-password
    """
    from python_backup.security.vault import VaultManager
    
    console.print("[bold blue]VYA BackupDB - Vault Get Credential[/bold blue]\n")
    
    try:
        vault = VaultManager(vault_path)
        
        if not vault.load():
            console.print(f"[red]✗ Failed to load vault[/red]")
            raise typer.Exit(code=1)
        
        # Get credential
        credential = vault.get(credential_id)
        
        if not credential:
            console.print(f"[red]✗ Credential '{credential_id}' not found[/red]")
            raise typer.Exit(code=1)
        
        # Get metadata
        metadata = vault.get_metadata(credential_id)
        
        console.print(f"[green]✓ Found:[/green] Credential '{credential_id}'")
        console.print(f"  Username: [cyan]{credential['username']}[/cyan]")
        
        if show_password:
            console.print(f"  Password: [red]{credential['password']}[/red]")
        else:
            console.print(f"  Password: [dim]{'*' * 12}[/dim] (use --show-password to reveal)")
        
        if metadata:
            if metadata.get('description'):
                console.print(f"  Description: {metadata['description']}")
            if metadata.get('created_at'):
                console.print(f"  Created: {metadata['created_at']}")
            if metadata.get('updated_at'):
                console.print(f"  Updated: {metadata['updated_at']}")
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("vault-list")
def vault_list(
    vault_path: str = typer.Option(".secrets/vault.json.enc", "--vault", help="Path to vault file"),
):
    """
    List all credentials in vault.
    
    Examples:
        vya-backupdb vault-list
    """
    from python_backup.security.vault import VaultManager
    
    console.print("[bold blue]VYA BackupDB - Vault List Credentials[/bold blue]\n")
    
    vault = VaultManager(vault_path)
    
    if not vault.load():
        console.print("[yellow]No credentials in vault[/yellow]")
        console.print(f"\n[dim]Vault: {vault_path}[/dim]")
        console.print("[dim]Use 'vault-add' to create your first credential[/dim]")
        return  # Exit without error
    
    # Get all credentials
    credential_ids = vault.list_credentials()
    
    if not credential_ids:
        console.print("[yellow]No credentials in vault[/yellow]")
        console.print(f"\n[dim]Vault: {vault_path}[/dim]")
        console.print("[dim]Use 'vault-add' to create your first credential[/dim]")
        return  # Exit without error
    
    # Sort credentials by ID
    credential_ids = sorted(credential_ids)
    
    # Display as table
    table = Table(title=f"Vault Credentials ({len(credential_ids)})")
    table.add_column("ID", style="cyan")
    table.add_column("Username", style="green")
    table.add_column("Description")
    table.add_column("Updated", style="dim")
    
    for cred_id in credential_ids:
        credential = vault.get(cred_id)
        metadata = vault.get_metadata(cred_id)
        
        username = credential['username'] if credential else "???"
        description = metadata.get('description', '') if metadata else ''
        updated = metadata.get('updated_at', '')[:19] if metadata else ''  # Trim to datetime
        
        table.add_row(cred_id, username, description, updated)
    
    console.print(table)
    console.print(f"\n[dim]Vault: {vault_path}[/dim]")
    
    # Show vault info
    info = vault.get_vault_info()
    console.print(f"[dim]Size: {info['file_size_bytes'] / 1024:.1f} KB | Version: {info['version']}[/dim]")


@app.command("vault-remove")
def vault_remove(
    credential_id: str = typer.Option(..., "--id", help="Credential identifier"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    vault_path: str = typer.Option(".secrets/vault.json.enc", "--vault", help="Path to vault file"),
):
    """
    Remove credential from vault.
    
    Examples:
        vya-backupdb vault-remove --id mysql-old
        vya-backupdb vault-remove --id mysql-old --force
    """
    from python_backup.security.vault import VaultManager
    
    console.print("[bold blue]VYA BackupDB - Vault Remove Credential[/bold blue]\n")
    
    try:
        vault = VaultManager(vault_path)
        
        if not vault.load():
            console.print(f"[red]✗ Failed to load vault[/red]")
            raise typer.Exit(code=1)
        
        # Check if exists
        if not vault.exists(credential_id):
            console.print(f"[red]✗ Credential '{credential_id}' not found[/red]")
            raise typer.Exit(code=1)
        
        # Confirm removal unless --force
        if not force:
            console.print(f"[yellow]⚠ Warning:[/yellow] Remove credential '[cyan]{credential_id}[/cyan]'?")
            confirm = typer.confirm("Are you sure?")
            if not confirm:
                console.print("[yellow]Cancelled by user[/yellow]")
                raise typer.Exit(code=0)
        
        # Remove credential
        if not vault.remove(credential_id):
            console.print(f"[red]✗ Failed to remove credential[/red]")
            raise typer.Exit(code=1)
        
        # Save vault
        if not vault.save():
            console.print(f"[red]✗ Failed to save vault[/red]")
            raise typer.Exit(code=1)
        
        console.print(f"[green]✓ Removed:[/green] Credential '{credential_id}'")
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("vault-info")
def vault_info(
    vault_path: str = typer.Option(".secrets/vault.json.enc", "--vault", help="Path to vault file"),
):
    """
    Show vault information and statistics.
    
    Examples:
        vya-backupdb vault-info
    """
    from python_backup.security.vault import VaultManager
    
    console.print("[bold blue]VYA BackupDB - Vault Information[/bold blue]\n")
    
    try:
        vault = VaultManager(vault_path)
        
        # Check if vault exists
        vault_file = Path(vault_path)
        if not vault_file.exists():
            console.print(f"[yellow]Vault doesn't exist yet[/yellow]")
            console.print(f"Path: {vault_path}")
            console.print("\nUse 'vault-add' to create your first credential")
            raise typer.Exit(code=0)
        
        if not vault.load():
            console.print(f"[red]✗ Failed to load vault[/red]")
            raise typer.Exit(code=1)
        
        info = vault.get_vault_info()
        
        # Display info
        console.print(f"[bold]Vault:[/bold] {info['path']}")
        console.print(f"[bold]Version:[/bold] {info['version']}")
        console.print(f"[bold]Credentials:[/bold] {info['credentials_count']}")
        console.print(f"[bold]File Size:[/bold] {info['file_size_bytes'] / 1024:.2f} KB")
        console.print(f"[bold]Cached:[/bold] {info['cache_size']} credential(s)")
        
        # File permissions
        stat = vault_file.stat()
        mode = oct(stat.st_mode)[-3:]
        console.print(f"[bold]Permissions:[/bold] {mode}")
        
        if mode != "600":
            console.print(f"  [yellow]⚠ Warning: Permissions should be 600 (owner read/write only)[/yellow]")
        
        console.print("\n[green]✓ Vault is healthy[/green]")
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("config-instance-add")
def config_instance_add(
    instance_id: str = typer.Option(..., "--id", help="Instance identifier (e.g., prod-mysql-01)"),
    db_type: str = typer.Option(..., "--type", help="Database type: mysql, postgresql"),
    host: str = typer.Option(..., "--host", help="Database host"),
    port: int = typer.Option(..., "--port", help="Database port"),
    credential_name: str = typer.Option(..., "--credential", help="Vault credential ID"),
    enabled: bool = typer.Option(True, "--enabled/--disabled", help="Enable this instance"),
    databases: Optional[str] = typer.Option(None, "--databases", help="Whitelist: comma-separated database names (empty = all)"),
    db_ignore: Optional[str] = typer.Option(None, "--db-ignore", help="Blacklist: comma-separated database names to exclude"),
    ssl_enabled: bool = typer.Option(False, "--ssl/--no-ssl", help="Enable SSL/TLS"),
    ssl_ca_cert: Optional[str] = typer.Option(None, "--ssl-ca-cert", help="Path to SSL CA certificate"),
    config_path: str = typer.Option("config/config.yaml", "--config", help="Path to config file"),
):
    """
    Add or update database instance in config file.
    
    Examples:
        # Basic MySQL instance
        vya-backupdb config-instance-add --id prod-mysql-01 --type mysql --host localhost --port 3306 --credential mysql-prod
        
        # PostgreSQL with SSL
        vya-backupdb config-instance-add --id prod-postgres-01 --type postgresql --host db.example.com --port 5432 --credential postgres-prod --ssl --ssl-ca-cert /etc/ssl/ca.pem
        
        # With database filters
        vya-backupdb config-instance-add --id mysql-app --type mysql --host localhost --port 3306 --credential mysql-prod --databases "app_prod,app_analytics" --db-ignore "test_db,dev_db"
    """
    import yaml
    
    console.print("[bold blue]VYA BackupDB - Add/Update Config Instance[/bold blue]\n")
    
    try:
        config_file = Path(config_path)
        
        # Load existing config or create new
        if config_file.exists():
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f) or {}
        else:
            config_data = {
                'application_name': 'vya-backupdb',
                'version': '2.0.0',
                'environment': 'production',
                'databases': [],
                'storage': {
                    'base_path': '/var/backups/vya_backupdb',
                    'structure': '{hostname}/{db_id}/{db_name}/{date}',
                    'compression_level': 6,
                    'checksum_algorithm': 'sha256'
                },
                'retention': {
                    'strategy': 'gfs',
                    'daily_keep': 7,
                    'weekly_keep': 4,
                    'monthly_keep': 12,
                    'cleanup_enabled': True
                },
                'logging': {
                    'level': 'INFO',
                    'format': 'json',
                    'output': 'file',
                    'file_path': '/var/log/vya_backupdb/app.log'
                }
            }
        
        # Ensure databases key exists
        if 'databases' not in config_data:
            config_data['databases'] = []
        
        # Parse database filters
        database_list = []
        if databases:
            database_list = [db.strip() for db in databases.split(',') if db.strip()]
        
        db_ignore_list = []
        if db_ignore:
            db_ignore_list = [db.strip() for db in db_ignore.split(',') if db.strip()]
        
        # Create instance config
        instance = {
            'id': instance_id,
            'type': db_type,
            'host': host,
            'port': port,
            'enabled': enabled,
            'credential_name': credential_name,
            'database': database_list,
            'db_ignore': db_ignore_list,
            'ssl_enabled': ssl_enabled
        }
        
        if ssl_ca_cert:
            instance['ssl_ca_cert'] = ssl_ca_cert
        
        # Check if instance exists
        existing_index = None
        for idx, db in enumerate(config_data['databases']):
            if db.get('id') == instance_id:
                existing_index = idx
                break
        
        if existing_index is not None:
            action = "Updated"
            config_data['databases'][existing_index] = instance
        else:
            action = "Added"
            config_data['databases'].append(instance)
        
        # Create directory if needed
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save config
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False, indent=2)
        
        console.print(f"[green]✓ {action}:[/green] Instance '{instance_id}'")
        console.print(f"  Type: {db_type}")
        console.print(f"  Host: {host}:{port}")
        console.print(f"  Credential: {credential_name}")
        console.print(f"  Enabled: {enabled}")
        if database_list:
            console.print(f"  Databases (whitelist): {', '.join(database_list)}")
        if db_ignore_list:
            console.print(f"  DB Ignore (blacklist): {', '.join(db_ignore_list)}")
        console.print(f"  Config: {config_path}")
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("config-instance-list")
def config_instance_list(
    config_path: str = typer.Option("config/config.yaml", "--config", help="Path to config file"),
    show_disabled: bool = typer.Option(False, "--show-disabled", help="Show disabled instances"),
):
    """
    List database instances in config file.
    
    Examples:
        vya-backupdb config-instance-list
        vya-backupdb config-instance-list --show-disabled
    """
    import yaml
    
    console.print("[bold blue]VYA BackupDB - Config Instances[/bold blue]\n")
    
    try:
        config_file = Path(config_path)
        
        if not config_file.exists():
            console.print("[yellow]Config file not found[/yellow]")
            console.print(f"\n[dim]Config: {config_path}[/dim]")
            console.print("[dim]Use 'config-instance-add' to create your first instance[/dim]")
            return
        
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        databases = config_data.get('databases', [])
        
        if not databases:
            console.print("[yellow]No instances in config[/yellow]")
            console.print(f"\n[dim]Config: {config_path}[/dim]")
            console.print("[dim]Use 'config-instance-add' to create your first instance[/dim]")
            return
        
        # Filter by enabled status
        if not show_disabled:
            databases = [db for db in databases if db.get('enabled', True)]
        
        if not databases:
            console.print("[yellow]No enabled instances[/yellow]")
            console.print(f"\n[dim]Use '--show-disabled' to see disabled instances[/dim]")
            return
        
        # Display as table
        table = Table(title=f"Config Instances ({len(databases)})")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Host:Port", style="green")
        table.add_column("Credential", style="yellow")
        table.add_column("Databases")
        table.add_column("Status")
        
        for db in databases:
            db_id = db.get('id', '?')
            db_type = db.get('type', '?')
            host = db.get('host', '?')
            port = db.get('port', '?')
            credential = db.get('credential_name', '?')
            enabled = db.get('enabled', True)
            
            # Database filtering info
            database_list = db.get('database', [])
            db_ignore_list = db.get('db_ignore', [])
            
            if database_list:
                db_info = f"✓ {len(database_list)} DBs"
            elif db_ignore_list:
                db_info = f"✗ {len(db_ignore_list)} excluded"
            else:
                db_info = "All databases"
            
            status = "[green]enabled[/green]" if enabled else "[red]disabled[/red]"
            
            table.add_row(
                db_id,
                db_type,
                f"{host}:{port}",
                credential,
                db_info,
                status
            )
        
        console.print(table)
        console.print(f"\n[dim]Config: {config_path}[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("config-instance-get")
def config_instance_get(
    instance_id: str = typer.Option(..., "--id", help="Instance identifier"),
    config_path: str = typer.Option("config/config.yaml", "--config", help="Path to config file"),
):
    """
    Get detailed information about a config instance.
    
    Examples:
        vya-backupdb config-instance-get --id prod-mysql-01
    """
    import yaml
    
    console.print("[bold blue]VYA BackupDB - Instance Details[/bold blue]\n")
    
    try:
        config_file = Path(config_path)
        
        if not config_file.exists():
            console.print(f"[red]✗ Config file not found:[/red] {config_path}")
            raise typer.Exit(code=1)
        
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        databases = config_data.get('databases', [])
        
        # Find instance
        instance = None
        for db in databases:
            if db.get('id') == instance_id:
                instance = db
                break
        
        if not instance:
            console.print(f"[red]✗ Instance not found:[/red] {instance_id}")
            raise typer.Exit(code=1)
        
        # Display details
        console.print(f"[bold]Instance:[/bold] [cyan]{instance_id}[/cyan]")
        console.print(f"[bold]Type:[/bold] {instance.get('type', '?')}")
        console.print(f"[bold]Host:[/bold] {instance.get('host', '?')}")
        console.print(f"[bold]Port:[/bold] {instance.get('port', '?')}")
        console.print(f"[bold]Credential:[/bold] {instance.get('credential_name', '?')}")
        console.print(f"[bold]Enabled:[/bold] {instance.get('enabled', True)}")
        
        # Database filtering
        database_list = instance.get('database', [])
        db_ignore_list = instance.get('db_ignore', [])
        
        if database_list:
            console.print(f"\n[bold]Databases (Whitelist):[/bold]")
            for db in database_list:
                console.print(f"  • {db}")
        else:
            console.print(f"\n[bold]Databases:[/bold] All (no whitelist)")
        
        if db_ignore_list:
            console.print(f"\n[bold]DB Ignore (Blacklist):[/bold]")
            for db in db_ignore_list:
                console.print(f"  • {db}")
        
        # SSL
        ssl_enabled = instance.get('ssl_enabled', False)
        console.print(f"\n[bold]SSL:[/bold] {'Enabled' if ssl_enabled else 'Disabled'}")
        if ssl_enabled and instance.get('ssl_ca_cert'):
            console.print(f"  CA Cert: {instance.get('ssl_ca_cert')}")
        
        console.print(f"\n[dim]Config: {config_path}[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("config-instance-remove")
def config_instance_remove(
    instance_id: str = typer.Option(..., "--id", help="Instance identifier"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
    config_path: str = typer.Option("config/config.yaml", "--config", help="Path to config file"),
):
    """
    Remove instance from config file.
    
    Examples:
        vya-backupdb config-instance-remove --id old-mysql
        vya-backupdb config-instance-remove --id old-mysql --force
    """
    import yaml
    
    console.print("[bold blue]VYA BackupDB - Remove Instance[/bold blue]\n")
    
    try:
        config_file = Path(config_path)
        
        if not config_file.exists():
            console.print(f"[red]✗ Config file not found:[/red] {config_path}")
            raise typer.Exit(code=1)
        
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        databases = config_data.get('databases', [])
        
        # Find instance
        found = False
        for idx, db in enumerate(databases):
            if db.get('id') == instance_id:
                found = True
                instance = db
                
                # Confirm deletion
                if not force:
                    console.print(f"Instance: [cyan]{instance_id}[/cyan]")
                    console.print(f"Type: {instance.get('type', '?')}")
                    console.print(f"Host: {instance.get('host', '?')}:{instance.get('port', '?')}")
                    
                    confirm = typer.confirm("\nAre you sure you want to remove this instance?")
                    if not confirm:
                        console.print("[yellow]Cancelled[/yellow]")
                        raise typer.Exit(code=0)
                
                # Remove instance
                databases.pop(idx)
                config_data['databases'] = databases
                
                # Save config
                with open(config_file, 'w') as f:
                    yaml.dump(config_data, f, default_flow_style=False, sort_keys=False, indent=2)
                
                console.print(f"[green]✓ Removed:[/green] Instance '{instance_id}'")
                console.print(f"  Config: {config_path}")
                break
        
        if not found:
            console.print(f"[red]✗ Instance not found:[/red] {instance_id}")
            raise typer.Exit(code=1)
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("config-instance-enable")
def config_instance_enable(
    instance_id: str = typer.Option(..., "--id", help="Instance identifier"),
    config_path: str = typer.Option("config/config.yaml", "--config", help="Path to config file"),
):
    """
    Enable a database instance.
    
    Examples:
        vya-backupdb config-instance-enable --id prod-mysql-01
    """
    import yaml
    
    console.print("[bold blue]VYA BackupDB - Enable Instance[/bold blue]\n")
    
    try:
        config_file = Path(config_path)
        
        if not config_file.exists():
            console.print(f"[red]✗ Config file not found:[/red] {config_path}")
            raise typer.Exit(code=1)
        
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        databases = config_data.get('databases', [])
        
        # Find and update instance
        found = False
        for db in databases:
            if db.get('id') == instance_id:
                found = True
                db['enabled'] = True
                
                # Save config
                with open(config_file, 'w') as f:
                    yaml.dump(config_data, f, default_flow_style=False, sort_keys=False, indent=2)
                
                console.print(f"[green]✓ Enabled:[/green] Instance '{instance_id}'")
                console.print(f"  Config: {config_path}")
                break
        
        if not found:
            console.print(f"[red]✗ Instance not found:[/red] {instance_id}")
            raise typer.Exit(code=1)
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(code=1)


@app.command("config-instance-disable")
def config_instance_disable(
    instance_id: str = typer.Option(..., "--id", help="Instance identifier"),
    config_path: str = typer.Option("config/config.yaml", "--config", help="Path to config file"),
):
    """
    Disable a database instance.
    
    Examples:
        vya-backupdb config-instance-disable --id old-mysql
    """
    import yaml
    
    console.print("[bold blue]VYA BackupDB - Disable Instance[/bold blue]\n")
    
    try:
        config_file = Path(config_path)
        
        if not config_file.exists():
            console.print(f"[red]✗ Config file not found:[/red] {config_path}")
            raise typer.Exit(code=1)
        
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        databases = config_data.get('databases', [])
        
        # Find and update instance
        found = False
        for db in databases:
            if db.get('id') == instance_id:
                found = True
                db['enabled'] = False
                
                # Save config
                with open(config_file, 'w') as f:
                    yaml.dump(config_data, f, default_flow_style=False, sort_keys=False, indent=2)
                
                console.print(f"[green]✓ Disabled:[/green] Instance '{instance_id}'")
                console.print(f"  Config: {config_path}")
                break
        
        if not found:
            console.print(f"[red]✗ Instance not found:[/red] {instance_id}")
            raise typer.Exit(code=1)
        
    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        raise typer.Exit(code=1)


def main():
    """Main CLI entry point."""
    app()


if __name__ == "__main__":
    main()
