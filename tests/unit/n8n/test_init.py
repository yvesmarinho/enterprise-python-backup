"""Unit tests for N8N __init__.py package."""


def test_package_version():
    """Test package version is defined."""
    from enterprise_backup.n8n import __version__
    
    assert __version__ == "0.1.0"


def test_module_info():
    """Test module metadata is defined."""
    from enterprise_backup.n8n import MODULE_INFO
    
    assert MODULE_INFO["name"] == "enterprise_backup.n8n"
    assert MODULE_INFO["version"] == "0.1.0"
    assert MODULE_INFO["constitution_version"] == "1.1.0"
    assert "backup_credentials" in MODULE_INFO["capabilities"]
    assert "restore_workflows" in MODULE_INFO["capabilities"]


def test_lazy_imports():
    """Test lazy import functionality."""
    # Import should work without loading all modules
    from enterprise_backup.n8n import N8NBackup, N8NRestore
    
    assert N8NBackup is not None
    assert N8NRestore is not None


def test_all_exports():
    """Test __all__ contains expected exports."""
    from enterprise_backup.n8n import __all__
    
    expected_exports = [
        "__version__",
        "MODULE_INFO",
        "N8NBackup",
        "N8NRestore",
        "BackupType",
        "OperationStatus",
        "n8n_cli",
    ]
    
    for export in expected_exports:
        assert export in __all__
