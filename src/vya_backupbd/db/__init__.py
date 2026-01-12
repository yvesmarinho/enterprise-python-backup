"""
Database abstraction layer.

Provides adapters for MySQL and PostgreSQL databases with
connection management, backup operations, and query execution.
"""

from vya_backupbd.db.base import DatabaseAdapter
from vya_backupbd.db.engine import create_db_engine, get_connection_string
from vya_backupbd.db.mysql import MySQLAdapter
from vya_backupbd.db.postgresql import PostgreSQLAdapter

__all__ = [
    "DatabaseAdapter",
    "MySQLAdapter",
    "PostgreSQLAdapter",
    "create_db_engine",
    "get_connection_string",
]
