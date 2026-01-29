# Vault Batch Import Guide

## Overview

The `vault-add --from-file` command allows you to import multiple credentials into the vault at once using a JSON file. This is useful for:

- **Migration**: Moving credentials from other systems
- **Backup/Restore**: Restoring credentials from a backup
- **Bulk Setup**: Setting up multiple credentials at once
- **Automation**: Scripting credential management

## JSON File Format

### Basic Structure

```json
[
  {
    "id": "credential-id",
    "username": "username",
    "password": "password",
    "description": "Optional description"
  }
]
```

### Required Fields

- **id**: Unique identifier for the credential (e.g., `mysql-prod`, `smtp-server`)
- **username**: Username for authentication
- **password**: Password for authentication

### Optional Fields

- **description**: Human-readable description of what this credential is for

## Usage

### Basic Import

```bash
vya-backupdb vault-add --from-file credentials.json
```

### Custom Vault Path

```bash
vya-backupdb vault-add --from-file credentials.json --vault /path/to/vault.json.enc
```

## Complete Example

### 1. Create Credentials File

Create a file named `credentials.json`:

```json
[
  {
    "id": "mysql-prod",
    "username": "root",
    "password": "MySecureP@ss123",
    "description": "Production MySQL Server"
  },
  {
    "id": "mysql-dev",
    "username": "dev_user",
    "password": "DevP@ss456",
    "description": "Development MySQL Server"
  },
  {
    "id": "postgresql-prod",
    "username": "postgres",
    "password": "PostgresP@ss789",
    "description": "Production PostgreSQL Server"
  },
  {
    "id": "postgresql-staging",
    "username": "postgres",
    "password": "StagingP@ss321",
    "description": "Staging PostgreSQL Server"
  },
  {
    "id": "smtp-server",
    "username": "notifications@company.com",
    "password": "SmtpP@ss654",
    "description": "SMTP Server for Notifications"
  }
]
```

### 2. Import Credentials

```bash
vya-backupdb vault-add --from-file credentials.json
```

**Output:**
```
VYA BackupDB - Vault Add Credential

Importing credentials from 'credentials.json'...

Adding credential 'mysql-prod'...
Adding credential 'mysql-dev'...
Adding credential 'postgresql-prod'...
Adding credential 'postgresql-staging'...
Adding credential 'smtp-server'...

Import Summary:
  Added: 5
  Updated: 0
  Vault: .secrets/vault.json.enc
```

### 3. Verify Import

```bash
vya-backupdb vault-list
```

## Behavior

### Add vs Update

- **Add**: If a credential with the given `id` doesn't exist, it will be created
- **Update**: If a credential with the given `id` already exists, it will be updated

### Summary Report

After importing, you'll see a summary showing:
- **Added**: Number of new credentials created
- **Updated**: Number of existing credentials modified
- **Failed**: Number of credentials that failed validation

### Error Handling

#### Invalid JSON

```bash
$ vya-backupdb vault-add --from-file invalid.json
✗ Invalid JSON file: Expecting value: line 1 column 1 (char 0)
```

#### Missing Required Fields

```json
[
  {
    "id": "mysql-prod",
    "username": "root"
    // ❌ Missing password
  }
]
```

**Output:**
```
⚠ Skipping entry 1: Missing required fields (id, username, password)

Import Summary:
  Added: 0
  Updated: 0
  Failed: 1
```

#### File Not Found

```bash
$ vya-backupdb vault-add --from-file missing.json
✗ File not found: missing.json
```

## Security Best Practices

### 1. Protect Credentials File

```bash
# Set restrictive permissions
chmod 600 credentials.json

# Store in secure location
mv credentials.json .secrets/
```

### 2. Delete After Import

```bash
# Import
vya-backupdb vault-add --from-file credentials.json

# Verify
vya-backupdb vault-list

# Securely delete
shred -vfz -n 10 credentials.json
```

### 3. Use Secure Transport

```bash
# If transferring between machines, use encrypted transfer
scp credentials.json user@server:/secure/path/

# Or use encrypted archives
tar czf - credentials.json | gpg -c > credentials.tar.gz.gpg
```

## Use Cases

### 1. Migration from Legacy System

```bash
# Export from old system (example)
python old_system_export.py > credentials.json

# Import to vault
vya-backupdb vault-add --from-file credentials.json

# Cleanup
shred -vfz -n 10 credentials.json
```

