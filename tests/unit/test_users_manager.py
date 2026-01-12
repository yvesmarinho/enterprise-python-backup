"""
Tests for UsersManager - User and role backup/restore management.
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from vya_backupbd.users.manager import (
    UsersManager,
    UserBackupMetadata,
    UserInfo,
    DatabaseType
)


class TestUserInfo:
    """Tests for UserInfo dataclass."""
    
    def test_create_user_info(self):
        """Test creating a UserInfo instance."""
        user = UserInfo(
            username="testuser",
            host="localhost",
            privileges=["SELECT", "INSERT"]
        )
        
        assert user.username == "testuser"
        assert user.host == "localhost"
        assert user.privileges == ["SELECT", "INSERT"]
    
    def test_user_info_with_password_hash(self):
        """Test UserInfo with password hash."""
        user = UserInfo(
            username="app_user",
            host="%",
            privileges=["ALL PRIVILEGES"],
            password_hash="*2470C0C06DEE42FD1618BB99005ADCA2EC9D1E19"
        )
        
        assert user.password_hash is not None
        assert user.username == "app_user"


class TestUserBackupMetadata:
    """Tests for UserBackupMetadata dataclass."""
    
    def test_create_metadata(self):
        """Test creating backup metadata."""
        users = [
            UserInfo("user1", "localhost", ["SELECT"]),
            UserInfo("user2", "%", ["ALL PRIVILEGES"])
        ]
        
        metadata = UserBackupMetadata(
            backup_timestamp=datetime.now(),
            database_type=DatabaseType.MYSQL,
            instance_name="prod-mysql-01",
            total_users=2,
            users=users
        )
        
        assert metadata.total_users == 2
        assert len(metadata.users) == 2
        assert metadata.database_type == DatabaseType.MYSQL
    
    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        users = [UserInfo("testuser", "localhost", ["SELECT"])]
        metadata = UserBackupMetadata(
            backup_timestamp=datetime.now(),
            database_type=DatabaseType.POSTGRESQL,
            instance_name="prod-pg-01",
            total_users=1,
            users=users
        )
        
        data = metadata.to_dict()
        assert isinstance(data, dict)
        assert data["total_users"] == 1
        assert data["database_type"] == "postgresql"
        assert len(data["users"]) == 1


class TestUsersManager:
    """Tests for UsersManager class."""
    
    def test_create_users_manager(self):
        """Test creating UsersManager instance."""
        manager = UsersManager(
            database_type=DatabaseType.MYSQL,
            host="localhost",
            port=3306,
            admin_user="root",
            admin_password="password"
        )
        
        assert manager.database_type == DatabaseType.MYSQL
        assert manager.host == "localhost"
        assert manager.port == 3306
    
    def test_invalid_database_type(self):
        """Test creating manager with invalid database type."""
        with pytest.raises(ValueError, match="Unsupported database type"):
            UsersManager(
                database_type="invalid",
                host="localhost",
                port=3306,
                admin_user="root",
                admin_password="password"
            )
    
    def test_backup_users_mysql(self):
        """Test backing up MySQL users."""
        manager = UsersManager(
            database_type=DatabaseType.MYSQL,
            host="localhost",
            port=3306,
            admin_user="root",
            admin_password="password"
        )
        
        with patch.object(manager, '_backup_mysql_users') as mock_backup:
            mock_backup.return_value = (True, Path("/tmp/backup.sql.gz"))
            
            success, backup_file = manager.backup_users(
                output_dir=Path("/tmp"),
                exclude_users=["root", "mysql.sys"]
            )
            
            assert success is True
            assert backup_file.suffix == ".gz"
            mock_backup.assert_called_once()
    
    def test_backup_users_postgresql(self):
        """Test backing up PostgreSQL users."""
        manager = UsersManager(
            database_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            admin_user="postgres",
            admin_password="password"
        )
        
        with patch.object(manager, '_backup_postgresql_roles') as mock_backup:
            mock_backup.return_value = (True, Path("/tmp/backup.sql.gz"))
            
            success, backup_file = manager.backup_users(
                output_dir=Path("/tmp"),
                exclude_users=["postgres"]
            )
            
            assert success is True
            mock_backup.assert_called_once()
    
    def test_list_users_from_backup(self):
        """Test listing users from backup file."""
        manager = UsersManager(
            database_type=DatabaseType.MYSQL,
            host="localhost",
            port=3306,
            admin_user="root",
            admin_password="password"
        )
        
        with patch.object(manager, '_extract_users_from_backup') as mock_extract:
            mock_users = [
                UserInfo("user1", "localhost", ["SELECT"]),
                UserInfo("user2", "%", ["ALL PRIVILEGES"])
            ]
            mock_extract.return_value = mock_users
            
            users = manager.list_users(backup_file=Path("/tmp/backup.sql.gz"))
            
            assert len(users) == 2
            assert users[0].username == "user1"
            assert users[1].username == "user2"
    
    def test_restore_all_users(self):
        """Test restoring all users from backup."""
        manager = UsersManager(
            database_type=DatabaseType.MYSQL,
            host="localhost",
            port=3306,
            admin_user="root",
            admin_password="password"
        )
        
        with patch.object(manager, '_restore_mysql_users') as mock_restore:
            mock_restore.return_value = (True, 5, 0)
            
            success, created, skipped = manager.restore_users(
                backup_file=Path("/tmp/backup.sql.gz"),
                restore_all=True
            )
            
            assert success is True
            assert created == 5
            assert skipped == 0
    
    def test_restore_single_user(self):
        """Test restoring a single user from backup."""
        manager = UsersManager(
            database_type=DatabaseType.MYSQL,
            host="localhost",
            port=3306,
            admin_user="root",
            admin_password="password"
        )
        
        with patch.object(manager, '_restore_single_user') as mock_restore:
            mock_restore.return_value = True
            
            success, created, skipped = manager.restore_users(
                backup_file=Path("/tmp/backup.sql.gz"),
                restore_all=False,
                username="testuser"
            )
            
            assert success is True
            mock_restore.assert_called_once_with(
                Path("/tmp/backup.sql.gz"),
                "testuser",
                skip_existing=False
            )
    
    def test_restore_with_skip_existing(self):
        """Test restoring users with skip_existing option."""
        manager = UsersManager(
            database_type=DatabaseType.POSTGRESQL,
            host="localhost",
            port=5432,
            admin_user="postgres",
            admin_password="password"
        )
        
        with patch.object(manager, '_restore_postgresql_roles') as mock_restore:
            mock_restore.return_value = (True, 3, 2)
            
            success, created, skipped = manager.restore_users(
                backup_file=Path("/tmp/backup.sql.gz"),
                restore_all=True,
                skip_existing=True
            )
            
            assert success is True
            assert created == 3
            assert skipped == 2
    
    def test_validate_backup_file(self):
        """Test validating backup file."""
        manager = UsersManager(
            database_type=DatabaseType.MYSQL,
            host="localhost",
            port=3306,
            admin_user="root",
            admin_password="password"
        )
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('pathlib.Path.is_file', return_value=True):
                is_valid = manager.validate_backup_file(Path("/tmp/backup.sql.gz"))
                assert is_valid is True
    
    def test_validate_nonexistent_backup_file(self):
        """Test validating non-existent backup file."""
        manager = UsersManager(
            database_type=DatabaseType.MYSQL,
            host="localhost",
            port=3306,
            admin_user="root",
            admin_password="password"
        )
        
        with patch('pathlib.Path.exists', return_value=False):
            is_valid = manager.validate_backup_file(Path("/tmp/nonexistent.sql.gz"))
            assert is_valid is False
    
    def test_get_backup_metadata(self):
        """Test getting backup metadata."""
        manager = UsersManager(
            database_type=DatabaseType.MYSQL,
            host="localhost",
            port=3306,
            admin_user="root",
            admin_password="password"
        )
        
        with patch.object(manager, '_read_metadata_file') as mock_read:
            mock_metadata = UserBackupMetadata(
                backup_timestamp=datetime.now(),
                database_type=DatabaseType.MYSQL,
                instance_name="prod-mysql-01",
                total_users=5,
                users=[]
            )
            mock_read.return_value = mock_metadata
            
            metadata = manager.get_backup_metadata(Path("/tmp/backup.sql.gz"))
            
            assert metadata is not None
            assert metadata.total_users == 5
            assert metadata.database_type == DatabaseType.MYSQL
    
    def test_exclude_system_users(self):
        """Test excluding system users during backup."""
        manager = UsersManager(
            database_type=DatabaseType.MYSQL,
            host="localhost",
            port=3306,
            admin_user="root",
            admin_password="password"
        )
        
        all_users = [
            UserInfo("root", "localhost", ["ALL PRIVILEGES"]),
            UserInfo("mysql.sys", "localhost", ["USAGE"]),
            UserInfo("app_user", "%", ["SELECT", "INSERT"])
        ]
        
        excluded = manager._filter_system_users(
            all_users,
            exclude_users=["root", "mysql.sys"]
        )
        
        assert len(excluded) == 1
        assert excluded[0].username == "app_user"
    
    def test_generate_backup_filename(self):
        """Test generating backup filename."""
        manager = UsersManager(
            database_type=DatabaseType.MYSQL,
            host="localhost",
            port=3306,
            admin_user="root",
            admin_password="password"
        )
        
        filename = manager._generate_backup_filename("prod-mysql-01")
        
        assert filename.startswith("users_prod-mysql-01_")
        assert filename.endswith(".sql.gz")
        assert len(filename) > 30
