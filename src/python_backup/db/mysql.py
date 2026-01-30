"""
MySQL database adapter implementation.

Provides MySQL-specific backup operations using mysqldump
and connection management.
"""

import subprocess
import logging
from typing import Any
from sqlalchemy import text

from python_backup.config.models import DatabaseConfig
from python_backup.db.base import DatabaseAdapter
from python_backup.utils.log_sanitizer import safe_repr

logger = logging.getLogger(__name__)


class MySQLAdapter(DatabaseAdapter):
    """
    MySQL database adapter.
    
    Implements backup operations for MySQL databases using mysqldump
    command-line tool.
    
    Example:
        >>> config = DatabaseConfig(type="mysql", ...)
        >>> with MySQLAdapter(config) as adapter:
        ...     databases = adapter.get_databases()
        ...     adapter.backup_database("myapp", "/backups/myapp.sql")
    """
    
    def __init__(self, config: DatabaseConfig):
        """
        Initialize MySQL adapter.
        
        Args:
            config: Database configuration
            
        Raises:
            ValueError: If config type is not 'mysql'
        """
        logger.debug(f"=== Função: __init__ (MySQLAdapter) ===")
        logger.debug(f"==> PARAM: config TYPE: {type(config)}, CONTENT: {safe_repr(config)}")
        
        if config.type != "mysql":
            raise ValueError(f"MySQL adapter requires type='mysql', got '{config.type}'")
            
        super().__init__(config)
        logger.debug(f"=== Término Função: __init__ (MySQLAdapter) ===")
    
    def get_databases(self) -> list[str]:
        """
        Get list of MySQL databases.
        
        Returns:
            List of database names (excluding system databases)
        """
        logger.debug(f"=== Função: get_databases (MySQLAdapter) ===")
        
        try:
            query = text("SHOW DATABASES")
            result = self._execute_query(query)
            
            # Extract database names from result tuples
            all_databases = [row[0] for row in result]
            
            # Filter out system databases
            user_databases = self.filter_system_databases(all_databases)
            
            logger.debug(f"Found {len(user_databases)} user databases")
            logger.debug(f"=== Término Função: get_databases (MySQLAdapter) ===")
            return user_databases
            
        except Exception as e:
            logger.error(f"Error getting databases: {e}")
            logger.debug(f"=== Término Função: get_databases (MySQLAdapter) COM ERRO ===")
            raise
    
    def test_connection(self) -> bool:
        """
        Test MySQL connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        logger.debug(f"=== Função: test_connection (MySQLAdapter) ===")
        
        try:
            query = text("SELECT 1")
            result = self._execute_query(query)
            logger.debug(f"=== Término Função: test_connection (MySQLAdapter) ===")
            return len(result) > 0
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            logger.debug(f"=== Término Função: test_connection (MySQLAdapter) COM ERRO ===")
            return False
    
    def get_backup_command(self, database: str, output_path: str) -> str:
        """
        Generate mysqldump command for backup.
        
        Args:
            database: Name of database to backup
            output_path: Path where backup file should be saved
            
        Returns:
            mysqldump command string
        """
        logger.debug(f"=== Função: get_backup_command (MySQLAdapter) ===")
        logger.debug(f"==> PARAM: database TYPE: {type(database)}, SIZE: {len(database)} chars, CONTENT: {database}")
        logger.debug(f"==> PARAM: output_path TYPE: {type(output_path)}, SIZE: {len(output_path)} chars, CONTENT: {output_path}")
        
        # Build mysqldump command with options
        cmd_parts = [
            "mysqldump",
            f"--user={self.config.username}",
            f"--password={self.config.password}",
            f"--host={self.config.host}",
            f"--port={self.config.port}",
            "--protocol=TCP",  # Force TCP connection (avoid Unix socket)
            "--single-transaction",  # Consistent backup without locking
            "--routines",  # Include stored procedures
            "--triggers",  # Include triggers
            "--events",  # Include events
            "--add-drop-database",  # Add DROP DATABASE before CREATE
            "--set-gtid-purged=OFF",  # Disable GTID info to avoid restore issues
            "--force",  # Continue even if SQL errors occur
        ]
        
        # Add SSL if enabled
        if self.config.ssl_enabled:
            cmd_parts.append("--ssl-mode=REQUIRED")
        
        # Add database name
        cmd_parts.append(database)
        
        # Build full command
        command = " ".join(cmd_parts)
        
        # Handle compressed output
        if output_path.endswith(".gz"):
            command = f"{command} | gzip > {output_path}"
        else:
            command = f"{command} > {output_path}"
        
        logger.debug(f"=== Término Função: get_backup_command (MySQLAdapter) ===")
        return command
    
    def backup_database(self, database: str, output_path: str) -> bool:
        """
        Backup MySQL database using mysqldump.
        
        Args:
            database: Name of database to backup
            output_path: Path where backup file should be saved
            
        Returns:
            True if backup successful, False otherwise
        """
        logger.debug(f"=== Função: backup_database (MySQLAdapter) ===")
        logger.debug(f"==> PARAM: database TYPE: {type(database)}, SIZE: {len(database)} chars, CONTENT: {database}")
        logger.debug(f"==> PARAM: output_path TYPE: {type(output_path)}, SIZE: {len(output_path)} chars, CONTENT: {output_path}")
        
        try:
            command = self.get_backup_command(database, output_path)
            
            logger.info(f"Executing mysqldump for database '{database}'")
            logger.info(f"Output file: '{output_path}'")
            
            # Execute backup command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                logger.info(f"mysqldump completed successfully for database '{database}'")
                logger.debug(f"=== Término Função: backup_database (MySQLAdapter) ===")
                return True
            else:
                logger.error(f"mysqldump FAILED: {result.stderr}")
                logger.debug(f"=== Término Função: backup_database (MySQLAdapter) COM ERRO ===")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Backup command failed: {e}")
            logger.debug(f"=== Término Função: backup_database (MySQLAdapter) COM ERRO ===")
            return False
            
        except subprocess.TimeoutExpired as e:
            timeout_value = e.args[1] if len(e.args) > 1 else 3600
            logger.error(f"Timeout exceeded during mysqldump for database '{database}' (timeout: {timeout_value}s)")
            logger.debug(f"=== Término Função: backup_database (MySQLAdapter) COM ERRO ===")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error during backup: {e}")
            logger.debug(f"=== Término Função: backup_database (MySQLAdapter) COM ERRO ===")
            return False
    
    def restore_database(self, database: str, backup_file: str) -> bool:
        """
        Restore MySQL database from backup file.
        
        Disaster Recovery Mode:
        - Verifies user privileges
        - Creates database if it doesn't exist
        - Creates backup user if needed
        - Grants necessary permissions
        - Restores database content
        
        Args:
            database: Name of database to restore
            backup_file: Path to backup file (.sql or .sql.gz)
            
        Returns:
            True if restore successful, False otherwise
        """
        logger.debug(f"=== Função: restore_database (MySQLAdapter) ===")
        logger.debug(f"==> PARAM: database TYPE: {type(database)}, SIZE: {len(database)} chars, CONTENT: {database}")
        logger.debug(f"==> PARAM: backup_file TYPE: {type(backup_file)}, SIZE: {len(backup_file)} chars, CONTENT: {backup_file}")
        
        try:
            logger.info(f"[DISASTER RECOVERY] Starting restore of database '{database}' from '{backup_file}'")
            
            # Step 1: Verify server connectivity and privileges
            logger.info(f"[STEP 1/4] Verifying MySQL server connectivity and privileges...")
            verify_cmd = [
                "mysql",
                f"--user={self.config.username}",
                f"--password={self.config.password}",
                f"--host={self.config.host}",
                f"--port={self.config.port}",
                "--protocol=TCP",
                "-e",
                "SELECT 1;"
            ]
            
            verify_result = subprocess.run(
                verify_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if verify_result.returncode != 0:
                logger.error(f"Cannot connect to MySQL server: {verify_result.stderr}")
                return False
            
            logger.info(f"[STEP 1/4] Connection verified successfully")
            
            # Step 2: Check if database exists, create if not
            logger.info(f"[STEP 2/4] Checking if database '{database}' exists...")
            check_db_cmd = [
                "mysql",
                f"--user={self.config.username}",
                f"--password={self.config.password}",
                f"--host={self.config.host}",
                f"--port={self.config.port}",
                "--protocol=TCP",
                "-e",
                f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{database}';"
            ]
            
            check_result = subprocess.run(
                check_db_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            db_exists = database in check_result.stdout
            
            if not db_exists:
                logger.info(f"[STEP 2/4] Database '{database}' does not exist, creating...")
                create_cmd = [
                    "mysql",
                    f"--user={self.config.username}",
                    f"--password={self.config.password}",
                    f"--host={self.config.host}",
                    f"--port={self.config.port}",
                    "--protocol=TCP",
                    "-e",
                    f"CREATE DATABASE `{database}` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
                ]
                
                create_result = subprocess.run(
                    create_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if create_result.returncode != 0:
                    logger.error(f"Failed to create database: {create_result.stderr}")
                    return False
                
                logger.info(f"[STEP 2/4] Database '{database}' created successfully")
            else:
                logger.info(f"[STEP 2/4] Database '{database}' already exists")
            
            # Step 3: Check and create backup user if needed
            logger.info(f"[STEP 3/4] Verifying backup user exists...")
            check_user_cmd = [
                "mysql",
                f"--user={self.config.username}",
                f"--password={self.config.password}",
                f"--host={self.config.host}",
                f"--port={self.config.port}",
                "--protocol=TCP",
                "-e",
                f"SELECT User FROM mysql.user WHERE User = 'backup';"
            ]
            
            user_result = subprocess.run(
                check_user_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if 'backup' not in user_result.stdout:
                logger.info(f"[STEP 3/4] Creating backup user...")
                # Note: In production, password should be configurable
                create_user_cmd = [
                    "mysql",
                    f"--user={self.config.username}",
                    f"--password={self.config.password}",
                    f"--host={self.config.host}",
                    f"--port={self.config.port}",
                    "--protocol=TCP",
                    "-e",
                    f"CREATE USER IF NOT EXISTS 'backup'@'%' IDENTIFIED BY 'BackupUser2026!'; GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER, CREATE TEMPORARY TABLES, LOCK TABLES, EXECUTE, SHOW VIEW, CREATE ROUTINE, ALTER ROUTINE, EVENT, TRIGGER ON `{database}`.* TO 'backup'@'%'; FLUSH PRIVILEGES;"
                ]
                
                user_create_result = subprocess.run(
                    create_user_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if user_create_result.returncode == 0:
                    logger.info(f"[STEP 3/4] Backup user created with permissions on '{database}'")
                else:
                    logger.warning(f"[STEP 3/4] Could not create backup user: {user_create_result.stderr}")
            else:
                logger.info(f"[STEP 3/4] Backup user already exists")
            
            # Step 4: Restore database
            logger.info(f"[STEP 4/4] Starting database restore...")
            
            # Build mysql command
            cmd_parts = [
                "mysql",
                f"--user={self.config.username}",
                f"--password={self.config.password}",
                f"--host={self.config.host}",
                f"--port={self.config.port}",
                "--protocol=TCP",
                f"--database={database}"
            ]
            
            # Extract original database name from SQL to replace it
            # Get first line to detect original database name
            if backup_file.endswith('.zip'):
                detect_cmd = f"unzip -p {backup_file} | grep -m1 'USE `'"
            elif backup_file.endswith('.gz'):
                detect_cmd = f"gunzip < {backup_file} | grep -m1 'USE `'"
            else:
                detect_cmd = f"grep -m1 'USE `' {backup_file}"
            
            try:
                detect_result = subprocess.run(
                    detect_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                original_db = None
                if detect_result.returncode == 0 and detect_result.stdout:
                    # Extract database name from "USE `dbname`;"
                    match = detect_result.stdout.strip()
                    if 'USE `' in match:
                        original_db = match.split('`')[1]
                        logger.debug(f"Detected original database name: {original_db}")
            except Exception as e:
                logger.warning(f"Could not detect original database name: {e}")
                original_db = None
            
            # Handle compressed files with sed replacement
            if backup_file.endswith('.gz'):
                if original_db and original_db != database:
                    # Replace database name in SQL
                    command = f"gunzip < {backup_file} | sed 's/`{original_db}`/`{database}`/g' | {' '.join(cmd_parts)}"
                else:
                    command = f"gunzip < {backup_file} | {' '.join(cmd_parts)}"
            elif backup_file.endswith('.zip'):
                if original_db and original_db != database:
                    # Replace database name in SQL
                    command = f"unzip -p {backup_file} | sed 's/`{original_db}`/`{database}`/g' | {' '.join(cmd_parts)}"
                else:
                    command = f"unzip -p {backup_file} | {' '.join(cmd_parts)}"
            else:
                if original_db and original_db != database:
                    command = f"sed 's/`{original_db}`/`{database}`/g' {backup_file} | {' '.join(cmd_parts)}"
                else:
                    command = f"{' '.join(cmd_parts)} < {backup_file}"
            
            logger.debug(f"Restore command prepared")
            
            # Execute restore command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                logger.info(f"Restore completed successfully: {database}")
                logger.debug(f"=== Término Função: restore_database (MySQLAdapter) ===")
                return True
            else:
                logger.error(f"Restore failed: {result.stderr}")
                logger.debug(f"=== Término Função: restore_database (MySQLAdapter) COM ERRO ===")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Restore command failed: {e}")
            logger.debug(f"=== Término Função: restore_database (MySQLAdapter) COM ERRO ===")
            return False
            
        except subprocess.TimeoutExpired:
            logger.error(f"Restore timeout exceeded for database: {database}")
            logger.debug(f"=== Término Função: restore_database (MySQLAdapter) COM ERRO ===")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error during restore: {e}")
            logger.debug(f"=== Término Função: restore_database (MySQLAdapter) COM ERRO ===")
            return False
    
    def _execute_query(self, query: str | Any) -> list[tuple]:
        """
        Execute SQL query and return results.
        
        Args:
            query: SQL query string or text object
            
        Returns:
            List of result tuples
        """
        with self.engine.connect() as conn:
            result = conn.execute(query)
            return result.fetchall()
