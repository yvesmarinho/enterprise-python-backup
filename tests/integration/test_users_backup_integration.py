"""
Integration tests for UsersManager with real database access.
Tests user backup/restore with actual MySQL and PostgreSQL databases.
"""

import pytest
from pathlib import Path
from datetime import datetime
from python_backup.users.manager import UsersManager, DatabaseType
from python_backup.config import load_config
import os
import shutil


# Try to load configuration from python_backup.json
try:
    config = load_config()
    # Get first enabled MySQL database
    mysql_dbs = [db for db in config.get_enabled_databases() if db.dbms == 'mysql']
    if mysql_dbs:
        mysql_config = mysql_dbs[0]
        MYSQL_HOST = mysql_config.host
        MYSQL_PORT = mysql_config.port
        MYSQL_USER = mysql_config.user
        MYSQL_PASSWORD = mysql_config.secret
    else:
        raise ValueError("No MySQL database found in config")
    
    # Get first enabled PostgreSQL database
    postgres_dbs = [db for db in config.get_enabled_databases() if db.dbms == 'postgresql']
    if postgres_dbs:
        pg_config = postgres_dbs[0]
        POSTGRESQL_HOST = pg_config.host
        POSTGRESQL_PORT = pg_config.port
        POSTGRESQL_USER = pg_config.user
        POSTGRESQL_PASSWORD = pg_config.secret
    else:
        # Use MySQL config for PostgreSQL if not found (same server)
        POSTGRESQL_HOST = MYSQL_HOST
        POSTGRESQL_PORT = 5432
        POSTGRESQL_USER = os.getenv('TEST_PG_USER', 'postgres')
        POSTGRESQL_PASSWORD = os.getenv('TEST_PG_PASSWORD', 'W123Mudar')
