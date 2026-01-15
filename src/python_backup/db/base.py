"""
Abstract base class for database adapters.

Defines the interface that all database adapters must implement
for backup operations, connection management, and database queries.
"""

from abc import ABC, abstractmethod
from typing import Any
from sqlalchemy.engine import Engine

from python_backup.config.models import DatabaseConfig
from python_backup.db.engine import create_db_engine


class DatabaseAdapter(ABC):
    """
    Abstract base class for database adapters.
    
    Provides common functionality and defines the interface that
    all concrete database adapters must implement.
    
    Attributes:
        config: Database configuration
        engine: SQLAlchemy engine for database connections
    """
    
    def __init__(self, config: DatabaseConfig):
        """
        Initialize database adapter.
        
        Args:
            config: Database configuration
        """
        self.config = config
        self.engine: Engine = create_db_engine(config)
        
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - dispose engine."""
        self.close()
        return False
        
    def __repr__(self) -> str:
        """String representation of adapter."""
        return (
            f"{self.__class__.__name__}("
            f"type={self.config.type}, "
            f"host={self.config.host}, "
            f"database={self.config.database})"
        )
    
    def close(self) -> None:
        """
        Close database connections and dispose engine.
        
        Should be called when adapter is no longer needed.
        """
        if self.engine:
            self.engine.dispose()
    
    def filter_system_databases(self, databases: list[str]) -> list[str]:
        """
        Filter out system databases from list.
        
        Uses the exclude_databases list from configuration to filter
        out system databases that should not be backed up.
        
        Args:
            databases: List of all database names
            
        Returns:
            Filtered list of user databases only
            
        Example:
            >>> adapter.filter_system_databases(["mysql", "myapp", "sys"])
            ["myapp"]
        """
        excluded = set(self.config.exclude_databases)
        return [db for db in databases if db not in excluded]
    
    def _execute_query(self, query: str) -> list[tuple]:
        """
        Execute SQL query and return results.
        
        Internal helper method for executing queries.
        
        Args:
            query: SQL query string
            
        Returns:
            List of result tuples
            
        Raises:
            Exception: If query execution fails
        """
        with self.engine.connect() as conn:
            result = conn.execute(query)
            return result.fetchall()
    
    @abstractmethod
    def get_databases(self) -> list[str]:
        """
        Get list of databases on the server.
        
        Returns:
            List of database names (excluding system databases)
            
        Example:
            >>> adapter.get_databases()
            ["myapp", "testdb", "production"]
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test database connection.
        
        Returns:
            True if connection successful, False otherwise
            
        Example:
            >>> if adapter.test_connection():
            ...     print("Connection OK")
        """
        pass
    
    @abstractmethod
    def backup_database(self, database: str, output_path: str) -> bool:
        """
        Backup a specific database.
        
        Args:
            database: Name of database to backup
            output_path: Path where backup file should be saved
            
        Returns:
            True if backup successful, False otherwise
            
        Example:
            >>> adapter.backup_database("myapp", "/backups/myapp_20260112.sql")
            True
        """
        pass
    
    @abstractmethod
    def get_backup_command(self, database: str, output_path: str) -> str:
        """
        Generate backup command for database.
        
        Args:
            database: Name of database to backup
            output_path: Path where backup file should be saved
            
        Returns:
            Backup command string
            
        Example:
            >>> cmd = adapter.get_backup_command("myapp", "/tmp/backup.sql")
            >>> print(cmd)
            "mysqldump --user=... --host=... myapp > /tmp/backup.sql"
        """
        pass
