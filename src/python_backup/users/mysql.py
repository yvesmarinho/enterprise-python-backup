"""
MySQL user backup implementation using SHOW GRANTS.
"""

import pymysql
from pathlib import Path
from datetime import datetime
from typing import List, Tuple
import gzip
from ..manager import UserInfo, UserBackupMetadata, DatabaseType


class MySQLUserBackup:
    """Handles MySQL user backup operations."""
    
    SYSTEM_USERS = [
        'root', 'mysql.sys', 'mysql.session', 'mysql.infoschema',
        'debian-sys-maint', 'phpmyadmin', 'pma'
    ]
    
    def __init__(self, host: str, port: int, user: str, password: str):
        """Initialize MySQL connection parameters."""
        self.host = host
        self.port = port
        self.user = user
        self.password = password
    
    def backup_users(
        self,
        output_path: Path,
        exclude_system: bool = True,
        compress: bool = True
    ) -> UserBackupMetadata:
        """
        Backup all MySQL users using SHOW GRANTS.
        
        Args:
            output_path: Where to save the backup
            exclude_system: Whether to exclude system users
            compress: Whether to compress the output
        
        Returns:
            UserBackupMetadata with backup information
        """
        # Connect to MySQL
        connection = pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            cursorclass=pymysql.cursors.DictCursor
        )
        
        try:
            users_info = []
            grants_sql = []
            
            # Get all users
            with connection.cursor() as cursor:
                cursor.execute("SELECT User, Host FROM mysql.user ORDER BY User, Host")
                users = cursor.fetchall()
            
            # Get grants for each user
            for user_row in users:
                username = user_row['User']
                host = user_row['Host']
                
                # Skip system users if requested
                if exclude_system and username in self.SYSTEM_USERS:
                    continue
                
                # Skip empty usernames
                if not username:
                    continue
                
                try:
                    # Get grants for this user
                    with connection.cursor() as cursor:
                        cursor.execute(f"SHOW GRANTS FOR '{username}'@'{host}'")
                        grants = cursor.fetchall()
                    
                    # Extract privileges
                    privileges = []
                    user_grants = []
                    
                    for grant in grants:
                        grant_stmt = list(grant.values())[0]
                        user_grants.append(grant_stmt)
                        
                        # Parse privileges from GRANT statement
                        if 'GRANT' in grant_stmt:
                            privs = grant_stmt.split('GRANT ')[1].split(' ON')[0]
                            privileges.append(privs.strip())
                    
                    # Create UserInfo
                    user_info = UserInfo(
                        username=username,
                        host=host,
                        privileges=privileges
                    )
                    users_info.append(user_info)
                    
                    # Add grants to SQL
                    grants_sql.append(f"\n-- User: {username}@{host}")
                    grants_sql.extend(user_grants)
                    grants_sql.append("")
                
                except pymysql.err.OperationalError as e:
                    # Skip users we can't get grants for
                    print(f"Warning: Could not get grants for {username}@{host}: {e}")
                    continue
            
            # Write backup file
            backup_content = self._generate_backup_header() + "\n".join(grants_sql)
            
            if compress:
                with gzip.open(output_path, 'wt', encoding='utf-8') as f:
                    f.write(backup_content)
            else:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(backup_content)
            
            # Get file size
            file_size = output_path.stat().st_size
            
            # Create metadata
            metadata = UserBackupMetadata(
                backup_timestamp=datetime.now(),
                database_type=DatabaseType.MYSQL,
                instance_name=f"{self.host}:{self.port}",
                total_users=len(users_info),
                users=users_info,
                backup_file_path=str(output_path),
                compressed=compress,
                backup_size_bytes=file_size
            )
            
            return metadata
            
        finally:
            connection.close()
    
    def _generate_backup_header(self) -> str:
        """Generate SQL header for backup file."""
        return f"""-- MySQL User Backup
-- Generated: {datetime.now().isoformat()}
-- Host: {self.host}:{self.port}
-- 
-- To restore: mysql -u root -p < backup.sql
--

"""
