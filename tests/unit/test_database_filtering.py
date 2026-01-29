"""Unit tests for database filtering logic with precedence rules"""

import pytest
from unittest.mock import Mock, patch
from python_backup.config.models import DatabaseConfig
from python_backup.db.base import DatabaseAdapter
from python_backup.db.mysql import MySQLAdapter
from python_backup.db.postgresql import PostgreSQLAdapter


class ConcreteDatabaseAdapter(DatabaseAdapter):
    """Concrete implementation for testing abstract DatabaseAdapter"""
    
    def get_databases(self) -> list[str]:
        return []
    
    def test_connection(self) -> bool:
        return True
    
    def backup_database(self, database_name: str, output_path: str) -> bool:
        return True
    
    def get_backup_command(self, database_name: str, output_path: str) -> list[str]:
        return []


class TestDatabaseFilteringPrecedence:
    """Test filtering precedence: 1. Include (databases) 2. Exclude (db_ignore) 3. System"""
    
    @pytest.fixture
    def mysql_config(self):
        """MySQL config with empty filters (all databases)"""
        return DatabaseConfig(
            id="test-mysql",
            type="mysql",
            host="localhost",
            port=3306,
            username="test",
            password="test",
            databases=[],
            db_ignore=[]
        )
    
    @pytest.fixture
    def postgresql_config(self):
        """PostgreSQL config with empty filters (all databases)"""
        return DatabaseConfig(
            id="test-pg",
            type="postgresql",
            host="localhost",
            port=5432,
            username="test",
            password="test",
            databases=[],
            db_ignore=[]
        )
    
    def test_scenario_1_all_databases_default(self, mysql_config):
        """Scenario 1: databases=[] db_ignore=[] → all (except system)"""
        adapter = ConcreteDatabaseAdapter(mysql_config)
        all_dbs = ["app1", "app2", "test", "mysql", "information_schema"]
        
        result = adapter.get_filtered_databases(all_dbs)
        
        # Should include all user databases
        assert "app1" in result
        assert "app2" in result
        assert "test" in result
        # Should exclude system databases
        assert "mysql" not in result
        assert "information_schema" not in result
    
    def test_scenario_2_whitelist_single(self, mysql_config):
        """Scenario 2: databases=['app'] db_ignore=[] → only 'app'"""
        mysql_config.databases = ["app_workforce"]
        adapter = ConcreteDatabaseAdapter(mysql_config)
        all_dbs = ["app_workforce", "app_test", "app_dev", "mysql"]
        
        result = adapter.get_filtered_databases(all_dbs)
        
        # Should include only whitelisted database
        assert result == ["app_workforce"]
    
    def test_scenario_3_blacklist_multiple(self, mysql_config):
        """Scenario 3: databases=[] db_ignore=['test','dev'] → all except test/dev/system"""
        mysql_config.db_ignore = ["test_db", "dev_db", "staging_db"]
        adapter = ConcreteDatabaseAdapter(mysql_config)
        all_dbs = ["prod", "test_db", "dev_db", "staging_db", "analytics", "mysql"]
        
        result = adapter.get_filtered_databases(all_dbs)
        
        # Should include non-blacklisted databases
        assert "prod" in result
        assert "analytics" in result
        # Should exclude blacklisted databases
        assert "test_db" not in result
        assert "dev_db" not in result
        assert "staging_db" not in result
        # Should exclude system databases
        assert "mysql" not in result
    
    def test_scenario_4_whitelist_with_blacklist(self, mysql_config):
        """Scenario 4: databases=['t1','t2','t3','t4'] db_ignore=['t3'] → t1,t2,t4"""
        mysql_config.databases = ["tenant1", "tenant2", "tenant3", "tenant4"]
        mysql_config.db_ignore = ["tenant3"]
        adapter = ConcreteDatabaseAdapter(mysql_config)
        all_dbs = ["tenant1", "tenant2", "tenant3", "tenant4", "tenant5", "admin"]
        
        result = adapter.get_filtered_databases(all_dbs)
        
        # Should include whitelisted except blacklisted
        assert "tenant1" in result
        assert "tenant2" in result
        assert "tenant4" in result
        # Should exclude blacklisted even if whitelisted
        assert "tenant3" not in result
        # Should exclude non-whitelisted
        assert "tenant5" not in result
        assert "admin" not in result
    
    def test_scenario_5_redundant_ignore(self, mysql_config):
        """Scenario 5: databases=['app'] db_ignore=['test'] → only 'app' (ignore has no effect)"""
        mysql_config.databases = ["app_prod"]
        mysql_config.db_ignore = ["app_test"]  # Not in whitelist, no effect
        adapter = ConcreteDatabaseAdapter(mysql_config)
        all_dbs = ["app_prod", "app_test", "app_dev"]
        
        result = adapter.get_filtered_databases(all_dbs)
        
        # Should include only whitelisted
        assert result == ["app_prod"]
    
    def test_system_databases_always_excluded_mysql(self, mysql_config):
        """System databases always excluded even if explicitly included"""
        mysql_config.databases = ["myapp", "mysql", "information_schema"]
        adapter = ConcreteDatabaseAdapter(mysql_config)
        all_dbs = ["myapp", "mysql", "information_schema", "performance_schema"]
        
        result = adapter.get_filtered_databases(all_dbs)
        
        # Should include user database
        assert "myapp" in result
        # Should exclude system databases even if in whitelist
        assert "mysql" not in result
        assert "information_schema" not in result
        assert "performance_schema" not in result
    
    def test_system_databases_always_excluded_postgresql(self, postgresql_config):
        """PostgreSQL system databases always excluded"""
        postgresql_config.databases = ["myapp", "postgres"]
        adapter = ConcreteDatabaseAdapter(postgresql_config)
        all_dbs = ["myapp", "postgres", "template0", "template1"]
        
        result = adapter.get_filtered_databases(all_dbs)
        
        # Should include user database
        assert "myapp" in result
        # Should exclude system databases
        assert "postgres" not in result
        assert "template0" not in result
        assert "template1" not in result
    
    def test_all_excluded_returns_empty(self, mysql_config):
        """When all databases are excluded, returns empty list"""
        mysql_config.databases = ["test"]
        mysql_config.db_ignore = ["test"]
        adapter = ConcreteDatabaseAdapter(mysql_config)
        all_dbs = ["test", "prod"]
        
        result = adapter.get_filtered_databases(all_dbs)
        
        assert result == []
    
    def test_nonexistent_database_in_whitelist(self, mysql_config):
        """Non-existent database in whitelist is ignored gracefully"""
        mysql_config.databases = ["myapp", "nonexistent"]
        adapter = ConcreteDatabaseAdapter(mysql_config)
        all_dbs = ["myapp", "test"]
        
        result = adapter.get_filtered_databases(all_dbs)
        
        # Should only include existing databases
        assert result == ["myapp"]
    
    def test_nonexistent_database_in_blacklist(self, mysql_config):
        """Non-existent database in blacklist has no effect"""
        mysql_config.db_ignore = ["nonexistent"]
        adapter = ConcreteDatabaseAdapter(mysql_config)
        all_dbs = ["myapp", "test"]
        
        result = adapter.get_filtered_databases(all_dbs)
        
        # Should include all user databases
        assert "myapp" in result
        assert "test" in result


