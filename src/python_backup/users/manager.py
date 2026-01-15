"""
UsersManager - Manages user and role backup/restore operations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional
import json
import gzip


class DatabaseType(Enum):
    """Supported database types for user backup."""
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"


@dataclass
class UserInfo:
    """Information about a database user or role."""
    username: str
    host: str = "%"
    privileges: List[str] = field(default_factory=list)
    password_hash: Optional[str] = None
    attributes: dict = field(default_factory=dict)


@dataclass
class UserBackupMetadata:
    """Metadata for a user backup operation."""
    backup_timestamp: datetime
    database_type: DatabaseType
    instance_name: str
    total_users: int
    users: List[UserInfo]
    backup_file_path: str = ""
    compressed: bool = True
    backup_size_bytes: int = 0
    
    def to_dict(self) -> dict:
        """Convert metadata to dictionary."""
        return {
            'backup_timestamp': self.backup_timestamp.isoformat(),
            'database_type': self.database_type.value,
            'instance_name': self.instance_name,
            'total_users': self.total_users,
            'users': [
                {
                    'username': u.username,
                    'host': u.host,
                    'privileges': u.privileges,
                    'password_hash': u.password_hash,
                    'attributes': u.attributes
                }
                for u in self.users
            ],
            'backup_file_path': self.backup_file_path,
            'compressed': self.compressed,
            'backup_size_bytes': self.backup_size_bytes
        }


class UsersManager:
    """
    Manages user and role backup/restore operations.
    
    Supports:
    - MySQL: SHOW GRANTS extraction
    - PostgreSQL: pg_dumpall --roles-only
    """
    
    def __init__(
        self,
        database_type: DatabaseType,
        host: str,
        port: int,
        admin_user: str,
        admin_password: str
    ):
        """
        Initialize UsersManager.
        
        Args:
            database_type: Type of database (MySQL or PostgreSQL)
            host: Database host
            port: Database port
            admin_user: Admin username for connection
            admin_password: Admin password
        """
        if not isinstance(database_type, DatabaseType):
            raise ValueError(f"Unsupported database type: {database_type}")
        
        self.database_type = database_type
        self.host = host
        self.port = port
        self.admin_user = admin_user
        self.admin_password = admin_password
    
    def backup_users(
        self,
        output_path: Path,
        exclude_system_users: bool = True,
        compress: bool = True
    ) -> UserBackupMetadata:
        """
        Backup all users and their privileges.
        
        Args:
            output_path: Path where backup file will be saved
            exclude_system_users: Whether to exclude system users
            compress: Whether to compress the backup file
        
        Returns:
            UserBackupMetadata with backup information
        """
        if self.database_type == DatabaseType.MYSQL:
            return self._backup_mysql_users(output_path, exclude_system_users, compress)
        elif self.database_type == DatabaseType.POSTGRESQL:
            return self._backup_postgresql_roles(output_path, exclude_system_users, compress)
        else:
            raise ValueError(f"Unsupported database type: {self.database_type}")
    
    def restore_users(
        self,
        backup_file: Path,
        specific_user: Optional[str] = None,
        skip_existing: bool = False
    ) -> int:
        """
        Restore users from backup file.
        
        Args:
            backup_file: Path to backup file
            specific_user: Optional specific user to restore
            skip_existing: Whether to skip existing users
        
        Returns:
            Number of users restored
        """
        if self.database_type == DatabaseType.MYSQL:
            return self._restore_mysql_users(backup_file, specific_user, skip_existing)
        elif self.database_type == DatabaseType.POSTGRESQL:
            return self._restore_postgresql_roles(backup_file, specific_user, skip_existing)
        else:
            raise ValueError(f"Unsupported database type: {self.database_type}")
    
    def list_users(self, backup_file: Path) -> List[UserInfo]:
        """
        List users from a backup file without restoring.
        
        Args:
            backup_file: Path to backup file
        
        Returns:
            List of UserInfo objects
        """
        metadata = self._read_metadata(backup_file)
        return metadata.users
    
    def validate_backup_file(self, backup_file: Path) -> bool:
        """
        Validate a backup file structure.
        
        Args:
            backup_file: Path to backup file
        
        Returns:
            True if valid, False otherwise
        """
        try:
            metadata = self._read_metadata(backup_file)
            return (
                metadata.database_type == self.database_type and
                metadata.total_users > 0 and
                Path(backup_file).exists()
            )
        except Exception:
            return False
    
    def _backup_mysql_users(
        self,
        output_path: Path,
        exclude_system: bool,
        compress: bool
    ) -> UserBackupMetadata:
        """Backup MySQL users using SHOW GRANTS."""
        import pymysql
        
        SYSTEM_USERS = ['root', 'mysql.sys', 'mysql.session', 'mysql.infoschema']
        
        # Connect to MySQL
        connection = pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.admin_user,
            password=self.admin_password,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        try:
            users_info = []
            grants_sql = [f"-- MySQL User Backup\n-- Generated: {datetime.now().isoformat()}\n"]
            
            # Get all users
            with connection.cursor() as cursor:
                cursor.execute("SELECT User, Host FROM mysql.user ORDER BY User, Host")
                users = cursor.fetchall()
            
            # Get grants for each user
            for user_row in users:
                username = user_row['User']
                host = user_row['Host']
                
                if exclude_system and username in SYSTEM_USERS:
                    continue
                if not username:
                    continue
                
                try:
                    with connection.cursor() as cursor:
                        cursor.execute(f"SHOW GRANTS FOR '{username}'@'{host}'")
                        grants = cursor.fetchall()
                    
                    privileges = []
                    for grant in grants:
                        grant_stmt = list(grant.values())[0]
                        grants_sql.append(f"{grant_stmt};")
                        if 'GRANT' in grant_stmt:
                            privs = grant_stmt.split('GRANT ')[1].split(' ON')[0]
                            privileges.append(privs.strip())
                    
                    users_info.append(UserInfo(username=username, host=host, privileges=privileges))
                except Exception:
                    continue
            
            # Write backup
            backup_content = "\n".join(grants_sql)
            if compress:
                with gzip.open(output_path, 'wt', encoding='utf-8') as f:
                    f.write(backup_content)
            else:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(backup_content)
            
            metadata = UserBackupMetadata(
                backup_timestamp=datetime.now(),
                database_type=DatabaseType.MYSQL,
                instance_name=f"{self.host}:{self.port}",
                total_users=len(users_info),
                users=users_info,
                backup_file_path=str(output_path),
                compressed=compress,
                backup_size_bytes=output_path.stat().st_size
            )
            
            self._write_metadata(metadata, output_path)
            return metadata
        finally:
            connection.close()
    
    def _backup_postgresql_roles(
        self,
        output_path: Path,
        exclude_system: bool,
        compress: bool
    ) -> UserBackupMetadata:
        """Backup PostgreSQL roles using pg_dumpall --roles-only."""
        import subprocess
        import psycopg
        
        SYSTEM_ROLES = ['postgres', 'pg_monitor', 'pg_read_all_settings', 'pg_read_all_stats']
        
        # Use pg_dumpall to dump roles
        env = {'PGPASSWORD': self.admin_password}
        cmd = [
            'pg_dumpall',
            '-h', self.host,
            '-p', str(self.port),
            '-U', self.admin_user,
            '--roles-only',
            '--no-role-passwords'  # Skip passwords for security
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, env={**env, 'PGCLIENTENCODING': 'UTF8'})
        if result.returncode != 0:
            # Try alternative method using psycopg if pg_dumpall fails
            return self._backup_postgresql_roles_native(output_path, exclude_system, compress)
        
        backup_content = result.stdout
        
        # Get role list for metadata
        connection = psycopg.connect(
            host=self.host,
            port=self.port,
            user=self.admin_user,
            password=self.admin_password,
            dbname='postgres'
        )
        
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT rolname FROM pg_roles ORDER BY rolname")
                roles = cursor.fetchall()
            
            users_info = []
            for role in roles:
                rolname = role[0]
                if exclude_system and rolname in SYSTEM_ROLES:
                    continue
                users_info.append(UserInfo(username=rolname, host='', privileges=[]))
        finally:
            connection.close()
        
        # Write backup
        if compress:
            with gzip.open(output_path, 'wt', encoding='utf-8') as f:
                f.write(backup_content)
        else:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(backup_content)
        
        metadata = UserBackupMetadata(
            backup_timestamp=datetime.now(),
            database_type=DatabaseType.POSTGRESQL,
            instance_name=f"{self.host}:{self.port}",
            total_users=len(users_info),
            users=users_info,
            backup_file_path=str(output_path),
            compressed=compress,
            backup_size_bytes=output_path.stat().st_size
        )
        
        self._write_metadata(metadata, output_path)
        return metadata
    
    def _backup_postgresql_roles_native(
        self,
        output_path: Path,
        exclude_system: bool,
        compress: bool
    ) -> UserBackupMetadata:
        """Backup PostgreSQL roles using native psycopg queries (fallback method)."""
        import psycopg
        
        SYSTEM_ROLES = ['postgres', 'pg_monitor', 'pg_read_all_settings', 'pg_read_all_stats']
        
        connection = psycopg.connect(
            host=self.host,
            port=self.port,
            user=self.admin_user,
            password=self.admin_password,
            dbname='postgres'
        )
        
        try:
            users_info = []
            roles_sql = [f"-- PostgreSQL Roles Backup\n-- Generated: {datetime.now().isoformat()}\n\n"]
            
            with connection.cursor() as cursor:
                # Get all roles with attributes
                cursor.execute("""
                    SELECT rolname, rolsuper, rolinherit, rolcreaterole, rolcreatedb, 
                           rolcanlogin, rolreplication, rolbypassrls
                    FROM pg_roles 
                    ORDER BY rolname
                """)
                roles = cursor.fetchall()
                
                for role in roles:
                    rolname = role[0]
                    if exclude_system and rolname in SYSTEM_ROLES:
                        continue
                    
                    # Build CREATE ROLE statement
                    attrs = []
                    if role[1]: attrs.append('SUPERUSER')
                    if role[2]: attrs.append('INHERIT')
                    if role[3]: attrs.append('CREATEROLE')
                    if role[4]: attrs.append('CREATEDB')
                    if role[5]: attrs.append('LOGIN')
                    else: attrs.append('NOLOGIN')
                    if role[6]: attrs.append('REPLICATION')
                    if role[7]: attrs.append('BYPASSRLS')
                    
                    roles_sql.append(f"CREATE ROLE {rolname} {' '.join(attrs)};")
                    users_info.append(UserInfo(username=rolname, host='', privileges=attrs))
            
            backup_content = "\n".join(roles_sql)
            
            if compress:
                with gzip.open(output_path, 'wt', encoding='utf-8') as f:
                    f.write(backup_content)
            else:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(backup_content)
            
            metadata = UserBackupMetadata(
                backup_timestamp=datetime.now(),
                database_type=DatabaseType.POSTGRESQL,
                instance_name=f"{self.host}:{self.port}",
                total_users=len(users_info),
                users=users_info,
                backup_file_path=str(output_path),
                compressed=compress,
                backup_size_bytes=output_path.stat().st_size
            )
            
            self._write_metadata(metadata, output_path)
            return metadata
        finally:
            connection.close()
    
    def _restore_mysql_users(
        self,
        backup_file: Path,
        specific_user: Optional[str],
        skip_existing: bool
    ) -> int:
        """Restore MySQL users from backup."""
        # To be implemented
        raise NotImplementedError("MySQL user restore not yet implemented")
    
    def _restore_postgresql_roles(
        self,
        backup_file: Path,
        specific_user: Optional[str],
        skip_existing: bool
    ) -> int:
        """Restore PostgreSQL roles from backup."""
        # To be implemented
        raise NotImplementedError("PostgreSQL role restore not yet implemented")
    
    def _read_metadata(self, backup_file: Path) -> UserBackupMetadata:
        """Read metadata from backup file."""
        metadata_file = backup_file.parent / f"{backup_file.stem}.metadata.json"
        
        if not metadata_file.exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_file}")
        
        with open(metadata_file, 'r') as f:
            data = json.load(f)
        
        return UserBackupMetadata(
            backup_timestamp=datetime.fromisoformat(data['backup_timestamp']),
            database_type=DatabaseType(data['database_type']),
            instance_name=data.get('instance_name', ''),
            total_users=data['total_users'],
            users=[UserInfo(**u) for u in data['users']],
            backup_file_path=data['backup_file_path'],
            compressed=data.get('compressed', True),
            backup_size_bytes=data.get('backup_size_bytes', 0)
        )
    
    def _write_metadata(self, metadata: UserBackupMetadata, output_path: Path) -> None:
        """Write metadata to JSON file."""
        metadata_file = output_path.parent / f"{output_path.stem}.metadata.json"
        
        data = {
            'database_type': metadata.database_type.value,
            'backup_timestamp': metadata.backup_timestamp.isoformat(),
            'total_users': metadata.total_users,
            'users': [
                {
                    'username': u.username,
                    'host': u.host,
                    'privileges': u.privileges,
                    'password_hash': u.password_hash,
                    'attributes': u.attributes
                }
                for u in metadata.users
            ],
            'backup_file_path': metadata.backup_file_path,
            'compressed': metadata.compressed,
            'backup_size_bytes': metadata.backup_size_bytes
        }
        
        with open(metadata_file, 'w') as f:
            json.dump(data, f, indent=2)
