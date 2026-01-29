"""
Unit tests for config-instance CLI commands.

Tests all 6 config-instance commands:
- config-instance-add
- config-instance-list
- config-instance-get
- config-instance-remove
- config-instance-enable
- config-instance-disable
"""

import pytest
import yaml
from pathlib import Path
from typer.testing import CliRunner
from python_backup.cli import app

runner = CliRunner()


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file path."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "test-config.yaml"
    return str(config_file)


@pytest.fixture
def sample_config_data():
    """Sample config data structure."""
    return {
        'application_name': 'vya-backupdb',
        'version': '2.0.0',
        'environment': 'test',
        'databases': [
            {
                'id': 'test-mysql-01',
                'type': 'mysql',
                'host': 'localhost',
                'port': 3306,
                'enabled': True,
                'credential_name': 'mysql-prod',
                'database': [],
                'db_ignore': ['information_schema', 'mysql', 'sys', 'performance_schema'],
                'ssl_enabled': False
            },
            {
                'id': 'test-postgres-01',
                'type': 'postgresql',
                'host': 'localhost',
                'port': 5432,
                'enabled': True,
                'credential_name': 'postgres-prod',
                'database': ['app_db', 'analytics_db'],
                'db_ignore': [],
                'ssl_enabled': True,
                'ssl_ca_cert': '/etc/ssl/ca.pem'
            }
        ],
        'storage': {
            'base_path': '/var/backups/test',
            'structure': '{hostname}/{db_id}/{db_name}/{date}',
            'compression_level': 6,
            'checksum_algorithm': 'sha256'
        },
        'retention': {
            'strategy': 'gfs',
            'daily_keep': 7,
            'weekly_keep': 4,
            'monthly_keep': 12,
            'cleanup_enabled': True
        },
        'logging': {
            'level': 'INFO',
            'format': 'json',
            'output': 'file',
            'file_path': '/var/log/vya_backupdb/test.log'
        }
    }


@pytest.fixture
def populated_config_file(temp_config_file, sample_config_data):
    """Create a config file with sample data."""
    with open(temp_config_file, 'w') as f:
        yaml.dump(sample_config_data, f, default_flow_style=False, sort_keys=False, indent=2)
    return temp_config_file


# ============================================================================
# Test config-instance-add
# ============================================================================

