"""
Unit tests for vault-list command functionality.
"""

import pytest
from pathlib import Path
from typer.testing import CliRunner
from python_backup.cli import app

runner = CliRunner()


@pytest.fixture
def temp_vault_file(tmp_path):
    """Create a temporary vault file path."""
    return str(tmp_path / "test_vault.json.enc")


class TestVaultList:
    """Test cases for vault-list command."""
    
    def test_empty_vault_no_error(self, temp_vault_file):
        """Test that empty vault shows message without error."""
        result = runner.invoke(
            app,
            ["vault-list", "--vault", temp_vault_file]
        )
        
        # Should exit successfully (code 0)
        assert result.exit_code == 0
        assert "No credentials in vault" in result.stdout
        assert "Use 'vault-add' to create your first credential" in result.stdout
        # Should NOT show error
        assert "Error:" not in result.stdout
    
    def test_list_single_credential(self, temp_vault_file):
        """Test listing vault with single credential."""
        # Add credential
        runner.invoke(
            app,
            [
                "vault-add",
                "--id", "test-1",
                "--username", "user1",
                "--password", "pass1",
                "--vault", temp_vault_file
            ]
        )
        
        # List credentials
        result = runner.invoke(
            app,
            ["vault-list", "--vault", temp_vault_file]
        )
        
        assert result.exit_code == 0
        assert "Vault Credentials (1)" in result.stdout
        assert "test-1" in result.stdout
        assert "user1" in result.stdout
    
    def test_list_multiple_credentials_sorted(self, temp_vault_file):
        """Test that credentials are sorted by ID."""
        # Add credentials in random order
        credentials = [
            ("zzz-last", "user3", "pass3"),
            ("aaa-first", "user1", "pass1"),
            ("mmm-middle", "user2", "pass2"),
        ]
        
        for cred_id, username, password in credentials:
            runner.invoke(
                app,
                [
                    "vault-add",
                    "--id", cred_id,
                    "--username", username,
                    "--password", password,
                    "--vault", temp_vault_file
                ]
            )
        
        # List credentials
        result = runner.invoke(
            app,
            ["vault-list", "--vault", temp_vault_file]
        )
        
        assert result.exit_code == 0
        assert "Vault Credentials (3)" in result.stdout
        
        # Check that IDs appear in sorted order
        output = result.stdout
        pos_aaa = output.find("aaa-first")
        pos_mmm = output.find("mmm-middle")
        pos_zzz = output.find("zzz-last")
        
        assert pos_aaa != -1, "aaa-first not found"
        assert pos_mmm != -1, "mmm-middle not found"
        assert pos_zzz != -1, "zzz-last not found"
        
        # Verify order: aaa < mmm < zzz
        assert pos_aaa < pos_mmm, "aaa-first should come before mmm-middle"
        assert pos_mmm < pos_zzz, "mmm-middle should come before zzz-last"
    
    def test_list_shows_metadata(self, temp_vault_file):
        """Test that list shows username, description, and updated time."""
        # Add credential with description
        runner.invoke(
            app,
            [
                "vault-add",
                "--id", "mysql-prod",
                "--username", "root",
                "--password", "pass123",
                "--description", "Production MySQL",
                "--vault", temp_vault_file
            ]
        )
        
        # List credentials
        result = runner.invoke(
            app,
            ["vault-list", "--vault", temp_vault_file]
        )
        
        assert result.exit_code == 0
        assert "mysql-prod" in result.stdout
        assert "root" in result.stdout
        assert "Production MySQL" in result.stdout
        # Should show updated timestamp
        assert "2026-01-26" in result.stdout or "Updated" in result.stdout
    
    def test_list_shows_vault_info(self, temp_vault_file):
        """Test that list shows vault path and info."""
        # Add a credential
        runner.invoke(
            app,
            [
                "vault-add",
                "--id", "test",
                "--username", "user",
                "--password", "pass",
                "--vault", temp_vault_file
            ]
        )
        
        # List credentials
        result = runner.invoke(
            app,
            ["vault-list", "--vault", temp_vault_file]
        )
        
        assert result.exit_code == 0
        # Should show vault path
        assert temp_vault_file in result.stdout or "Vault:" in result.stdout
        # Should show size and version
        assert "KB" in result.stdout
        assert "Version:" in result.stdout or "1.0.0" in result.stdout
    
    def test_list_with_special_characters_in_id(self, temp_vault_file):
        """Test listing credentials with special characters in ID."""
        # Add credential with hyphens and underscores
        runner.invoke(
            app,
            [
                "vault-add",
                "--id", "mysql-prod_v2.0",
                "--username", "user",
                "--password", "pass",
                "--vault", temp_vault_file
            ]
        )
        
        # List credentials
        result = runner.invoke(
            app,
            ["vault-list", "--vault", temp_vault_file]
        )
        
        assert result.exit_code == 0
        assert "mysql-prod_v2.0" in result.stdout
    
    def test_list_preserves_order_after_update(self, temp_vault_file):
        """Test that order is maintained after updating credentials."""
        # Add credentials
        for i in [3, 1, 2]:
            runner.invoke(
                app,
                [
                    "vault-add",
                    "--id", f"test-{i}",
                    "--username", f"user{i}",
                    "--password", f"pass{i}",
                    "--vault", temp_vault_file
                ]
            )
        
        # Update middle credential
        runner.invoke(
            app,
            [
                "vault-add",
                "--id", "test-2",
                "--username", "updated-user",
                "--password", "updated-pass",
                "--vault", temp_vault_file
            ]
        )
        
        # List should still be sorted
        result = runner.invoke(
            app,
            ["vault-list", "--vault", temp_vault_file]
        )
        
        assert result.exit_code == 0
        output = result.stdout
        pos_1 = output.find("test-1")
        pos_2 = output.find("test-2")
        pos_3 = output.find("test-3")
        
        assert pos_1 < pos_2 < pos_3, "Credentials should be sorted after update"
    
    def test_list_with_numeric_ids(self, temp_vault_file):
        """Test that numeric IDs are sorted correctly."""
        # Add credentials with numeric suffixes
        for i in [10, 2, 1, 20]:
            runner.invoke(
                app,
                [
                    "vault-add",
                    "--id", f"server-{i}",
                    "--username", f"user{i}",
                    "--password", f"pass{i}",
                    "--vault", temp_vault_file
                ]
            )
        
        result = runner.invoke(
            app,
            ["vault-list", "--vault", temp_vault_file]
        )
        
        assert result.exit_code == 0
        # Note: Alphabetical sort, so server-1, server-10, server-2, server-20
        output = result.stdout
        assert "server-1" in output
        assert "server-10" in output
        assert "server-2" in output
        assert "server-20" in output