### 2. Disaster Recovery

```bash
# Restore from backup
tar xzf vault-backup-20260115.tar.gz .secrets/vault.json.enc

# If backup corrupted, use credential export
vya-backupdb vault-add --from-file credentials-backup.json
```

### 3. Multi-Environment Setup

**Production:**
```json
[
  {
    "id": "mysql-prod",
    "username": "prod_user",
    "password": "ProdP@ss123"
  }
]
```

**Staging:**
```json
[
  {
    "id": "mysql-staging",
    "username": "staging_user",
    "password": "StagingP@ss456"
  }
]
```

**Development:**
```json
[
  {
    "id": "mysql-dev",
    "username": "dev_user",
    "password": "DevP@ss789"
  }
]
```

Import all:
```bash
vya-backupdb vault-add --from-file prod-credentials.json
vya-backupdb vault-add --from-file staging-credentials.json
vya-backupdb vault-add --from-file dev-credentials.json
```

### 4. Team Onboarding

Create a template file for new team members:

**credentials-template.json:**
```json
[
  {
    "id": "mysql-dev",
    "username": "YOUR_USERNAME",
    "password": "YOUR_PASSWORD",
    "description": "Development MySQL Server"
  },
  {
    "id": "postgresql-dev",
    "username": "YOUR_USERNAME",
    "password": "YOUR_PASSWORD",
    "description": "Development PostgreSQL Server"
  }
]
```

Team member fills in their credentials and imports:
```bash
vya-backupdb vault-add --from-file my-credentials.json
shred -vfz -n 10 my-credentials.json
```

## Comparison: Single vs Batch

### Single Mode

**Advantages:**
- Interactive
- Immediate feedback per credential
- Good for one-off additions

**Usage:**
```bash
vya-backupdb vault-add --id mysql-prod --username root --password SecureP@ss
```

### Batch Mode

**Advantages:**
- Bulk operations
- Migration-friendly
- Scriptable
- Version controllable (encrypted)

**Usage:**
```bash
vya-backupdb vault-add --from-file credentials.json
```

## Advanced Patterns

### Generate from Configuration

```python
#!/usr/bin/env python3
import json

databases = [
    {"host": "mysql-1.example.com", "user": "root", "pass": "pass1"},
    {"host": "mysql-2.example.com", "user": "root", "pass": "pass2"},
    {"host": "postgres-1.example.com", "user": "postgres", "pass": "pass3"},
]

credentials = [
    {
        "id": f"{db['host'].split('.')[0]}",
        "username": db['user'],
        "password": db['pass'],
        "description": f"Server {db['host']}"
    }
    for db in databases
]

with open('credentials.json', 'w') as f:
    json.dump(credentials, f, indent=2)
```

Run:
```bash
python generate_credentials.py
vya-backupdb vault-add --from-file credentials.json
rm credentials.json
```

### Export and Re-import

```bash
# Export (manually create JSON from vault-list)
vya-backupdb vault-list > credentials-export.txt

# Create JSON manually or with script
# Then re-import
vya-backupdb vault-add --from-file credentials.json
```

## Troubleshooting

### Issue: Import shows 0 added

**Cause**: All credentials already exist

**Solution**: Check with `vault-list`. If updating is intended, this is normal behavior (they'll show in "Updated" count).

### Issue: JSON parse error

**Cause**: Invalid JSON syntax

**Solution**:
```bash
# Validate JSON
python -m json.tool credentials.json

# Or use jq
jq . credentials.json
```

### Issue: Permission denied

**Cause**: File permissions too restrictive

**Solution**:
```bash
chmod 600 credentials.json
```

## Related Commands

- **vault-list**: List all credentials in vault
- **vault-get**: Retrieve specific credential
- **vault-remove**: Remove credential from vault
- **vault-info**: Show vault statistics

## Example Files

- [examples/credentials_import.json](../../../examples/credentials_import.json) - Sample import file with 5 credentials

## References

- [VAULT_SYSTEM_GUIDE.md](VAULT_SYSTEM_GUIDE.md) - Complete vault documentation
- [SECRETS_DIRECTORY_GUIDE.md](SECRETS_DIRECTORY_GUIDE.md) - .secrets/ directory management

---

**Created**: 2026-01-26  
**Last Updated**: 2026-01-26  
**Feature Version**: 2.0.0+  
**Author**: DevOps Team
