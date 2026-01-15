#!/usr/bin/env python3
"""
Migration script: vya_backupbd.json credentials → vault.json.enc

Extracts credentials from vya_backupbd.json and migrates them to encrypted vault.
Creates vault entries for:
- SMTP credentials (email_settings.smtp_user + smtp_password)
- Database credentials (db_config[].user + secret for each DBMS)

Usage:
    python scripts/utils/migrate_to_vault.py
    python scripts/utils/migrate_to_vault.py --config /path/to/vya_backupbd.json
    python scripts/utils/migrate_to_vault.py --vault /path/to/vault.json.enc
    python scripts/utils/migrate_to_vault.py --dry-run
"""

import json
import sys
import argparse
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from python_backup.security.vault import VaultManager


def migrate_credentials(config_path: Path, vault_path: Path, dry_run: bool = False):
    """
    Migrate credentials from config to vault.
    
    Args:
        config_path: Path to vya_backupbd.json
        vault_path: Path to vault.json.enc
        dry_run: If True, only show what would be migrated
    """
    # Load configuration
    print(f"Loading configuration: {config_path}")
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Prepare vault
    if not dry_run:
        vault = VaultManager(vault_path)
        # Try to load existing vault (if any)
        vault.load()
        print(f"Vault: {vault_path}")
    else:
        print(f"[DRY-RUN] Would use vault: {vault_path}")
    
    credentials_count = 0
    
    # Migrate SMTP credentials
    if 'email_settings' in config and config['email_settings'].get('enabled'):
        email = config['email_settings']
        smtp_user = email.get('smtp_user', '')
        smtp_password = email.get('smtp_password', '')
        
        if smtp_user and smtp_password:
            credential_id = f"smtp-{email.get('smtp_host', 'server')}"
            description = f"SMTP {email.get('smtp_host')} (port {email.get('smtp_port')})"
            
            print(f"\n[SMTP] {credential_id}")
            print(f"  Username: {smtp_user}")
            print(f"  Password: {'*' * len(smtp_password)}")
            print(f"  Description: {description}")
            
            if not dry_run:
                vault.set(credential_id, smtp_user, smtp_password, description)
                print("  ✓ Migrated")
            
            credentials_count += 1
    
    # Migrate database credentials
    if 'db_config' in config:
        for db in config['db_config']:
            id_dbms = db.get('id_dbms')
            dbms = db.get('dbms', 'unknown')
            host = db.get('host', 'localhost')
            port = db.get('port', '0')
            user = db.get('user', '')
            secret = db.get('secret', '')
            enabled = db.get('enabled', True)
            
            # Skip files type (no credentials)
            if dbms == 'files':
                continue
            
            # Skip disabled databases
            if not enabled:
                print(f"\n[SKIP] {dbms}-{id_dbms} (disabled)")
                continue
            
            if user and secret:
                credential_id = f"{dbms}-{id_dbms}"
                description = f"{dbms.upper()} {host}:{port}"
                
                print(f"\n[{dbms.upper()}] {credential_id}")
                print(f"  Username: {user}")
                print(f"  Password: {'*' * len(secret)}")
                print(f"  Description: {description}")
                print(f"  Enabled: {enabled}")
                
                if not dry_run:
                    vault.set(credential_id, user, secret, description)
                    print("  ✓ Migrated")
                
                credentials_count += 1
    
    # Save vault
    if not dry_run:
        print(f"\nSaving vault...")
        if vault.save():
            print(f"✓ Vault saved successfully")
        else:
            print(f"✗ Failed to save vault")
            return False
    
    # Summary
    print(f"\n{'=' * 60}")
    print(f"Migration Summary:")
    print(f"  Credentials: {credentials_count}")
    if dry_run:
        print(f"  Status: DRY-RUN (nothing saved)")
    else:
        print(f"  Status: COMPLETED")
        print(f"  Vault: {vault_path}")
    print(f"{'=' * 60}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Migrate credentials from vya_backupbd.json to encrypted vault"
    )
    parser.add_argument(
        '--config',
        default='vya_backupbd.json',
        help='Path to vya_backupbd.json (default: vya_backupbd.json)'
    )
    parser.add_argument(
        '--vault',
        default='.secrets/vault.json.enc',
        help='Path to vault file (default: .secrets/vault.json.enc)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be migrated without saving'
    )
    
    args = parser.parse_args()
    
    # Convert to Path objects
    config_path = Path(args.config)
    vault_path = Path(args.vault)
    
    # Validate config exists
    if not config_path.exists():
        print(f"Error: Configuration file not found: {config_path}")
        return 1
    
    # Warn if vault already exists
    if vault_path.exists() and not args.dry_run:
        print(f"Warning: Vault already exists: {vault_path}")
        response = input("Existing credentials will be preserved. Continue? [y/N] ")
        if response.lower() != 'y':
            print("Cancelled by user")
            return 0
    
    # Run migration
    try:
        success = migrate_credentials(config_path, vault_path, args.dry_run)
        return 0 if success else 1
    except Exception as e:
        print(f"\nError during migration: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