except Exception as e:
    print(f"Warning: Could not load vya_backupbd.json, using defaults: {e}")
    # Fallback to environment variables or defaults
    MYSQL_HOST = os.getenv('TEST_MYSQL_HOST', '192.168.15.197')
    MYSQL_PORT = int(os.getenv('TEST_MYSQL_PORT', '3306'))
    MYSQL_USER = os.getenv('TEST_MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.getenv('TEST_MYSQL_PASSWORD', 'W123Mudar')
    
    POSTGRESQL_HOST = os.getenv('TEST_PG_HOST', '192.168.15.197')
    POSTGRESQL_PORT = int(os.getenv('TEST_PG_PORT', '5432'))
    POSTGRESQL_USER = os.getenv('TEST_PG_USER', 'postgres')
    POSTGRESQL_PASSWORD = os.getenv('TEST_PG_PASSWORD', 'W123Mudar')


@pytest.fixture
def test_output_dir(tmp_path):
    """Create temporary directory for backup files."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    yield backup_dir
    # Cleanup
    if backup_dir.exists():
        shutil.rmtree(backup_dir)


@pytest.fixture
def mysql_manager():
    """Create UsersManager instance for MySQL."""
    return UsersManager(
        database_type=DatabaseType.MYSQL,
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        admin_user=MYSQL_USER,
        admin_password=MYSQL_PASSWORD
    )


@pytest.fixture
def postgresql_manager():
    """Create UsersManager instance for PostgreSQL."""
    return UsersManager(
        database_type=DatabaseType.POSTGRESQL,
        host=POSTGRESQL_HOST,
        port=POSTGRESQL_PORT,
        admin_user=POSTGRESQL_USER,
        admin_password=POSTGRESQL_PASSWORD
    )


class TestMySQLUsersBackup:
    """Integration tests for MySQL user backup."""
    
    def test_backup_mysql_users(self, mysql_manager, test_output_dir):
        """Test backing up MySQL users from test_ecommerce database."""
        output_file = test_output_dir / "mysql_users_backup.sql.gz"
        
        # Perform backup
        metadata = mysql_manager.backup_users(
            output_path=output_file,
            exclude_system_users=True,
            compress=True
        )
        
        # Verify backup was created
        assert output_file.exists()
        assert output_file.stat().st_size > 0
        
        # Verify metadata
        assert metadata.database_type == DatabaseType.MYSQL
        assert metadata.total_users > 0
        assert metadata.compressed is True
        assert metadata.backup_size_bytes > 0
        
        # Verify backup contains test users
        user_names = [u.username for u in metadata.users]
        assert 'app_user' in user_names
        assert 'readonly_user' in user_names
        assert 'backup_user' in user_names
        assert 'analytics_user' in user_names
        
        print(f"\n✅ MySQL backup criado: {output_file}")
        print(f"📊 Total de usuários: {metadata.total_users}")
        print(f"💾 Tamanho: {metadata.backup_size_bytes} bytes")
        print(f"👥 Usuários: {', '.join(user_names)}")
    
    def test_list_mysql_users(self, mysql_manager, test_output_dir):
        """Test listing MySQL users from backup without restoring."""
        output_file = test_output_dir / "mysql_users_list.sql.gz"
        
        # Create backup
        metadata = mysql_manager.backup_users(
            output_path=output_file,
            exclude_system_users=True,
            compress=True
        )
        
        # List users from backup
        users = mysql_manager.list_users(output_file)
        
        assert len(users) == metadata.total_users
        assert all(hasattr(u, 'username') for u in users)
        assert all(hasattr(u, 'host') for u in users)
        assert all(hasattr(u, 'privileges') for u in users)
        
        print(f"\n📋 Usuários MySQL listados do backup:")
        for user in users:
            print(f"   - {user.username}@{user.host}: {len(user.privileges)} privilégios")
    
    def test_validate_mysql_backup(self, mysql_manager, test_output_dir):
        """Test validating MySQL backup file."""
        output_file = test_output_dir / "mysql_users_validate.sql.gz"
        
        # Create backup
        mysql_manager.backup_users(
            output_path=output_file,
            exclude_system_users=True,
            compress=True
        )
        
        # Validate backup
        is_valid = mysql_manager.validate_backup_file(output_file)
        assert is_valid is True
        
        # Test invalid file
        invalid_file = test_output_dir / "nonexistent.sql.gz"
        is_valid = mysql_manager.validate_backup_file(invalid_file)
        assert is_valid is False
        
        print(f"\n✅ Backup MySQL validado com sucesso")


class TestPostgreSQLRolesBackup:
    """Integration tests for PostgreSQL roles backup."""
    
    def test_backup_postgresql_roles(self, postgresql_manager, test_output_dir):
        """Test backing up PostgreSQL roles from test_inventory database."""
        output_file = test_output_dir / "postgresql_roles_backup.sql.gz"
        
        # Perform backup
        metadata = postgresql_manager.backup_users(
            output_path=output_file,
            exclude_system_users=True,
            compress=True
        )
        
        # Verify backup was created
        assert output_file.exists()
        assert output_file.stat().st_size > 0
        
        # Verify metadata
        assert metadata.database_type == DatabaseType.POSTGRESQL
        assert metadata.total_users > 0
        assert metadata.compressed is True
        assert metadata.backup_size_bytes > 0
        
        # Verify backup contains test roles
        role_names = [u.username for u in metadata.users]
        assert 'app_role' in role_names
        assert 'readonly_role' in role_names
        assert 'backup_role' in role_names
        assert 'analytics_role' in role_names
        assert 'admin_group' in role_names
        
        print(f"\n✅ PostgreSQL backup criado: {output_file}")
        print(f"📊 Total de roles: {metadata.total_users}")
        print(f"💾 Tamanho: {metadata.backup_size_bytes} bytes")
        print(f"👥 Roles: {', '.join(role_names[:10])}...")
    
    def test_list_postgresql_roles(self, postgresql_manager, test_output_dir):
        """Test listing PostgreSQL roles from backup without restoring."""
        output_file = test_output_dir / "postgresql_roles_list.sql.gz"
        
        # Create backup
        metadata = postgresql_manager.backup_users(
            output_path=output_file,
            exclude_system_users=True,
            compress=True
        )
        
        # List roles from backup
        roles = postgresql_manager.list_users(output_file)
        
        assert len(roles) == metadata.total_users
        assert all(hasattr(r, 'username') for r in roles)
        
        print(f"\n📋 Roles PostgreSQL listadas do backup:")
        for role in roles[:10]:  # Show first 10
            print(f"   - {role.username}")
    
    def test_validate_postgresql_backup(self, postgresql_manager, test_output_dir):
        """Test validating PostgreSQL backup file."""
        output_file = test_output_dir / "postgresql_roles_validate.sql.gz"
        
        # Create backup
        postgresql_manager.backup_users(
            output_path=output_file,
            exclude_system_users=True,
            compress=True
        )
        
        # Validate backup
        is_valid = postgresql_manager.validate_backup_file(output_file)
        assert is_valid is True
        
        # Test invalid file
        invalid_file = test_output_dir / "nonexistent.sql.gz"
        is_valid = postgresql_manager.validate_backup_file(invalid_file)
        assert is_valid is False
        
        print(f"\n✅ Backup PostgreSQL validado com sucesso")


class TestBackupMetadata:
    """Test backup metadata functionality."""
    
    def test_mysql_backup_metadata_file(self, mysql_manager, test_output_dir):
        """Test that metadata file is created alongside backup."""
        output_file = test_output_dir / "mysql_metadata_test.sql.gz"
        
        # Create backup
        metadata = mysql_manager.backup_users(
            output_path=output_file,
            exclude_system_users=True,
            compress=True
        )
        
        # Check metadata file exists
        metadata_file = test_output_dir / "mysql_metadata_test.metadata.json"
        assert metadata_file.exists()
        
        # Verify metadata can be read back
        import json
        with open(metadata_file, 'r') as f:
            data = json.load(f)
        
        assert data['database_type'] == 'mysql'
        assert data['total_users'] == metadata.total_users
        assert 'backup_timestamp' in data
        assert 'users' in data
        
        print(f"\n✅ Arquivo de metadata criado: {metadata_file}")
        print(f"📄 Conteúdo: {json.dumps(data, indent=2)[:500]}...")
    
    def test_postgresql_backup_metadata_file(self, postgresql_manager, test_output_dir):
        """Test that metadata file is created alongside backup."""
        output_file = test_output_dir / "postgresql_metadata_test.sql.gz"
        
        # Create backup
        metadata = postgresql_manager.backup_users(
            output_path=output_file,
            exclude_system_users=True,
            compress=True
        )
        
        # Check metadata file exists
        metadata_file = test_output_dir / "postgresql_metadata_test.metadata.json"
        assert metadata_file.exists()
        
        # Verify metadata can be read back
        import json
        with open(metadata_file, 'r') as f:
            data = json.load(f)
        
        assert data['database_type'] == 'postgresql'
        assert data['total_users'] == metadata.total_users
        
        print(f"\n✅ Arquivo de metadata criado: {metadata_file}")
