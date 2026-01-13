"""
Backup strategy implementations using the Strategy pattern.

Strategies define different backup approaches (full, incremental, differential).
"""

import logging
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime
from typing import Optional

from vya_backupbd.backup.context import BackupContext
from vya_backupbd.db.mysql import MySQLAdapter
from vya_backupbd.db.postgresql import PostgreSQLAdapter
from vya_backupbd.storage.local import LocalStorage
from vya_backupbd.storage.s3 import S3Storage
from vya_backupbd.utils.compression import compress_file
from vya_backupbd.utils.log_sanitizer import safe_repr

logger = logging.getLogger(__name__)


def get_database_adapter(db_config):
    """Get database adapter based on configuration."""
    logger.debug(f"=== Função: get_database_adapter ===")
    logger.debug(f"==> PARAM: db_config TYPE: {type(db_config)}, CONTENT: {safe_repr(db_config)}")
    
    if db_config.type == "mysql":
        return MySQLAdapter(db_config)
    elif db_config.type == "postgresql":
        return PostgreSQLAdapter(db_config)
    else:
        logger.debug(f"=== Término Função: get_database_adapter ===")
        raise ValueError(f"Unknown database type: {db_config.type}")
    
    logger.debug(f"=== Término Função: get_database_adapter ===")


def get_storage_adapter(storage_config):
    """Get storage adapter based on configuration."""
    logger.debug(f"=== Função: get_storage_adapter ===")
    logger.debug(f"==> PARAM: storage_config TYPE: {type(storage_config)}, CONTENT: {storage_config}")
    
    if storage_config.type == "local":
        return LocalStorage(base_path=storage_config.path)
    elif storage_config.type == "s3":
        return S3Storage(
            bucket=storage_config.bucket,
            region=storage_config.region,
            access_key=storage_config.access_key,
            secret_key=storage_config.secret_key,
            prefix=storage_config.prefix
        )
    else:
        logger.debug(f"=== Término Função: get_storage_adapter ===")
        raise ValueError(f"Unknown storage type: {storage_config.type}")
    
    logger.debug(f"=== Término Função: get_storage_adapter ===")


class BackupStrategy(ABC):
    """Abstract base class for backup strategies."""
    
    @abstractmethod
    def execute(self, context: BackupContext) -> bool:
        """
        Execute the backup strategy.
        
        Args:
            context: BackupContext with configuration and state
            
        Returns:
            True if backup succeeded, False otherwise
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the strategy name."""
        pass