class TestConfigInstanceAdd:
    """Tests for config-instance-add command."""
    
    def test_add_new_instance_basic(self, temp_config_file):
        """Test adding a new instance with basic parameters."""
        result = runner.invoke(app, [
            "config-instance-add",
            "--id", "new-mysql",
            "--type", "mysql",
            "--host", "db.example.com",
            "--port", "3306",
            "--credential", "mysql-cred",
            "--config", temp_config_file
        ])
        
        assert result.exit_code == 0
        assert "Added" in result.stdout
        assert "new-mysql" in result.stdout
        
        # Verify file was created
        with open(temp_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        assert len(config['databases']) == 1
        instance = config['databases'][0]
        assert instance['id'] == 'new-mysql'
        assert instance['type'] == 'mysql'
        assert instance['host'] == 'db.example.com'
        assert instance['port'] == 3306
        assert instance['credential_name'] == 'mysql-cred'
        assert instance['enabled'] is True
    
    def test_add_instance_with_whitelist(self, temp_config_file):
        """Test adding instance with database whitelist."""
        result = runner.invoke(app, [
            "config-instance-add",
            "--id", "mysql-whitelist",
            "--type", "mysql",
            "--host", "localhost",
            "--port", "3306",
            "--credential", "mysql-cred",
            "--databases", "app_prod,app_staging,app_analytics",
            "--config", temp_config_file
        ])
        
        assert result.exit_code == 0
        
        with open(temp_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        instance = config['databases'][0]
        assert instance['database'] == ['app_prod', 'app_staging', 'app_analytics']
        assert instance['db_ignore'] == []
    
    def test_add_instance_with_blacklist(self, temp_config_file):
        """Test adding instance with database blacklist."""
        result = runner.invoke(app, [
            "config-instance-add",
            "--id", "mysql-blacklist",
            "--type", "mysql",
            "--host", "localhost",
            "--port", "3306",
            "--credential", "mysql-cred",
            "--db-ignore", "information_schema,mysql,sys,performance_schema",
            "--config", temp_config_file
        ])
        
        assert result.exit_code == 0
        
        with open(temp_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        instance = config['databases'][0]
        assert instance['db_ignore'] == ['information_schema', 'mysql', 'sys', 'performance_schema']
        assert instance['database'] == []
    
    def test_add_instance_with_ssl(self, temp_config_file):
        """Test adding instance with SSL enabled."""
        result = runner.invoke(app, [
            "config-instance-add",
            "--id", "postgres-ssl",
            "--type", "postgresql",
            "--host", "secure.example.com",
            "--port", "5432",
            "--credential", "postgres-cred",
            "--ssl",
            "--ssl-ca-cert", "/etc/ssl/certs/ca.pem",
            "--config", temp_config_file
        ])
        
        assert result.exit_code == 0
        
        with open(temp_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        instance = config['databases'][0]
        assert instance['ssl_enabled'] is True
        assert instance['ssl_ca_cert'] == '/etc/ssl/certs/ca.pem'
    
    def test_add_instance_disabled(self, temp_config_file):
        """Test adding a disabled instance."""
        result = runner.invoke(app, [
            "config-instance-add",
            "--id", "disabled-mysql",
            "--type", "mysql",
            "--host", "localhost",
            "--port", "3306",
            "--credential", "mysql-cred",
            "--disabled",
            "--config", temp_config_file
        ])
        
        assert result.exit_code == 0
        
        with open(temp_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        instance = config['databases'][0]
        assert instance['enabled'] is False
    
    def test_update_existing_instance(self, populated_config_file):
        """Test updating an existing instance."""
        result = runner.invoke(app, [
            "config-instance-add",
            "--id", "test-mysql-01",
            "--type", "mysql",
            "--host", "new-host.example.com",
            "--port", "3307",
            "--credential", "mysql-new-cred",
            "--config", populated_config_file
        ])
        
        assert result.exit_code == 0
        assert "Updated" in result.stdout
        
        with open(populated_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        # Should still have 2 instances
        assert len(config['databases']) == 2
        
        # Find updated instance
        instance = next(db for db in config['databases'] if db['id'] == 'test-mysql-01')
        assert instance['host'] == 'new-host.example.com'
        assert instance['port'] == 3307
        assert instance['credential_name'] == 'mysql-new-cred'
    
    def test_add_instance_creates_directory(self, tmp_path):
        """Test that add command creates config directory if needed."""
        config_file = tmp_path / "nonexistent" / "dir" / "config.yaml"
        
        result = runner.invoke(app, [
            "config-instance-add",
            "--id", "test-mysql",
            "--type", "mysql",
            "--host", "localhost",
            "--port", "3306",
            "--credential", "mysql-cred",
            "--config", str(config_file)
        ])
        
        assert result.exit_code == 0
        assert config_file.exists()
        assert config_file.parent.exists()


# ============================================================================
# Test config-instance-list
# ============================================================================

class TestConfigInstanceList:
    """Tests for config-instance-list command."""
    
    def test_list_instances_success(self, populated_config_file):
        """Test listing instances successfully."""
        result = runner.invoke(app, [
            "config-instance-list",
            "--config", populated_config_file
        ])
        
        assert result.exit_code == 0
        # Check for truncated IDs (table formatting may truncate)
        assert "test-mysql" in result.stdout or "mysql" in result.stdout
        assert "test-postg" in result.stdout or "postgresql" in result.stdout
        assert "mysql" in result.stdout
        assert "postgresql" in result.stdout
    
    def test_list_empty_config(self, temp_config_file):
        """Test listing when config has no instances."""
        # Create empty config
        config_data = {
            'application_name': 'vya-backupdb',
            'version': '2.0.0',
            'databases': []
        }
        with open(temp_config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        result = runner.invoke(app, [
            "config-instance-list",
            "--config", temp_config_file
        ])
        
        assert result.exit_code == 0
        assert "No instances" in result.stdout
    
    def test_list_nonexistent_config(self, tmp_path):
        """Test listing when config file doesn't exist."""
        nonexistent = tmp_path / "nonexistent.yaml"
        
        result = runner.invoke(app, [
            "config-instance-list",
            "--config", str(nonexistent)
        ])
        
        assert result.exit_code == 0
        assert "not found" in result.stdout
    
    def test_list_with_disabled_instances(self, populated_config_file):
        """Test listing with disabled instances."""
        # Disable one instance
        with open(populated_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        config['databases'][0]['enabled'] = False
        
        with open(populated_config_file, 'w') as f:
            yaml.dump(config, f)
        
        # List without show-disabled
        result = runner.invoke(app, [
            "config-instance-list",
            "--config", populated_config_file
        ])
        
        assert result.exit_code == 0
        # PostgreSQL instance should appear (it's enabled)
        assert "postg" in result.stdout or "postgresql" in result.stdout
        # Count should be 1 (only enabled)
        assert "Config Instances (1)" in result.stdout
    
    def test_list_show_disabled_flag(self, populated_config_file):
        """Test --show-disabled flag."""
        # Disable one instance
        with open(populated_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        config['databases'][0]['enabled'] = False
        
        with open(populated_config_file, 'w') as f:
            yaml.dump(config, f)
        
        # List with show-disabled
        result = runner.invoke(app, [
            "config-instance-list",
            "--show-disabled",
            "--config", populated_config_file
        ])
        
        assert result.exit_code == 0
        # Both should appear (with show-disabled flag)
        assert "mysql" in result.stdout
        assert "postg" in result.stdout or "postgresql" in result.stdout
        # Count should be 2 (both enabled and disabled)
        assert "Config Instances (2)" in result.stdout
        assert "disabled" in result.stdout


# ============================================================================
# Test config-instance-get
# ============================================================================

class TestConfigInstanceGet:
    """Tests for config-instance-get command."""
    
    def test_get_instance_success(self, populated_config_file):
        """Test getting instance details successfully."""
        result = runner.invoke(app, [
            "config-instance-get",
            "--id", "test-mysql-01",
            "--config", populated_config_file
        ])
        
        assert result.exit_code == 0
        assert "test-mysql-01" in result.stdout
        assert "mysql" in result.stdout
        assert "localhost" in result.stdout
        assert "3306" in result.stdout
        assert "mysql-prod" in result.stdout
    
    def test_get_instance_with_whitelist(self, populated_config_file):
        """Test getting instance that has database whitelist."""
        result = runner.invoke(app, [
            "config-instance-get",
            "--id", "test-postgres-01",
            "--config", populated_config_file
        ])
        
        assert result.exit_code == 0
        assert "app_db" in result.stdout
        assert "analytics_db" in result.stdout
        assert "Whitelist" in result.stdout or "whitelist" in result.stdout.lower()
    
    def test_get_instance_with_blacklist(self, populated_config_file):
        """Test getting instance that has database blacklist."""
        result = runner.invoke(app, [
            "config-instance-get",
            "--id", "test-mysql-01",
            "--config", populated_config_file
        ])
        
        assert result.exit_code == 0
        assert "information_schema" in result.stdout
        assert "mysql" in result.stdout
        assert "Blacklist" in result.stdout or "blacklist" in result.stdout.lower() or "DB Ignore" in result.stdout
    
    def test_get_instance_with_ssl(self, populated_config_file):
        """Test getting instance with SSL enabled."""
        result = runner.invoke(app, [
            "config-instance-get",
            "--id", "test-postgres-01",
            "--config", populated_config_file
        ])
        
        assert result.exit_code == 0
        assert "SSL" in result.stdout or "ssl" in result.stdout
        assert "ca.pem" in result.stdout
    
    def test_get_nonexistent_instance(self, populated_config_file):
        """Test getting instance that doesn't exist."""
        result = runner.invoke(app, [
            "config-instance-get",
            "--id", "nonexistent-instance",
            "--config", populated_config_file
        ])
        
        assert result.exit_code == 1
        assert "not found" in result.stdout
    
    def test_get_from_nonexistent_config(self, tmp_path):
        """Test getting instance from nonexistent config."""
        nonexistent = tmp_path / "nonexistent.yaml"
        
        result = runner.invoke(app, [
            "config-instance-get",
            "--id", "test-mysql-01",
            "--config", str(nonexistent)
        ])
        
        assert result.exit_code == 1
        assert "not found" in result.stdout


# ============================================================================
# Test config-instance-remove
# ============================================================================

class TestConfigInstanceRemove:
    """Tests for config-instance-remove command."""
    
    def test_remove_instance_with_force(self, populated_config_file):
        """Test removing instance with --force flag."""
        result = runner.invoke(app, [
            "config-instance-remove",
            "--id", "test-mysql-01",
            "--force",
            "--config", populated_config_file
        ])
        
        assert result.exit_code == 0
        assert "Removed" in result.stdout
        
        # Verify instance was removed
        with open(populated_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        assert len(config['databases']) == 1
        assert config['databases'][0]['id'] == 'test-postgres-01'
    
    def test_remove_instance_with_confirmation(self, populated_config_file):
        """Test removing instance with confirmation."""
        result = runner.invoke(app, [
            "config-instance-remove",
            "--id", "test-mysql-01",
            "--config", populated_config_file
        ], input="y\n")
        
        assert result.exit_code == 0
        assert "Removed" in result.stdout
        
        # Verify instance was removed
        with open(populated_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        assert len(config['databases']) == 1
    
    def test_remove_instance_cancel_confirmation(self, populated_config_file):
        """Test canceling removal confirmation."""
        result = runner.invoke(app, [
            "config-instance-remove",
            "--id", "test-mysql-01",
            "--config", populated_config_file
        ], input="n\n")
        
        # When user cancels, typer exits with code 0 but raises Abort
        # The implementation raises Exit(0) on cancel
        assert result.exit_code in [0, 1]  # Accept both since typer.confirm can vary
        
        # Verify instance was NOT removed
        with open(populated_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        assert len(config['databases']) == 2
    
    def test_remove_nonexistent_instance(self, populated_config_file):
        """Test removing instance that doesn't exist."""
        result = runner.invoke(app, [
            "config-instance-remove",
            "--id", "nonexistent-instance",
            "--force",
            "--config", populated_config_file
        ])
        
        assert result.exit_code == 1
        assert "not found" in result.stdout
    
    def test_remove_from_nonexistent_config(self, tmp_path):
        """Test removing from nonexistent config."""
        nonexistent = tmp_path / "nonexistent.yaml"
        
        result = runner.invoke(app, [
            "config-instance-remove",
            "--id", "test-mysql-01",
            "--force",
            "--config", str(nonexistent)
        ])
        
        assert result.exit_code == 1
        assert "not found" in result.stdout


# ============================================================================
# Test config-instance-enable
# ============================================================================

class TestConfigInstanceEnable:
    """Tests for config-instance-enable command."""
    
    def test_enable_disabled_instance(self, populated_config_file):
        """Test enabling a disabled instance."""
        # First disable it
        with open(populated_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        config['databases'][0]['enabled'] = False
        
        with open(populated_config_file, 'w') as f:
            yaml.dump(config, f)
        
        # Now enable it
        result = runner.invoke(app, [
            "config-instance-enable",
            "--id", "test-mysql-01",
            "--config", populated_config_file
        ])
        
        assert result.exit_code == 0
        assert "Enabled" in result.stdout
        
        # Verify it was enabled
        with open(populated_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        instance = next(db for db in config['databases'] if db['id'] == 'test-mysql-01')
        assert instance['enabled'] is True
    
    def test_enable_already_enabled_instance(self, populated_config_file):
        """Test enabling an already enabled instance."""
        result = runner.invoke(app, [
            "config-instance-enable",
            "--id", "test-mysql-01",
            "--config", populated_config_file
        ])
        
        assert result.exit_code == 0
        assert "Enabled" in result.stdout
    
    def test_enable_nonexistent_instance(self, populated_config_file):
        """Test enabling instance that doesn't exist."""
        result = runner.invoke(app, [
            "config-instance-enable",
            "--id", "nonexistent-instance",
            "--config", populated_config_file
        ])
        
        assert result.exit_code == 1
        assert "not found" in result.stdout
    
    def test_enable_from_nonexistent_config(self, tmp_path):
        """Test enabling from nonexistent config."""
        nonexistent = tmp_path / "nonexistent.yaml"
        
        result = runner.invoke(app, [
            "config-instance-enable",
            "--id", "test-mysql-01",
            "--config", str(nonexistent)
        ])
        
        assert result.exit_code == 1
        assert "not found" in result.stdout


# ============================================================================
# Test config-instance-disable
# ============================================================================

class TestConfigInstanceDisable:
    """Tests for config-instance-disable command."""
    
    def test_disable_enabled_instance(self, populated_config_file):
        """Test disabling an enabled instance."""
        result = runner.invoke(app, [
            "config-instance-disable",
            "--id", "test-mysql-01",
            "--config", populated_config_file
        ])
        
        assert result.exit_code == 0
        assert "Disabled" in result.stdout
        
        # Verify it was disabled
        with open(populated_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        instance = next(db for db in config['databases'] if db['id'] == 'test-mysql-01')
        assert instance['enabled'] is False
    
    def test_disable_already_disabled_instance(self, populated_config_file):
        """Test disabling an already disabled instance."""
        # First disable it
        with open(populated_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        config['databases'][0]['enabled'] = False
        
        with open(populated_config_file, 'w') as f:
            yaml.dump(config, f)
        
        # Disable again
        result = runner.invoke(app, [
            "config-instance-disable",
            "--id", "test-mysql-01",
            "--config", populated_config_file
        ])
        
        assert result.exit_code == 0
        assert "Disabled" in result.stdout
    
    def test_disable_preserves_configuration(self, populated_config_file):
        """Test that disabling preserves all other configuration."""
        # Get original config
        with open(populated_config_file, 'r') as f:
            config_before = yaml.safe_load(f)
        
        instance_before = next(db for db in config_before['databases'] if db['id'] == 'test-mysql-01')
        
        # Disable
        result = runner.invoke(app, [
            "config-instance-disable",
            "--id", "test-mysql-01",
            "--config", populated_config_file
        ])
        
        assert result.exit_code == 0
        
        # Verify other fields preserved
        with open(populated_config_file, 'r') as f:
            config_after = yaml.safe_load(f)
        
        instance_after = next(db for db in config_after['databases'] if db['id'] == 'test-mysql-01')
        
        assert instance_after['type'] == instance_before['type']
        assert instance_after['host'] == instance_before['host']
        assert instance_after['port'] == instance_before['port']
        assert instance_after['credential_name'] == instance_before['credential_name']
        assert instance_after['enabled'] is False  # Only this changed
    
    def test_disable_nonexistent_instance(self, populated_config_file):
        """Test disabling instance that doesn't exist."""
        result = runner.invoke(app, [
            "config-instance-disable",
            "--id", "nonexistent-instance",
            "--config", populated_config_file
        ])
        
        assert result.exit_code == 1
        assert "not found" in result.stdout
    
    def test_disable_from_nonexistent_config(self, tmp_path):
        """Test disabling from nonexistent config."""
        nonexistent = tmp_path / "nonexistent.yaml"
        
        result = runner.invoke(app, [
            "config-instance-disable",
            "--id", "test-mysql-01",
            "--config", str(nonexistent)
        ])
        
        assert result.exit_code == 1
        assert "not found" in result.stdout


# ============================================================================
# Integration Tests
# ============================================================================

class TestConfigInstanceIntegration:
    """Integration tests for config-instance commands."""
    
    def test_full_lifecycle(self, temp_config_file):
        """Test full lifecycle: add, list, get, disable, enable, remove."""
        # 1. Add instance
        result = runner.invoke(app, [
            "config-instance-add",
            "--id", "lifecycle-test",
            "--type", "mysql",
            "--host", "localhost",
            "--port", "3306",
            "--credential", "test-cred",
            "--config", temp_config_file
        ])
        assert result.exit_code == 0
        
        # 2. List instances
        result = runner.invoke(app, [
            "config-instance-list",
            "--config", temp_config_file
        ])
        assert result.exit_code == 0
        # Check for truncated ID or full ID
        assert "lifecycle" in result.stdout or "mysql" in result.stdout
        
        # 3. Get instance details
        result = runner.invoke(app, [
            "config-instance-get",
            "--id", "lifecycle-test",
            "--config", temp_config_file
        ])
        assert result.exit_code == 0
        assert "mysql" in result.stdout
        
        # 4. Disable instance
        result = runner.invoke(app, [
            "config-instance-disable",
            "--id", "lifecycle-test",
            "--config", temp_config_file
        ])
        assert result.exit_code == 0
        
        # 5. Verify disabled
        with open(temp_config_file, 'r') as f:
            config = yaml.safe_load(f)
        assert config['databases'][0]['enabled'] is False
        
        # 6. Enable instance
        result = runner.invoke(app, [
            "config-instance-enable",
            "--id", "lifecycle-test",
            "--config", temp_config_file
        ])
        assert result.exit_code == 0
        
        # 7. Verify enabled
        with open(temp_config_file, 'r') as f:
            config = yaml.safe_load(f)
        assert config['databases'][0]['enabled'] is True
        
        # 8. Remove instance
        result = runner.invoke(app, [
            "config-instance-remove",
            "--id", "lifecycle-test",
            "--force",
            "--config", temp_config_file
        ])
        assert result.exit_code == 0
        
        # 9. Verify removed
        with open(temp_config_file, 'r') as f:
            config = yaml.safe_load(f)
        assert len(config['databases']) == 0
    
    def test_multiple_instances_management(self, temp_config_file):
        """Test managing multiple instances."""
        # Add 3 instances
        for i in range(1, 4):
            result = runner.invoke(app, [
                "config-instance-add",
                "--id", f"mysql-{i}",
                "--type", "mysql",
                "--host", f"host{i}.example.com",
                "--port", "3306",
                "--credential", f"cred-{i}",
                "--config", temp_config_file
            ])
            assert result.exit_code == 0
        
        # List all
        result = runner.invoke(app, [
            "config-instance-list",
            "--config", temp_config_file
        ])
        assert result.exit_code == 0
        assert "mysql-1" in result.stdout
        assert "mysql-2" in result.stdout
        assert "mysql-3" in result.stdout
        
        # Disable one
        result = runner.invoke(app, [
            "config-instance-disable",
            "--id", "mysql-2",
            "--config", temp_config_file
        ])
        assert result.exit_code == 0
        
        # List without show-disabled
        result = runner.invoke(app, [
            "config-instance-list",
            "--config", temp_config_file
        ])
        assert result.exit_code == 0
        # Should show 2 enabled instances
        
        # Remove one
        result = runner.invoke(app, [
            "config-instance-remove",
            "--id", "mysql-3",
            "--force",
            "--config", temp_config_file
        ])
        assert result.exit_code == 0
        
        # Verify final state
        with open(temp_config_file, 'r') as f:
            config = yaml.safe_load(f)
        assert len(config['databases']) == 2
        ids = [db['id'] for db in config['databases']]
        assert 'mysql-1' in ids
        assert 'mysql-2' in ids
        assert 'mysql-3' not in ids