class TestBackwardCompatibility:
    """Test backward compatibility with old field names"""
    
    def test_legacy_exclude_databases_field(self):
        """Support legacy exclude_databases field"""
        from python_backup.config.loader import DatabaseConfig as LegacyConfig
        
        # Create config with old field name - db_ignore is a list
        legacy = LegacyConfig(
            id_dbms=1,
            dbms="mysql",
            host="localhost",
            port=3306,
            user="test",
            secret="test",
            db_ignore=["test"],  # Excluding 'test'
            database=[],  # All databases
            enabled=True
        )
        
        # Create mock config with Pydantic model fields for adapter
        from python_backup.config.models import DatabaseConfig
        pydantic_config = DatabaseConfig(
            id="test-mysql",
            type="mysql",
            host="localhost",
            port=3306,
            username="test",
            password="test",
            databases=[],  # All databases
            db_ignore=["test"]  # Excluding 'test'
        )
        
        adapter = ConcreteDatabaseAdapter(pydantic_config)
        all_dbs = ["myapp", "test", "mysql"]
        
        result = adapter.get_filtered_databases(all_dbs)
        
        # Should include myapp, exclude test and mysql (system)
        assert "myapp" in result
        assert "test" not in result
        assert "mysql" not in result
    
    def test_legacy_db_list_field_in_loader(self):
        """Loader supports both 'database' and 'db_list' fields"""
        from python_backup.config.loader import DatabaseConfig as LegacyConfig
        
        # Test with new field name 'database'
        config1 = LegacyConfig.from_dict({
            'id_dbms': 1,
            'dbms': 'mysql',
            'host': 'localhost',
            'port': 3306,
            'user': 'test',
            'secret': 'test',
            'database': ['app1', 'app2'],
            'db_ignore': []
        })
        assert config1.database == ['app1', 'app2']
        
        # Test with old field name 'db_list'
        config2 = LegacyConfig.from_dict({
            'id_dbms': 1,
            'dbms': 'mysql',
            'host': 'localhost',
            'port': 3306,
            'user': 'test',
            'secret': 'test',
            'db_list': ['app3', 'app4'],
            'db_ignore': []
        })
        assert config2.database == ['app3', 'app4']
        
        # Test priority: 'database' > 'db_list'
        config3 = LegacyConfig.from_dict({
            'id_dbms': 1,
            'dbms': 'mysql',
            'host': 'localhost',
            'port': 3306,
            'user': 'test',
            'secret': 'test',
            'database': ['new'],
            'db_list': ['old'],
            'db_ignore': []
        })
        assert config3.database == ['new']  # 'database' takes priority