class FullBackupStrategy(BackupStrategy):
    """
    Full backup strategy - complete database dump.
    
    Process:
    1. Create temporary directory
    2. Dump database to file
    3. Compress if configured
    4. Upload to storage
    5. Update context with metadata
    """
    
    def get_name(self) -> str:
        """Get strategy name."""
        return "full"
    
    def execute(self, context: BackupContext) -> bool:
        """
        Execute full backup.
        
        Args:
            context: BackupContext with configuration
            
        Returns:
            True if backup succeeded, False otherwise
        """
        logger.debug(f"=== Função: execute ===")
        logger.debug(f"==> PARAM: context TYPE: {type(context)}, SIZE: {len(str(context))} bytes")
        
        try:
            logger.info(f"Starting full backup for database: {context.database_config.database}")
            
            # Step 1: Create database adapter
            logger.debug(f"Creating adapter for: {safe_repr(context.database_config)}")
            db_adapter = get_database_adapter(context.database_config)
            
            # Step 2: Generate backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dbms = context.database_config.type.lower()
            db_name = context.database_config.database
            filename = f"{timestamp}_{dbms}_{db_name}.sql"
            
            # Step 3: Create SQL directory and dump path
            sql_dir = Path(context.storage_config.path)
            sql_dir.mkdir(parents=True, exist_ok=True)
            dump_file = sql_dir / filename
            
            logger.info(f"Dumping database to: {dump_file}")
            
            # Step 4: Backup grants/users BEFORE database dump
            grants_content = self._backup_grants(db_adapter, context)
            
            # Step 5: Perform database dump
            database_name = context.database_config.database
            success = db_adapter.backup_database(database_name, str(dump_file))
            if not success:
                error_msg = "Database dump failed"
                logger.error(error_msg)
                context.fail(error_msg)
                return False
            
            # Step 6: Prepend grants to SQL file
            if grants_content:
                self._prepend_grants_to_dump(dump_file, grants_content)
            
            # Step 7: Get dump size
            dump_size = dump_file.stat().st_size
            context.set_backup_file(dump_file)
            context.set_backup_size(dump_size)
            
            logger.info(f"Database dumped successfully ({dump_size} bytes)")
            
            # Step 8: Compress if configured
            if context.backup_config.compression:
                compressed_file = self._compress_backup(dump_file, context)
                if compressed_file:
                    compressed_size = compressed_file.stat().st_size
                    context.set_compressed_size(compressed_size)
                    logger.info(f"Compressed to {compressed_size} bytes (ratio: {context.get_compression_ratio():.2f})")
                    context.set_storage_location(str(compressed_file))
                else:
                    logger.warning("Compression failed, keeping SQL file only")
                    context.set_storage_location(str(dump_file))
            else:
                context.set_storage_location(str(dump_file))
            
            # Step 9: Update context
            context.complete()
            
            logger.info(f"Backup completed successfully: {context.storage_location}")
            logger.debug(f"=== Término Função: execute ===")
            return True
            
        except Exception as e:
            error_msg = f"Backup failed with exception: {str(e)}"
            logger.error(error_msg, exc_info=True)
            context.fail(error_msg)
            logger.debug(f"=== Término Função: execute (COM ERRO) ===")
            return False
    
    def _compress_backup(self, dump_file: Path, context: BackupContext) -> Optional[Path]:
        """
        Compress the backup file and save to path_zip.
        
        Args:
            dump_file: Path to the dump file
            context: BackupContext with compression settings
            
        Returns:
            Path to compressed file or None if compression failed
        """
        logger.debug(f"=== Função: _compress_backup ===")
        logger.debug(f"==> PARAM: dump_file TYPE: {type(dump_file)}, CONTENT: {dump_file}")
        logger.debug(f"==> PARAM: context TYPE: {type(context)}, SIZE: {len(str(context))} bytes")
        
        try:
            compression_method = context.backup_config.compression
            
            # Map compression method to proper file extension
            extension_map = {
                'zip': 'zip',
                'gzip': 'gz',
                'bzip2': 'bz2'
            }
            ext = extension_map.get(compression_method, 'zip')
            
            # Get path_zip from config (assuming it's passed somehow or hardcoded)
            # For now, use sibling directory ending in 'zip'
            sql_dir = dump_file.parent
            zip_dir = Path(str(sql_dir).replace('bkpsql', 'bkpzip'))
            zip_dir.mkdir(parents=True, exist_ok=True)
            
            # Replace .sql extension with compression extension
            compressed_filename = dump_file.stem + f".{ext}"
            compressed_file = zip_dir / compressed_filename
            
            logger.info(f"Compressing with {compression_method}: {dump_file}")
            logger.info(f"Output: {compressed_file}")
            
            success = compress_file(
                str(dump_file),
                str(compressed_file),
                method=compression_method
            )
            
            if success:
                logger.debug(f"=== Término Função: _compress_backup ===")
                return compressed_file
            else:
                logger.warning("Compression failed, will upload uncompressed file")
                logger.debug(f"=== Término Função: _compress_backup ===")
                return None
                
        except Exception as e:
            logger.warning(f"Compression failed: {e}, will upload uncompressed file")
            logger.debug(f"=== Término Função: _compress_backup ===")
            return None
    
    def _backup_grants(self, db_adapter, context: BackupContext) -> Optional[str]:
        """
        Backup database grants/users.
        
        Args:
            db_adapter: Database adapter instance
            context: BackupContext
            
        Returns:
            SQL content with grants or None
        """
        logger.debug(f"=== Função: _backup_grants ===")
        logger.debug(f"==> PARAM: db_adapter TYPE: {type(db_adapter)}")
        logger.debug(f"==> PARAM: context TYPE: {type(context)}, SIZE: {len(str(context))} bytes")
        
        try:
            dbms = context.database_config.type.lower()
            db_name = context.database_config.database
            
            logger.info(f"Backing up grants for {dbms}:{db_name}")
            
            if dbms == "mysql":
                return self._backup_mysql_grants(db_adapter, db_name)
            elif dbms == "postgresql":
                return self._backup_postgresql_grants(db_adapter, db_name)
            else:
                logger.warning(f"Grant backup not implemented for {dbms}")
                logger.debug(f"=== Término Função: _backup_grants ===")
                return None
                
        except Exception as e:
            logger.warning(f"Failed to backup grants: {e}")
            logger.debug(f"=== Término Função: _backup_grants ===")
            return None
    
    def _backup_mysql_grants(self, db_adapter, db_name: str) -> str:
        """Backup MySQL grants for database users."""
        logger.debug(f"=== Função: _backup_mysql_grants ===")
        logger.debug(f"==> PARAM: db_adapter TYPE: {type(db_adapter)}")
        logger.debug(f"==> PARAM: db_name TYPE: {type(db_name)}, SIZE: {len(db_name)} chars, CONTENT: {db_name}")
        
        try:
            connection = db_adapter.engine.raw_connection()
            cursor = connection.cursor()
            
            # Get all users with privileges on this database
            cursor.execute(f"""
                SELECT DISTINCT User, Host 
                FROM mysql.db 
                WHERE Db = '{db_name}' OR Db = '%'
                ORDER BY User, Host
            """)
            users = cursor.fetchall()
            
            grants_sql = ["-- ============================================"]
            grants_sql.append(f"-- GRANTS BACKUP FOR DATABASE: {db_name}")
            grants_sql.append("-- ============================================\n")
            
            # Add CREATE DATABASE IF NOT EXISTS
            grants_sql.append(f"-- Create database if not exists")
            grants_sql.append(f"CREATE DATABASE IF NOT EXISTS `{db_name}`;")
            grants_sql.append(f"USE `{db_name}`;\n")
            
            for user, host in users:
                if not user:
                    continue
                    
                try:
                    # Get user authentication info
                    cursor.execute(f"""
                        SELECT plugin, authentication_string 
                        FROM mysql.user 
                        WHERE User = '{user}' AND Host = '{host}'
                    """)
                    user_info = cursor.fetchone()
                    
                    # Create user if not exists
                    grants_sql.append(f"-- User: {user}@{host}")
                    if user_info:
                        plugin, auth_string = user_info
                        if plugin == 'mysql_native_password' and auth_string:
                            grants_sql.append(f"CREATE USER IF NOT EXISTS '{user}'@'{host}' IDENTIFIED WITH mysql_native_password AS '{auth_string}';")
                        elif plugin == 'caching_sha2_password' and auth_string:
                            grants_sql.append(f"CREATE USER IF NOT EXISTS '{user}'@'{host}' IDENTIFIED WITH caching_sha2_password AS '{auth_string}';")
                        else:
                            grants_sql.append(f"CREATE USER IF NOT EXISTS '{user}'@'{host}';")
                    else:
                        grants_sql.append(f"CREATE USER IF NOT EXISTS '{user}'@'{host}';")
                    
                    # Get and add grants
                    cursor.execute(f"SHOW GRANTS FOR '{user}'@'{host}'")
                    grants = cursor.fetchall()
                    
                    for grant in grants:
                        grants_sql.append(grant[0] + ";")
                    grants_sql.append("")
                    
                except Exception as e:
                    logger.debug(f"Could not get grants for {user}@{host}: {e}")
                    continue
            
            grants_sql.append("FLUSH PRIVILEGES;\n")
            
            cursor.close()
            connection.close()
            
            result = "\n".join(grants_sql) + "\n\n"
            logger.debug(f"=== Término Função: _backup_mysql_grants ===")
            return result
            
        except Exception as e:
            logger.warning(f"MySQL grants backup failed: {e}")
            logger.debug(f"=== Término Função: _backup_mysql_grants ===")
            return None
    
    def _backup_postgresql_grants(self, db_adapter, db_name: str) -> str:
        """Backup PostgreSQL grants for database."""
        logger.debug(f"=== Função: _backup_postgresql_grants ===")
        logger.debug(f"==> PARAM: db_adapter TYPE: {type(db_adapter)}")
        logger.debug(f"==> PARAM: db_name TYPE: {type(db_name)}, SIZE: {len(db_name)} chars, CONTENT: {db_name}")
        
        try:
            connection = db_adapter.engine.raw_connection()
            cursor = connection.cursor()
            
            grants_sql = ["-- ============================================"]
            grants_sql.append(f"-- GRANTS BACKUP FOR DATABASE: {db_name}")
            grants_sql.append("-- ============================================\n")
            
            # Create database if not exists
            grants_sql.append(f"-- Create database if not exists")
            grants_sql.append(f"SELECT 'CREATE DATABASE {db_name}' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '{db_name}')\\gexec")
            grants_sql.append(f"\\c {db_name}\n")
            
            # Get roles with access
            cursor.execute("""
                SELECT r.rolname, r.rolsuper, r.rolinherit,
                       r.rolcreaterole, r.rolcreatedb, r.rolcanlogin,
                       r.rolpassword
                FROM pg_roles r
                LEFT JOIN pg_shadow s ON r.rolname = s.usename
                WHERE r.rolname NOT LIKE 'pg_%'
                  AND r.rolname != 'postgres'
                ORDER BY r.rolname
            """)
            roles = cursor.fetchall()
            
            grants_sql.append("-- Create roles if not exist")
            for role in roles:
                rolname = role[0]
                superuser, inherit, createrole, createdb, canlogin = role[1:6]
                
                attrs = []
                if superuser:
                    attrs.append("SUPERUSER")
                else:
                    attrs.append("NOSUPERUSER")
                if createrole:
                    attrs.append("CREATEROLE")
                else:
                    attrs.append("NOCREATEROLE")
                if createdb:
                    attrs.append("CREATEDB")
                else:
                    attrs.append("NOCREATEDB")
                if canlogin:
                    attrs.append("LOGIN")
                else:
                    attrs.append("NOLOGIN")
                if inherit:
                    attrs.append("INHERIT")
                else:
                    attrs.append("NOINHERIT")
                
                grants_sql.append(f"DO $$")
                grants_sql.append(f"BEGIN")
                grants_sql.append(f"  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{rolname}') THEN")
                grants_sql.append(f"    CREATE ROLE {rolname} WITH {' '.join(attrs)};")
                grants_sql.append(f"  END IF;")
                grants_sql.append(f"END $$;")
            
            grants_sql.append("")
            
            # Get database privileges
            cursor.execute(f"""
                SELECT grantee, privilege_type
                FROM information_schema.table_privileges
                WHERE table_catalog = '{db_name}'
                  AND grantee NOT LIKE 'pg_%'
                  AND grantee != 'postgres'
                GROUP BY grantee, privilege_type
            """)
            privileges = cursor.fetchall()
            
            if privileges:
                grants_sql.append("-- Grant privileges")
                for grantee, priv_type in privileges:
                    grants_sql.append(f"GRANT {priv_type} ON ALL TABLES IN SCHEMA public TO {grantee};")
            
            grants_sql.append("")
            
            cursor.close()
            connection.close()
            
            result = "\n".join(grants_sql) + "\n\n"
            logger.debug(f"=== Término Função: _backup_postgresql_grants ===")
            return result
            
        except Exception as e:
            logger.warning(f"PostgreSQL grants backup failed: {e}")
            logger.debug(f"=== Término Função: _backup_postgresql_grants ===")
            return None
    
    def _prepend_grants_to_dump(self, dump_file: Path, grants_content: str):
        """Prepend grants content to the beginning of dump file."""
        logger.debug(f"=== Função: _prepend_grants_to_dump ===")
        logger.debug(f"==> PARAM: dump_file TYPE: {type(dump_file)}, CONTENT: {dump_file}")
        logger.debug(f"==> PARAM: grants_content TYPE: {type(grants_content)}, SIZE: {len(grants_content)} chars")
        
        try:
            # Read existing content
            with open(dump_file, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Write grants + original content
            with open(dump_file, 'w', encoding='utf-8') as f:
                f.write(grants_content)
                f.write(original_content)
            
            logger.info("Grants prepended to dump file")
            logger.debug(f"=== Término Função: _prepend_grants_to_dump ===")
            
        except Exception as e:
            logger.warning(f"Failed to prepend grants: {e}")
            logger.debug(f"=== Término Função: _prepend_grants_to_dump ===")


class BackupStrategyFactory:
    """Factory for creating backup strategies."""
    
    _strategies = {
        "full": FullBackupStrategy,
    }
    
    @classmethod
    def create(cls, strategy_name: str) -> BackupStrategy:
        """
        Create a backup strategy by name.
        
        Args:
            strategy_name: Name of the strategy (case-insensitive)
            
        Returns:
            BackupStrategy instance
            
        Raises:
            ValueError: If strategy name is unknown
        """
        logger.debug(f"=== Função: create ===")
        logger.debug(f"==> PARAM: strategy_name TYPE: {type(strategy_name)}, CONTENT: {strategy_name}")
        
        if not strategy_name:
            raise ValueError("Strategy name cannot be empty or None")
        
        strategy_name_lower = strategy_name.lower()
        
        if strategy_name_lower not in cls._strategies:
            available = ", ".join(cls._strategies.keys())
            raise ValueError(
                f"Unknown backup strategy: {strategy_name}. "
                f"Available strategies: {available}"
            )
        
        strategy_class = cls._strategies[strategy_name_lower]
        result = strategy_class()
        logger.debug(f"=== Término Função: create ===")
        return result
    
    @classmethod
    def get_available_strategies(cls) -> list:
        """Get list of available strategy names."""
        return list(cls._strategies.keys())
    
    @classmethod
    def is_available(cls, strategy_name: str) -> bool:
        """Check if a strategy is available."""
        if not strategy_name:
            return False
        return strategy_name.lower() in cls._strategies
