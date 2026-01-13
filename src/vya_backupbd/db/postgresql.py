"""
PostgreSQL database adapter implementation.

Provides PostgreSQL-specific backup operations using pg_dump
and connection management.
"""

import subprocess
import logging
import os
from typing import Any
from sqlalchemy import text

from vya_backupbd.config.models import DatabaseConfig
from vya_backupbd.db.base import DatabaseAdapter
from vya_backupbd.utils.log_sanitizer import safe_repr

logger = logging.getLogger(__name__)


class PostgreSQLAdapter(DatabaseAdapter):
    """
    PostgreSQL database adapter.
    
    Implements backup operations for PostgreSQL databases using pg_dump
    command-line tool.
    
    Example:
        >>> config = DatabaseConfig(type="postgresql", ...)
        >>> with PostgreSQLAdapter(config) as adapter:
        ...     databases = adapter.get_databases()
        ...     adapter.backup_database("myapp", "/backups/myapp.sql")
    """
    
    def __init__(self, config: DatabaseConfig):
        """
        Initialize PostgreSQL adapter.
        
        Args:
            config: Database configuration
            
        Raises:
            ValueError: If config type is not 'postgresql'
        """
        logger.debug(f"=== Função: __init__ (PostgreSQLAdapter) ===")
        logger.debug(f"==> PARAM: config TYPE: {type(config)}, CONTENT: {safe_repr(config)}")
        
        if config.type != "postgresql":
            raise ValueError(
                f"PostgreSQL adapter requires type='postgresql', got '{config.type}'"
            )
            
        super().__init__(config)
        logger.debug(f"=== Término Função: __init__ (PostgreSQLAdapter) ===")
    
    def get_databases(self) -> list[str]:
        """
        Get list of PostgreSQL databases.
        
        Returns:
            List of database names (excluding system databases)
        """
        logger.debug(f"=== Função: get_databases (PostgreSQLAdapter) ===")
        
        try:
            query = text(
                "SELECT datname FROM pg_database "
                "WHERE datistemplate = false"
            )
            result = self._execute_query(query)
            
            # Extract database names from result tuples
            all_databases = [row[0] for row in result]
            
            # Filter out system databases
            user_databases = self.filter_system_databases(all_databases)
            
            logger.debug(f"Found {len(user_databases)} user databases")
            logger.debug(f"=== Término Função: get_databases (PostgreSQLAdapter) ===")
            return user_databases
            
        except Exception as e:
            logger.error(f"Error getting databases: {e}")
            logger.debug(f"=== Término Função: get_databases (PostgreSQLAdapter) COM ERRO ===")
            raise
    
    def test_connection(self) -> bool:
        """
        Test PostgreSQL connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        logger.debug(f"=== Função: test_connection (PostgreSQLAdapter) ===")
        
        try:
            query = text("SELECT 1")
            result = self._execute_query(query)
            logger.debug(f"=== Término Função: test_connection (PostgreSQLAdapter) ===")
            return len(result) > 0
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            logger.debug(f"=== Término Função: test_connection (PostgreSQLAdapter) COM ERRO ===")
            return False
    
    def get_backup_command(self, database: str, output_path: str) -> str:
        """
        Generate pg_dump command for backup.
        
        Args:
            database: Name of database to backup
            output_path: Path where backup file should be saved
            
        Returns:
            pg_dump command string
        """
        logger.debug(f"=== Função: get_backup_command (PostgreSQLAdapter) ===")
        logger.debug(f"==> PARAM: database TYPE: {type(database)}, SIZE: {len(database)} chars, CONTENT: {database}")
        logger.debug(f"==> PARAM: output_path TYPE: {type(output_path)}, SIZE: {len(output_path)} chars, CONTENT: {output_path}")
        
        # Build pg_dump command with options
        cmd_parts = [
            "pg_dump",
            f"--username={self.config.username}",
            f"--host={self.config.host}",
            f"--port={self.config.port}",
            "--clean",  # Include DROP commands
            "--create",  # Include CREATE DATABASE
            "--if-exists",  # Use IF EXISTS for DROP commands
        ]
        
        # Determine format based on output file extension
        if output_path.endswith(".dump") or output_path.endswith(".custom"):
            cmd_parts.append("--format=custom")  # Custom format for better compression
        else:
            cmd_parts.append("--format=plain")  # Plain SQL format
        
        # Add SSL if enabled
        if self.config.ssl:
            cmd_parts.append("--set=sslmode=require")
        
        # Add database name
        cmd_parts.append(database)
        
        # Build full command
        command = " ".join(cmd_parts)
        
        # Handle compressed output for plain format
        if output_path.endswith(".gz") and "--format=plain" in command:
            command = f"{command} | gzip > {output_path}"
        elif "--format=custom" in command:
            # Custom format writes directly to file
            command = f"{command} --file={output_path}"
        else:
            command = f"{command} > {output_path}"
        
        logger.debug(f"=== Término Função: get_backup_command (PostgreSQLAdapter) ===")
        return command
    
    def backup_database(self, database: str, output_path: str) -> bool:
        """
        Backup PostgreSQL database using pg_dump.
        
        Args:
            database: Name of database to backup
            output_path: Path where backup file should be saved
            
        Returns:
            True if backup successful, False otherwise
        """
        logger.debug(f"=== Função: backup_database (PostgreSQLAdapter) ===")
        logger.debug(f"==> PARAM: database TYPE: {type(database)}, SIZE: {len(database)} chars, CONTENT: {database}")
        logger.debug(f"==> PARAM: output_path TYPE: {type(output_path)}, SIZE: {len(output_path)} chars, CONTENT: {output_path}")
        
        try:
            command = self.get_backup_command(database, output_path)
            
            logger.info(f"Starting backup of database '{database}' to '{output_path}'")
            
            # Set PGPASSWORD environment variable for authentication
            env = os.environ.copy()
            env['PGPASSWORD'] = self.config.password
            
            # Execute backup command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                env=env,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                logger.info(f"Backup completed successfully: {database}")
                logger.debug(f"=== Término Função: backup_database (PostgreSQLAdapter) ===")
                return True
            else:
                logger.error(f"Backup failed: {result.stderr}")
                logger.debug(f"=== Término Função: backup_database (PostgreSQLAdapter) COM ERRO ===")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Backup command failed: {e}")
            logger.debug(f"=== Término Função: backup_database (PostgreSQLAdapter) COM ERRO ===")
            return False
            
        except subprocess.TimeoutExpired:
            logger.error(f"Backup timeout exceeded for database: {database}")
            logger.debug(f"=== Término Função: backup_database (PostgreSQLAdapter) COM ERRO ===")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error during backup: {e}")
            logger.debug(f"=== Término Função: backup_database (PostgreSQLAdapter) COM ERRO ===")
            return False
    
    def restore_database(self, database: str, backup_file: str) -> bool:
        """
        Restore PostgreSQL database from backup file.
        
        Args:
            database: Name of database to restore
            backup_file: Path to backup file (.sql or .sql.gz)
            
        Returns:
            True if restore successful, False otherwise
        """
        logger.debug(f"=== Função: restore_database (PostgreSQLAdapter) ===")
        logger.debug(f"==> PARAM: database TYPE: {type(database)}, SIZE: {len(database)} chars, CONTENT: {database}")
        logger.debug(f"==> PARAM: backup_file TYPE: {type(backup_file)}, SIZE: {len(backup_file)} chars, CONTENT: {backup_file}")
        
        try:
            logger.info(f"Starting restore of database '{database}' from '{backup_file}'")
            
            # Set PGPASSWORD environment variable
            env = subprocess.os.environ.copy()
            env['PGPASSWORD'] = self.config.password
            
            # Create database if it doesn't exist
            logger.debug(f"Creating database '{database}' if not exists")
            create_cmd = [
                "psql",
                f"--username={self.config.username}",
                f"--host={self.config.host}",
                f"--port={self.config.port}",
                "--dbname=postgres",
                "-c",
                f"CREATE DATABASE {database};"
            ]
            
            create_result = subprocess.run(
                create_cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=30
            )
            
            if create_result.returncode != 0:
                # Database might already exist, that's ok
                logger.debug(f"Database creation: {create_result.stderr}")
            else:
                logger.debug(f"Database '{database}' created successfully")
            
            # Build psql command (connect to the target database)
            cmd_parts = [
                "psql",
                f"--username={self.config.username}",
                f"--host={self.config.host}",
                f"--port={self.config.port}",
                f"--dbname={database}",
                "--quiet",
                "--single-transaction"
            ]
            
            # Detect original database name to replace if needed
            if backup_file.endswith('.zip'):
                detect_cmd = f"unzip -p {backup_file} | grep -m1 '\\\\connect '"
            elif backup_file.endswith('.gz'):
                detect_cmd = f"gunzip < {backup_file} | grep -m1 '\\\\connect '"
            else:
                detect_cmd = f"grep -m1 '\\\\connect ' {backup_file}"
            
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
                    # Extract database name from "\connect dbname"
                    parts = detect_result.stdout.strip().split()
                    if len(parts) >= 2:
                        original_db = parts[1].strip('"')
                        logger.debug(f"Detected original database name: {original_db}")
            except Exception as e:
                logger.warning(f"Could not detect original database name: {e}")
                original_db = None
            
            # Build filter to remove problematic SQL commands
            # Remove: DROP DATABASE, CREATE DATABASE, CREATE ROLE with @, LOCALE_PROVIDER
            filter_cmd = "grep -v -E '(^DROP DATABASE|^CREATE DATABASE|CREATE ROLE.*@|LOCALE_PROVIDER|^\\\\connect)'"
            
            # Handle compressed files with sed replacement and filtering
            if backup_file.endswith('.gz'):
                if original_db and original_db != database:
                    command = f"gunzip < {backup_file} | {filter_cmd} | sed 's/{original_db}/{database}/g' | {' '.join(cmd_parts)}"
                else:
                    command = f"gunzip < {backup_file} | {filter_cmd} | {' '.join(cmd_parts)}"
            elif backup_file.endswith('.zip'):
                if original_db and original_db != database:
                    command = f"unzip -p {backup_file} | {filter_cmd} | sed 's/{original_db}/{database}/g' | {' '.join(cmd_parts)}"
                else:
                    command = f"unzip -p {backup_file} | {filter_cmd} | {' '.join(cmd_parts)}"
            else:
                if original_db and original_db != database:
                    command = f"cat {backup_file} | {filter_cmd} | sed 's/{original_db}/{database}/g' | {' '.join(cmd_parts)}"
                else:
                    command = f"cat {backup_file} | {filter_cmd} | {' '.join(cmd_parts)}"
            
            logger.debug(f"Restore command prepared")
            
            # Execute restore command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                env=env,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                logger.info(f"Restore completed successfully: {database}")
                logger.debug(f"=== Término Função: restore_database (PostgreSQLAdapter) ===")
                return True
            else:
                logger.error(f"Restore failed: {result.stderr}")
                logger.debug(f"=== Término Função: restore_database (PostgreSQLAdapter) COM ERRO ===")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Restore command failed: {e}")
            logger.debug(f"=== Término Função: restore_database (PostgreSQLAdapter) COM ERRO ===")
            return False
            
        except subprocess.TimeoutExpired:
            logger.error(f"Restore timeout exceeded for database: {database}")
            logger.debug(f"=== Término Função: restore_database (PostgreSQLAdapter) COM ERRO ===")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error during restore: {e}")
            logger.debug(f"=== Término Função: restore_database (PostgreSQLAdapter) COM ERRO ===")
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
