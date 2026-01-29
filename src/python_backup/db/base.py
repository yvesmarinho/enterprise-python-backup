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
        
        Only removes predefined system databases specific to the database type.
        Does NOT use db_ignore - that's handled separately in get_filtered_databases.
        
        Args:
            databases: List of all database names
            
        Returns:
            Filtered list of user databases only
            
        Example:
            >>> adapter.filter_system_databases(["mysql", "myapp", "sys"])
            ["myapp"]
        """
        # System databases by type (hardcoded, not from config)
        system_dbs_map = {
            "mysql": ["information_schema", "performance_schema", "mysql", "sys"],
            "postgresql": ["postgres", "template0", "template1"],
            "files": []  # No system databases for files
        }
        system_dbs = set(system_dbs_map.get(self.config.type, []))
        return [db for db in databases if db not in system_dbs]
    
    def get_filtered_databases(self, all_databases: list[str]) -> list[str]:
        """
        Apply database filtering with precedence rules.
        
        Filtering order (precedence):
        1. INCLUSION (databases field) - defines initial set
        2. EXCLUSION (db_ignore field) - removes from set
        3. SYSTEM databases - always removed (mysql, postgres, etc.)
        
        Args:
            all_databases: List of all available databases on server
            
        Returns:
            Filtered list of databases to backup
            
        Examples:
            >>> # Scenario 1: All databases (default)
            >>> config.databases = []
            >>> config.db_ignore = []
            >>> adapter.get_filtered_databases(["app", "test", "mysql"])
            ["app", "test"]  # mysql excluded as system DB
            
            >>> # Scenario 2: Whitelist specific databases
            >>> config.databases = ["app"]
            >>> config.db_ignore = []
            >>> adapter.get_filtered_databases(["app", "test", "dev"])
            ["app"]
            
            >>> # Scenario 3: Blacklist specific databases
            >>> config.databases = []
            >>> config.db_ignore = ["test", "dev"]
            >>> adapter.get_filtered_databases(["app", "test", "dev"])
            ["app"]
            
            >>> # Scenario 4: Whitelist + Blacklist
            >>> config.databases = ["app", "crm"]
            >>> config.db_ignore = ["crm"]
            >>> adapter.get_filtered_databases(["app", "crm", "test"])
            ["app"]
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Support both old (db_list/database) and new (databases) field names
        databases_to_include = (
            getattr(self.config, 'databases', []) or
            getattr(self.config, 'database', []) or
            []
        )
        
        # Support both old (exclude_databases) and new (db_ignore) field names
        databases_to_exclude = (
            getattr(self.config, 'db_ignore', []) or
            getattr(self.config, 'exclude_databases', []) or
            []
        )
        
        logger.debug(f"Filtering databases: total={len(all_databases)}")
        logger.debug(f"  Include filter (whitelist): {databases_to_include or 'all'}")
        logger.debug(f"  Exclude filter (blacklist): {databases_to_exclude or 'none'}")
        
        # Step 1: Apply INCLUSION filter (databases)
        if not databases_to_include:
            # Empty list = include all databases
            included = all_databases.copy()
            logger.debug(f"  Step 1 (inclusion): all {len(included)} databases")
        else:
            # Non-empty list = only include specified databases
            included = [db for db in all_databases if db in databases_to_include]
            logger.debug(f"  Step 1 (inclusion): {len(included)} databases matched whitelist")
        
        # Step 2: Apply EXCLUSION filter (db_ignore)
        if databases_to_exclude:
            before_count = len(included)
            included = [db for db in included if db not in databases_to_exclude]
            logger.debug(f"  Step 2 (exclusion): removed {before_count - len(included)} databases")
        else:
            logger.debug(f"  Step 2 (exclusion): no blacklist, kept all {len(included)} databases")
        
        # Step 3: Remove SYSTEM databases (always)
        before_count = len(included)
        included = self.filter_system_databases(included)
        system_removed = before_count - len(included)
        if system_removed > 0:
            logger.debug(f"  Step 3 (system): removed {system_removed} system databases")
        
        logger.info(f"Final databases to backup: {len(included)} of {len(all_databases)} total")
        if included:
            logger.debug(f"  Databases: {', '.join(included)}")
        else:
            logger.warning(f"  No databases matched filters!")
        
        return included
    
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
