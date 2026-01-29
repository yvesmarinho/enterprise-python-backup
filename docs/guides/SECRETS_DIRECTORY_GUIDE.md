# .secrets/ Directory Management Guide

## Purpose
This directory stores **encrypted and sensitive files** that should **NEVER** be committed to version control.

## Contents
- `credentials.json.enc` - Encrypted database credentials (Fernet encryption)
- `vault.json.enc` - Encrypted vault (T-SECURITY-001 ✅)
- `vya_backupbd.json` - Configuration file with database instances
- `logs/` - Log files with sensitive information
- `backups/` - Temporary backups during deployment

## Security Rules

### 🔴 NEVER commit to git
All files in this directory (except `.gitignore` and `README.md`) are automatically ignored by git.

### 🔒 File Permissions
All sensitive files should have `0600` permissions (read/write for owner only):
```bash
chmod 600 .secrets/credentials.json.enc
chmod 600 .secrets/vault.json.enc
chmod 600 .secrets/vya_backupbd.json
```

### 🔐 Encryption
- All credentials use Fernet encryption (AES-128-CBC + HMAC-SHA256)
- Keys derived from hostname (non-portable by design)
- See `VaultManager` and `CredentialsManager` classes for implementation

## Usage

### Vault Commands (Recommended)

#### Add/Update Single Credential
```bash
vya-backupdb vault-add \
  --id mysql-prod \
  --username root \
  --password <secure-password> \
  --description "Production MySQL server"
```

#### Import Multiple Credentials from JSON
```bash
# Import credentials in batch from JSON file
vya-backupdb vault-add --from-file credentials.json
```

**JSON Format:**
```json
[
  {
    "id": "mysql-prod",
    "username": "root",
    "password": "SecureP@ss123",
    "description": "Production MySQL Server"
  },
  {
    "id": "postgresql-prod",
    "username": "postgres",
    "password": "PostgresP@ss789",
    "description": "Production PostgreSQL Server"
  }
]
```

**Example File:** See [examples/credentials_import.json](../../examples/credentials_import.json)

#### Get Credential
```bash
# Without password
vya-backupdb vault-get --id mysql-prod

# With password visible
vya-backupdb vault-get --id mysql-prod --show-password
```

#### List All Credentials
```bash
vya-backupdb vault-list
```

#### Remove Credential
```bash
# With confirmation
vya-backupdb vault-remove --id mysql-old

# Force removal (no confirmation)
vya-backupdb vault-remove --id mysql-old --force
```

#### Vault Information
```bash
vya-backupdb vault-info
```

### Legacy Credentials (Deprecated)
```bash
# Old method (still supported for backward compatibility)
python -m python_backup.cli credentials add \
  --id-dbms 1 \
  --username postgres \
  --password <secure-password>

python -m python_backup.cli credentials list
```

## Backup Strategy

### Production Servers
1. Backup `.secrets/` directory separately
2. Store encrypted backup in secure location
3. Never backup to public cloud without additional encryption

**Backup Command**:
```bash
# Create encrypted tar archive
tar czf secrets-backup-$(date +%Y%m%d).tar.gz .secrets/
chmod 600 secrets-backup-*.tar.gz

# Move to secure location
mv secrets-backup-*.tar.gz /secure/backup/location/
```

### Development
1. Use example files (`config.example.yaml`)
2. Copy and modify for local dev
3. Never commit real credentials

**Development Setup**:
```bash
# Copy example config
cp config/config.example.yaml .secrets/vya_backupbd.json

# Edit with your dev credentials
vim .secrets/vya_backupbd.json

# Migrate to vault
python scripts/utils/migrate_to_vault.py
```

## Recovery

### Scenario 1: Lost Vault on Same Machine
If vault is lost but machine is the same:
```bash
# Keys are hostname-based, so re-create from backup
tar xzf secrets-backup-YYYYMMDD.tar.gz
chmod 600 .secrets/vault.json.enc

# Verify
vya-backupdb vault-list
```

### Scenario 2: New Machine or Lost Backup
If moving to new machine or backup lost:
1. Update `vya_backupbd.json` with plain text credentials
2. Run migration to re-encrypt:
   ```bash
   python scripts/utils/migrate_to_vault.py --dry-run  # Preview
   python scripts/utils/migrate_to_vault.py            # Migrate
   ```
3. Verify vault:
   ```bash
   vya-backupdb vault-info
   vya-backupdb vault-list
   ```

### Scenario 3: Emergency Access
If vault is corrupted:
1. Fallback to `vya_backupbd.json` (system supports fallback)
2. Restore from backup
3. Re-create vault from scratch

## File Structure

```
.secrets/
├── .gitignore              # Ensures files not committed
├── vault.json.enc          # 🔐 Encrypted vault (2.0 KB)
├── credentials.json.enc    # 🔐 Legacy encrypted credentials
├── vya_backupbd.json       # ⚠️  Config with instances (plain)
├── logs/                   # 📝 Log files
└── backups/                # 💾 Temporary backups
```

### File Descriptions

**vault.json.enc** (New - Recommended):
- Complete file encryption
- Metadata tracking (created_at, updated_at)
- Cache support
- CLI friendly
- Size: ~2.0 KB

