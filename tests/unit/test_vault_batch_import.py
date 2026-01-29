"""
Unit tests for vault-add --from-file functionality.
"""

import json
import pytest
from pathlib import Path
from typer.testing import CliRunner
from python_backup.cli import app

runner = CliRunner()


@pytest.fixture
def temp_credentials_file(tmp_path):
    """Create a temporary credentials JSON file."""
    credentials = [
        {
            "id": "test-mysql",
            "username": "root",
            "password": "TestP@ss123",
            "description": "Test MySQL Server"
        },
        {
            "id": "test-postgres",
            "username": "postgres",
            "password": "PostgresP@ss456",
            "description": "Test PostgreSQL Server"
        }
    ]
    
    creds_file = tmp_path / "credentials.json"
    creds_file.write_text(json.dumps(credentials, indent=2))
    return creds_file


@pytest.fixture
def temp_vault_file(tmp_path):
    """Create a temporary vault file path."""
    return str(tmp_path / "test_vault.json.enc")


class TestVaultAddFromFile:
    """Test cases for vault-add --from-file command."""
    
    def test_import_multiple_credentials_success(self, temp_credentials_file, temp_vault_file):
        """Test successful import of multiple credentials."""
        result = runner.invoke(
            app,
            ["vault-add", "--from-file", str(temp_credentials_file), "--vault", temp_vault_file]
        )
        
        assert result.exit_code == 0
        assert "Importing credentials from" in result.stdout
        assert "Adding credential 'test-mysql'" in result.stdout
        assert "Adding credential 'test-postgres'" in result.stdout
        assert "Import Summary:" in result.stdout
        assert "Added: 2" in result.stdout
        assert "Updated: 0" in result.stdout
    
    def test_update_existing_credentials(self, temp_credentials_file, temp_vault_file):
        """Test updating existing credentials with --from-file."""
        # First import
        runner.invoke(
            app,
            ["vault-add", "--from-file", str(temp_credentials_file), "--vault", temp_vault_file]
        )
        
        # Second import (should update)
        result = runner.invoke(
            app,
            ["vault-add", "--from-file", str(temp_credentials_file), "--vault", temp_vault_file]
        )
        
        assert result.exit_code == 0
        assert "Updating credential" in result.stdout
        assert "Added: 0" in result.stdout
        assert "Updated: 2" in result.stdout
    
    def test_file_not_found(self, temp_vault_file):
        """Test error when credentials file doesn't exist."""
        result = runner.invoke(
            app,
            ["vault-add", "--from-file", "nonexistent.json", "--vault", temp_vault_file]
        )
        
        assert result.exit_code == 1
        assert "File not found" in result.stdout
    
    def test_invalid_json(self, tmp_path, temp_vault_file):
        """Test error handling for invalid JSON file."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("{ invalid json ")
        
        result = runner.invoke(
            app,
            ["vault-add", "--from-file", str(invalid_file), "--vault", temp_vault_file]
        )
        
        assert result.exit_code == 1
        assert "Invalid JSON file" in result.stdout
    
    def test_not_an_array(self, tmp_path, temp_vault_file):
        """Test error when JSON is not an array."""
        not_array_file = tmp_path / "not_array.json"
        not_array_file.write_text('{"id": "test", "username": "user", "password": "pass"}')
        
        result = runner.invoke(
            app,
            ["vault-add", "--from-file", str(not_array_file), "--vault", temp_vault_file]
        )
        
        assert result.exit_code == 1
        assert "must contain an array" in result.stdout
    
    def test_missing_required_fields(self, tmp_path, temp_vault_file):
        """Test skipping entries with missing required fields."""
        credentials = [
            {
                "id": "complete",
                "username": "user",
                "password": "pass"
            },
            {
                "id": "missing-password",
                "username": "user"
                # Missing password
            },
            {
                "username": "user",
                "password": "pass"
                # Missing id
            }
        ]
        
        creds_file = tmp_path / "incomplete.json"
        creds_file.write_text(json.dumps(credentials, indent=2))
        
        result = runner.invoke(
            app,
            ["vault-add", "--from-file", str(creds_file), "--vault", temp_vault_file]
        )
        
        assert result.exit_code == 1  # Should fail due to errors
        assert "Skipping entry" in result.stdout
        assert "Missing required fields" in result.stdout
        assert "Added: 1" in result.stdout
        assert "Failed: 2" in result.stdout
    
    def test_empty_array(self, tmp_path, temp_vault_file):
        """Test importing empty credentials array."""
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("[]")
        
        result = runner.invoke(
            app,
            ["vault-add", "--from-file", str(empty_file), "--vault", temp_vault_file]
        )
        
        assert result.exit_code == 0
        assert "Import Summary:" in result.stdout
        assert "Added: 0" in result.stdout
    
    def test_with_optional_description(self, tmp_path, temp_vault_file):
        """Test credentials with and without description."""
        credentials = [
            {
                "id": "with-desc",
                "username": "user1",
                "password": "pass1",
                "description": "Has description"
            },
            {
                "id": "without-desc",
                "username": "user2",
                "password": "pass2"
            }
        ]
        
        creds_file = tmp_path / "mixed.json"
        creds_file.write_text(json.dumps(credentials, indent=2))
        
        result = runner.invoke(
            app,
            ["vault-add", "--from-file", str(creds_file), "--vault", temp_vault_file]
        )
        
        assert result.exit_code == 0
        assert "Added: 2" in result.stdout
    
    def test_mixed_add_and_update(self, tmp_path, temp_vault_file):
        """Test importing with some new and some existing credentials."""
        # First batch
        first_batch = [
            {"id": "existing-1", "username": "user1", "password": "pass1"}
        ]
        creds_file = tmp_path / "creds.json"
        creds_file.write_text(json.dumps(first_batch, indent=2))
        
        runner.invoke(
            app,
            ["vault-add", "--from-file", str(creds_file), "--vault", temp_vault_file]
        )
        
        # Second batch with mixed new and existing
        second_batch = [
            {"id": "existing-1", "username": "user1", "password": "newpass1"},  # Update
            {"id": "new-1", "username": "user2", "password": "pass2"}  # Add
        ]
        creds_file.write_text(json.dumps(second_batch, indent=2))
        
        result = runner.invoke(
            app,
            ["vault-add", "--from-file", str(creds_file), "--vault", temp_vault_file]
        )
        
        assert result.exit_code == 0
        assert "Added: 1" in result.stdout
        assert "Updated: 1" in result.stdout
    
    def test_single_mode_still_works(self, temp_vault_file):
        """Test that single credential mode still works."""
        result = runner.invoke(
            app,
            [
                "vault-add",
                "--id", "single-test",
                "--username", "user",
                "--password", "pass",
                "--vault", temp_vault_file
            ]
        )
        
        assert result.exit_code == 0
        assert "Added:" in result.stdout or "Credential 'single-test'" in result.stdout
    
    def test_requires_either_file_or_params(self, temp_vault_file):
        """Test that command requires either --from-file or manual parameters."""
        result = runner.invoke(
            app,
            ["vault-add", "--vault", temp_vault_file]
        )
        
        assert result.exit_code == 1
        assert "Either provide --from-file or all of --id, --username, and --password" in result.stdout
    
    def test_verify_credentials_after_import(self, temp_credentials_file, temp_vault_file):
        """Test that imported credentials can be retrieved."""
        # Import
        runner.invoke(
            app,
            ["vault-add", "--from-file", str(temp_credentials_file), "--vault", temp_vault_file]
        )
        
        # Verify with vault-list
        result = runner.invoke(
            app,
            ["vault-list", "--vault", temp_vault_file]
        )
        
        assert result.exit_code == 0
        assert "test-mysql" in result.stdout
        assert "test-postgres" in result.stdout
        assert "root" in result.stdout
        assert "postgres" in result.stdout
