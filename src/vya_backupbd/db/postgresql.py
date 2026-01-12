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
        if config.type != "postgresql":
            raise ValueError(
                f"PostgreSQL adapter requires type='postgresql', got '{config.type}'"
            )
            
        super().__init__(config)
    
    def get_databases(self) -> list[str]:
        """
        Get list of PostgreSQL databases.
        
        Returns:
            List of database names (excluding system databases)
        """
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
            return user_databases
            
        except Exception as e:
            logger.error(f"Error getting databases: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test PostgreSQL connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            query = text("SELECT 1")
            result = self._execute_query(query)
            return len(result) > 0
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
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
                return True
            else:
                logger.error(f"Backup failed: {result.stderr}")
                return False
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Backup command failed: {e}")
            return False
            
        except subprocess.TimeoutExpired:
            logger.error(f"Backup timeout exceeded for database: {database}")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error during backup: {e}")
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