**credentials.json.enc** (Legacy):
- Individual credential encryption
- Backward compatibility
- Deprecated in favor of vault
- Size: varies

**vya_backupbd.json**:
- Database instance configuration
- Connection details
- Backup settings
- ⚠️ Contains some sensitive data (migrate to vault recommended)

## Security Best Practices

### 1. Regular Credential Rotation
```bash
# Every 90 days recommended
vya-backupdb vault-add --id mysql-prod --username root --password <NEW_PASSWORD>
vya-backupdb test-connection --instance mysql-1
```

See: [CREDENTIAL_ROTATION_GUIDE.md](../CREDENTIAL_ROTATION_GUIDE.md)

### 2. File Permissions Audit
```bash
# Check permissions
ls -la .secrets/

# Fix if needed
chmod 700 .secrets/
chmod 600 .secrets/*.enc
chmod 600 .secrets/vya_backupbd.json
```

### 3. Backup Verification
```bash
# Test restore in safe environment
mkdir /tmp/secrets-test
tar xzf secrets-backup-YYYYMMDD.tar.gz -C /tmp/secrets-test
vya-backupdb vault-list  # Should work
rm -rf /tmp/secrets-test
```

### 4. Access Logging
```bash
# Monitor access to .secrets/
sudo auditctl -w /path/to/.secrets/ -p rwa -k secrets_access

# View logs
sudo ausearch -k secrets_access
```

## Migration Path

### From vya_backupbd.json to Vault

**Step 1**: Preview migration
```bash
python scripts/utils/migrate_to_vault.py --dry-run
```

**Step 2**: Execute migration
```bash
python scripts/utils/migrate_to_vault.py
```

**Step 3**: Verify
```bash
vya-backupdb vault-list
vya-backupdb vault-info
```

**Step 4**: Test connections
```bash
vya-backupdb test-connection --instance mysql-1
vya-backupdb test-connection --instance postgresql-2
```

**Step 5**: Update application to use vault
- Modify `config/loader.py` to prioritize vault
- Keep vya_backupbd.json as fallback
- See: T-VAULT-INTEGRATION task

## Troubleshooting

### Issue: ImportError - cannot import name 'main'
**Cause**: Package not installed or needs reinstallation after code changes

**Solution**:
```bash
# Using UV (recommended)
uv pip install -e .

# Using standard pip
pip install -e .

# Verify
vya-backupdb --help
```

**Documentation**: See [CLI_IMPORT_ERROR.md](../troubleshooting/CLI_IMPORT_ERROR.md) for detailed troubleshooting.

### Issue: Cannot decrypt vault
**Cause**: Wrong hostname or corrupted file

**Solution**:
```bash
# Check hostname
hostname

# Verify file
ls -lh .secrets/vault.json.enc

# If corrupted, restore from backup
tar xzf secrets-backup-YYYYMMDD.tar.gz .secrets/vault.json.enc
```

### Issue: Permission denied
**Cause**: Wrong file permissions

**Solution**:
```bash
chmod 600 .secrets/vault.json.enc
chmod 700 .secrets/
```

### Issue: Vault not found
**Cause**: File doesn't exist

**Solution**:
```bash
# Create new vault by adding first credential
vya-backupdb vault-add --id test --username user --password pass

# Or restore from backup
tar xzf secrets-backup-YYYYMMDD.tar.gz
```

### Issue: Wrong credentials after migration
**Cause**: Migration script error

**Solution**:
```bash
# Remove vault and retry
rm .secrets/vault.json.enc

# Run migration again
python scripts/utils/migrate_to_vault.py
```

## Audit Trail

### Security Audits
- **2026-01-15**: Complete security audit - See [SECURITY_AUDIT_2026-01-15.md](../SECURITY_AUDIT_2026-01-15.md)
- **2026-01-15**: Vault system implemented - See [VAULT_SYSTEM_GUIDE.md](VAULT_SYSTEM_GUIDE.md)

### Credential Rotation History
Track in: [CREDENTIAL_ROTATION_GUIDE.md](../CREDENTIAL_ROTATION_GUIDE.md)

## Related Documentation

- [VAULT_SYSTEM_GUIDE.md](VAULT_SYSTEM_GUIDE.md) - Complete vault system documentation
- [CREDENTIAL_ROTATION_GUIDE.md](../CREDENTIAL_ROTATION_GUIDE.md) - Credential rotation procedures
- [SECURITY_AUDIT_2026-01-15.md](../SECURITY_AUDIT_2026-01-15.md) - Security audit report

## Implementation References

### Code Files
- `src/python_backup/security/vault.py` - VaultManager class
- `src/python_backup/security/credentials.py` - CredentialsManager (legacy)
- `src/python_backup/security/encryption.py` - EncryptionManager
- `scripts/utils/migrate_to_vault.py` - Migration script

### Tests
- `tests/unit/security/test_vault.py` - Vault unit tests (29 tests)
- `tests/unit/security/test_credentials.py` - Credentials tests
- `tests/unit/security/test_encryption.py` - Encryption tests

---

**Created**: 2026-01-15  
**Last Updated**: 2026-01-26  
**Security Level**: 🔴 CRITICAL  
**Maintained By**: DevOps Team
