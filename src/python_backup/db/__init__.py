"""
Database abstraction layer.

Provides adapters for MySQL, PostgreSQL and Files backup with
connection management, backup operations, and query execution.
"""

from python_backup.db.base import DatabaseAdapter
from python_backup.db.engine import create_db_engine, get_connection_string
from python_backup.db.mysql import MySQLAdapter
from python_backup.db.postgresql import PostgreSQLAdapter
from python_backup.db.files import FilesAdapter

__all__ = [
    "DatabaseAdapter",
    "MySQLAdapter",
    "PostgreSQLAdapter",
    "FilesAdapter",
    "create_db_engine",
    "get_connection_string",
]
