"""
PostgreSQL database adapter implementation.

Provides PostgreSQL-specific backup operations using pg_dump
and connection management.
"""

import subprocess
import logging
import os
import time
import select
from typing import Any
from sqlalchemy import text

from python_backup.config.models import DatabaseConfig
from python_backup.db.base import DatabaseAdapter
from python_backup.utils.log_sanitizer import safe_repr

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
        # Use configured database or fallback to postgres
        self._default_db = config.database if config.database else "postgres"
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
    
    def get_server_version(self, database: str = None) -> tuple[int, int]:
        """
        Get PostgreSQL server version.
        
        Args:
            database: Database to connect to (default: from config or postgres)
        
        Returns:
            Tuple of (major, minor) version numbers
        """
        if database is None:
            database = self._default_db
        try:
            # Use psql to query server version
            env = os.environ.copy()
            env['PGPASSWORD'] = self.config.password
            
            # Build psql command
            cmd = [
                "psql",
                "-h", self.config.host,
                "-p", str(self.config.port),
                "-U", self.config.username,
                "-d", database,
                "-t",  # tuples only
                "-c", "SHOW server_version"
            ]
            
            # Add SSL mode if enabled
            if getattr(self.config, 'ssl_enabled', False):
                env['PGSSLMODE'] = 'require'
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=10
            )
            
            if result.returncode == 0:
                version_str = result.stdout.strip().split()[0]  # e.g., "17.7"
                major, minor = map(int, version_str.split('.')[:2])
                logger.debug(f"Server version: {major}.{minor}")
                return (major, minor)
            else:
                logger.warning(f"Could not detect server version: {result.stderr}")
                return (0, 0)
        except Exception as e:
            logger.warning(f"Could not detect server version: {e}")
            return (0, 0)
    
    def get_local_pg_dump_version(self) -> tuple[int, int]:
        """
        Get local pg_dump version.
        
        Returns:
            Tuple of (major, minor) version numbers
        """
        try:
            result = subprocess.run(
                ["pg_dump", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Output: "pg_dump (PostgreSQL) 16.11 ..."
            version_str = result.stdout.split()[2]  # "16.11"
            major, minor = map(int, version_str.split('.')[:2])
            logger.debug(f"Local pg_dump version: {major}.{minor}")
            return (major, minor)
        except Exception as e:
            logger.warning(f"Could not detect local pg_dump version: {e}")
            return (0, 0)
    
    def should_use_docker(self) -> tuple[bool, str]:
        """
        Check if Docker should be used for pg_dump/pg_restore.
        
        Returns:
            Tuple of (should_use_docker, reason)
        """
        server_version = self.get_server_version()
        local_version = self.get_local_pg_dump_version()
        
        if server_version == (0, 0) or local_version == (0, 0):
            return (False, "Could not detect versions")
        
        server_major, _ = server_version
        local_major, _ = local_version
        
        if local_major < server_major:
            return (True, f"Server v{server_major} > local pg_dump v{local_major}")
        
        return (False, f"Local pg_dump v{local_major} >= Server v{server_major}")
    
    def get_docker_backup_command(self, database: str, output_path: str, server_major_version: int) -> str:
        """
        Generate Docker-based pg_dump command for version-independent backup.
        
        Args:
            database: Name of database to backup
            output_path: Path where backup file should be saved
            server_major_version: Major version of PostgreSQL server
            
        Returns:
            Docker command string to run pg_dump
        """
        # Use official PostgreSQL Docker image matching server version
        image = f"postgres:{server_major_version}-alpine"
        
        # Build pg_dump options
        pg_dump_opts = [
            f"--username={self.config.username}",
            f"--host={self.config.host}",
            f"--port={self.config.port}",
            "--clean",
            "--create",
            "--if-exists",
            database
        ]
        
        # Build Docker command
        docker_cmd = [
            "docker", "run", "--rm",
            "-e", f"PGPASSWORD={self.config.password}",
            image,
            "pg_dump"
        ] + pg_dump_opts
        
        command = " ".join(docker_cmd)
        
        # Handle output redirection
        if output_path.endswith(".gz"):
            command = f"{command} | gzip > {output_path}"
        else:
            command = f"{command} > {output_path}"
        
        return command
    
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
            "--no-privileges",  # Don't dump privileges (will be in roles file)
            "--no-owner",  # Don't set ownership (will be handled by roles)
        ]
        
        # Determine format based on output file extension
        if output_path.endswith(".dump") or output_path.endswith(".custom"):
            cmd_parts.append("--format=custom")  # Custom format for better compression
        else:
            cmd_parts.append("--format=plain")  # Plain SQL format
        
        # Add database name
        cmd_parts.append(database)
        
        # Build full command
        command = " ".join(cmd_parts)
        
        # Output redirection (no compression - done separately for better performance)
        if output_path.endswith(".dump") or output_path.endswith(".custom"):
            # Custom format writes directly to file
            command = f"{command} --file={output_path}"
        else:
            # Plain SQL format - remove .gz if present (will be added later)
            sql_file = output_path[:-3] if output_path.endswith('.gz') else output_path
            command = f"{command} > {sql_file}"
        
        logger.debug(f"=== Término Função: get_backup_command (PostgreSQLAdapter) ===")
        return command
    
    def backup_database(self, database: str, output_path: str) -> bool:
        """
        Backup PostgreSQL database using pg_dump.
        
        Automatically detects server version and uses Docker if local pg_dump
        is incompatible (older than server version).
        
        For .gz files, uses 2-step process for better performance:
        1. pg_dump > .sql (fast, no compression overhead)
        2. gzip .sql (optimized compression)
        
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
            # Check if output should be compressed
            needs_compression = output_path.endswith('.gz')
            temp_sql_file = output_path[:-3] if needs_compression else output_path
            
            # Check if Docker should be used
            use_docker, reason = self.should_use_docker()
            
            if use_docker:
                logger.info(f"Using Docker for backup: {reason}")
                server_version = self.get_server_version()  # Uses _default_db from config
                command = self.get_docker_backup_command(database, temp_sql_file, server_version[0])
                env = os.environ.copy()  # Docker handles PGPASSWORD via -e flag
            else:
                logger.info(f"Using local pg_dump: {reason}")
                command = self.get_backup_command(database, temp_sql_file)
                env = os.environ.copy()
                env['PGPASSWORD'] = self.config.password
                # Add SSL mode if enabled
                if getattr(self.config, 'ssl_enabled', False):
                    env['PGSSLMODE'] = 'require'
            
            logger.info(f"[PHASE 1/2] Executing pg_dump for database '{database}'")
            if needs_compression:
                logger.info(f"[PHASE 2/2] Will compress to '{output_path}' after pg_dump completes")
            logger.debug(f"Command: {command.replace(self.config.password, '***')}")
            
            # Step 1: Execute backup command with timeout monitoring
            # Timeout: 12 hours for very large databases
            start_time = time.time()
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True
            )
            
            # Monitor for timeout
            timeout_limit = 43200  # 12 hours
            
            while True:
                # Check if process finished
                retcode = process.poll()
                if retcode is not None:
                    break
                    
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > timeout_limit:
                    process.kill()
                    logger.error(f"[PHASE 1/2] pg_dump TIMEOUT after {elapsed:.0f} seconds (limit: {timeout_limit}s)")
                    logger.debug(f"=== Término Função: backup_database (PostgreSQLAdapter) COM ERRO ===")
                    return False
                
                # Wait before next check
                time.sleep(5)
            
            # Get output
            stdout, stderr = process.communicate()
            elapsed_total = time.time() - start_time
            
            if process.returncode != 0:
                logger.error(f"[PHASE 1/2] pg_dump FAILED: {stderr}")
                logger.debug(f"=== Término Função: backup_database (PostgreSQLAdapter) COM ERRO ===")
                return False
            
            # Check output file size
            final_size = 0
            if os.path.exists(temp_sql_file):
                final_size = os.path.getsize(temp_sql_file)
                size_mb = final_size / (1024 * 1024)
                size_gb = size_mb / 1024
                if size_gb >= 1:
                    logger.info(f"[PHASE 1/2] pg_dump completed - Size: {size_gb:.2f} GB")
                else:
                    logger.info(f"[PHASE 1/2] pg_dump completed - Size: {size_mb:.1f} MB")
            else:
                logger.warning(f"[PHASE 1/2] pg_dump completed but output file not found: {temp_sql_file}")
            
            # Step 2: Compress if needed
            if needs_compression:
                logger.info(f"[PHASE 2/2] Starting gzip compression...")
                
                compress_start = time.time()
                compress_process = subprocess.Popen(
                    f"gzip -f '{temp_sql_file}'",
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Monitor compression timeout
                compress_timeout = 7200  # 2 hours
                
                while True:
                    retcode = compress_process.poll()
                    if retcode is not None:
                        break
                    
                    elapsed = time.time() - compress_start
                    if elapsed > compress_timeout:
                        compress_process.kill()
                        logger.error(f"[PHASE 2/2] gzip TIMEOUT after {elapsed:.0f}s (limit: {compress_timeout}s)")
                        logger.debug(f"=== Término Função: backup_database (PostgreSQLAdapter) COM ERRO ===")
                        return False
                    
                    time.sleep(5)
                
                stdout, stderr = compress_process.communicate()
                
                if compress_process.returncode == 0:
                    if os.path.exists(output_path):
                        compressed_size = os.path.getsize(output_path)
                        ratio = (compressed_size / final_size * 100) if final_size > 0 else 0
                        size_mb = compressed_size / (1024 * 1024)
                        size_gb = size_mb / 1024
                        if size_gb >= 1:
                            logger.info(f"[PHASE 2/2] gzip completed - Size: {size_gb:.2f} GB ({ratio:.1f}%)")
                        else:
                            logger.info(f"[PHASE 2/2] gzip completed - Size: {size_mb:.1f} MB ({ratio:.1f}%)")
                    else:
                        logger.info(f"[PHASE 2/2] gzip completed successfully")
                    logger.debug(f"=== Término Função: backup_database (PostgreSQLAdapter) ===")
                    return True
                else:
                    logger.error(f"[PHASE 2/2] gzip compression FAILED: {stderr}")
                    logger.debug(f"=== Término Função: backup_database (PostgreSQLAdapter) COM ERRO ===")
                    return False
            else:
                logger.debug(f"=== Término Função: backup_database (PostgreSQLAdapter) ===")
                return True
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Backup command failed: {e}")
            logger.debug(f"=== Término Função: backup_database (PostgreSQLAdapter) COM ERRO ===")
            return False
            
        except subprocess.TimeoutExpired as e:
            # Determinar em qual fase ocorreu o timeout
            phase = "pg_dump" if "pg_dump" in command or not needs_compression else "gzip compression"
            logger.error(f"Timeout exceeded during {phase} for database '{database}' (timeout: {e.args[1] if len(e.args) > 1 else 'unknown'}s)")
            logger.debug(f"=== Término Função: backup_database (PostgreSQLAdapter) COM ERRO ===")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error during backup: {e}")
            logger.debug(f"=== Término Função: backup_database (PostgreSQLAdapter) COM ERRO ===")
            return False
    
    def restore_database(self, database: str, backup_file: str) -> bool:
        """
        Restore PostgreSQL database from backup file.
        
        Disaster Recovery Mode:
        - Verifies server connectivity and user privileges
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
        logger.debug(f"=== Função: restore_database (PostgreSQLAdapter) ===")
        logger.debug(f"==> PARAM: database TYPE: {type(database)}, SIZE: {len(database)} chars, CONTENT: {database}")
        logger.debug(f"==> PARAM: backup_file TYPE: {type(backup_file)}, SIZE: {len(backup_file)} chars, CONTENT: {backup_file}")
        
        try:
            logger.info(f"[DISASTER RECOVERY] Starting restore of database '{database}' from '{backup_file}'")
            
            # Set PGPASSWORD environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = self.config.password
            if getattr(self.config, 'ssl_enabled', False):
                env['PGSSLMODE'] = 'require'
            
            # Step 1: Verify server connectivity
            logger.info(f"[STEP 1/4] Verifying PostgreSQL server connectivity...")
            verify_cmd = [
                "psql",
                f"--username={self.config.username}",
                f"--host={self.config.host}",
                f"--port={self.config.port}",
                "--dbname=postgres",
                "-c",
                "SELECT version();"
            ]
            
            verify_result = subprocess.run(
                verify_cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=30
            )
            
            if verify_result.returncode != 0:
                logger.error(f"Cannot connect to PostgreSQL server: {verify_result.stderr}")
                return False
            
            logger.info(f"[STEP 1/4] Connection verified successfully")
            
            # Step 2: Check if database exists, create if not
            logger.info(f"[STEP 2/4] Checking if database '{database}' exists...")
            check_db_cmd = [
                "psql",
                f"--username={self.config.username}",
                f"--host={self.config.host}",
                f"--port={self.config.port}",
                "--dbname=postgres",
                "-tAc",
                f"SELECT 1 FROM pg_database WHERE datname = '{database}';"
            ]
            
            check_result = subprocess.run(
                check_db_cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=30
            )
            
            db_exists = '1' in check_result.stdout
            
            if not db_exists:
                logger.info(f"[STEP 2/4] Database '{database}' does not exist, creating...")
                create_cmd = [
                    "psql",
                    f"--username={self.config.username}",
                    f"--host={self.config.host}",
                    f"--port={self.config.port}",
                    "--dbname=postgres",
                    "-c",
                    f"CREATE DATABASE {database} WITH ENCODING 'UTF8' LC_COLLATE='en_US.UTF-8' LC_CTYPE='en_US.UTF-8' TEMPLATE=template0;"
                ]
                
                create_result = subprocess.run(
                    create_cmd,
                    capture_output=True,
                    text=True,
                    env=env,
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
                "psql",
                f"--username={self.config.username}",
                f"--host={self.config.host}",
                f"--port={self.config.port}",
                "--dbname=postgres",
                "-tAc",
                "SELECT 1 FROM pg_roles WHERE rolname = 'backup';"
            ]
            
            user_result = subprocess.run(
                check_user_cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=30
            )
            
            if '1' not in user_result.stdout:
                logger.info(f"[STEP 3/4] Creating backup user...")
                create_user_cmd = [
                    "psql",
                    f"--username={self.config.username}",
                    f"--host={self.config.host}",
                    f"--port={self.config.port}",
                    "--dbname=postgres",
                    "-c",
                    f"CREATE USER backup WITH PASSWORD 'BackupUser2026!'; GRANT CONNECT ON DATABASE {database} TO backup; GRANT ALL PRIVILEGES ON DATABASE {database} TO backup;"
                ]
                
                user_create_result = subprocess.run(
                    create_user_cmd,
                    capture_output=True,
                    text=True,
                    env=env,
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