class TestEdgeCases:
    """Test edge cases and error scenarios"""
    
    def test_empty_all_databases_list(self):
        """Empty input list returns empty result"""
        config = DatabaseConfig(
            id="test",
            type="mysql",
            host="localhost",
            port=3306,
            username="test",
            password="test"
        )
        adapter = ConcreteDatabaseAdapter(config)
        
        result = adapter.get_filtered_databases([])
        
        assert result == []
    
    def test_databases_with_special_characters(self):
        """Databases with special characters are handled correctly"""
        config = DatabaseConfig(
            id="test",
            type="mysql",
            host="localhost",
            port=3306,
            username="test",
            password="test",
            databases=["my-app", "my_db", "my.database"]
        )
        adapter = ConcreteDatabaseAdapter(config)
        all_dbs = ["my-app", "my_db", "my.database", "other"]
        
        result = adapter.get_filtered_databases(all_dbs)
        
        assert "my-app" in result
        assert "my_db" in result
        assert "my.database" in result
        assert "other" not in result
    
    def test_case_sensitive_filtering(self):
        """Database names are case-sensitive"""
        config = DatabaseConfig(
            id="test",
            type="mysql",
            host="localhost",
            port=3306,
            username="test",
            password="test",
            databases=["MyApp"]
        )
        adapter = ConcreteDatabaseAdapter(config)
        all_dbs = ["MyApp", "myapp", "MYAPP"]
        
        result = adapter.get_filtered_databases(all_dbs)
        
        # Only exact match should be included
        assert result == ["MyApp"]
    
    def test_duplicate_databases_in_config(self):
        """Duplicate databases in config are handled gracefully"""
        config = DatabaseConfig(
            id="test",
            type="mysql",
            host="localhost",
            port=3306,
            username="test",
            password="test",
            databases=["app", "app", "test"]
        )
        adapter = ConcreteDatabaseAdapter(config)
        all_dbs = ["app", "test", "other"]
        
        result = adapter.get_filtered_databases(all_dbs)
        
        # Should not have duplicates in result
        assert len(result) == len(set(result))
        assert "app" in result
        assert "test" in result


class TestLoggingOutput:
    """Test that filtering produces proper log output"""
    
    def test_filtering_produces_debug_logs(self, caplog):
        """Filtering should produce debug logs for transparency"""
        import logging
        caplog.set_level(logging.DEBUG)
        
        config = DatabaseConfig(
            id="test",
            type="mysql",
            host="localhost",
            port=3306,
            username="test",
            password="test",
            databases=["app"],
            db_ignore=["test"]
        )
        adapter = ConcreteDatabaseAdapter(config)
        all_dbs = ["app", "test", "mysql"]
        
        result = adapter.get_filtered_databases(all_dbs)
        
        # Check that logs contain filtering information
        assert "Filtering databases" in caplog.text
        assert "Step 1" in caplog.text  # Inclusion
        assert "Step 2" in caplog.text  # Exclusion
        # Note: Step 3 only logs when system DBs are actually removed
        assert "Final databases to backup" in caplog.text
    
    def test_empty_result_produces_warning(self, caplog):
        """Empty result should produce warning log"""
        import logging
        caplog.set_level(logging.WARNING)
        
        config = DatabaseConfig(
            id="test",
            type="mysql",
            host="localhost",
            port=3306,
            username="test",
            password="test",
            databases=["app"],
            db_ignore=["app"]
        )
        adapter = ConcreteDatabaseAdapter(config)
        all_dbs = ["app", "test"]
        
        result = adapter.get_filtered_databases(all_dbs)
        
        # Should produce warning about no databases
        assert "No databases matched filters" in caplog.text
        assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
