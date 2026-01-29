# Quick Setup Guide - VYA BackupDB

## Overview

VYA BackupDB uses a **two-file configuration system**:

1. **Vault** (`.secrets/vault.json.enc`) - Stores credentials (username/password)
2. **Config** (`config/config.yaml`) - Stores instance settings (host, port, filters)

This separation provides better security and flexibility.

## Quick Start (5 minutes)

### Step 1: Add Credentials to Vault

```bash
# Add MySQL credential
vya-backupdb vault-add \
  --id mysql-prod \
  --username root \
  --password YourSecurePassword123 \
  --description "Production MySQL Server"

# Add PostgreSQL credential
vya-backupdb vault-add \
  --id postgresql-prod \
  --username postgres \
  --password YourSecurePassword456 \
  --description "Production PostgreSQL Server"

# Verify credentials
vya-backupdb vault-list
```

### Step 2: Create Configuration File

```bash
# Copy example config
cp config/config.example.yaml config/config.yaml

# Edit with your settings
vim config/config.yaml
```

**Minimal config.yaml:**
```yaml
application_name: vya-backupdb
version: "2.0.0"
environment: production

databases:
  - id: prod-mysql-01
    type: mysql
    host: localhost
    port: 3306
    enabled: true
    credential_name: mysql-prod  # ← References vault credential
    database: []  # All databases
    db_ignore:    # Exclude system databases
      - information_schema
      - performance_schema
      - mysql
      - sys
    ssl_enabled: false

storage:
  base_path: /var/backups/vya_backupdb
  structure: "{hostname}/{db_id}/{db_name}/{date}"
  compression_level: 6

retention:
  strategy: gfs
  daily_keep: 7
  weekly_keep: 4
  monthly_keep: 12

logging:
  level: INFO
  format: json
  output: file
  file_path: /var/log/vya_backupdb/app.log
```

### Step 3: Test Configuration

```bash
# Validate config
vya-backupdb config-validate

# Test database connection
vya-backupdb test-connection --instance prod-mysql-01

# View configuration
vya-backupdb config-show
```

### Step 4: Run Backup

```bash
# Backup specific instance
vya-backupdb backup --instance prod-mysql-01

# Backup all enabled instances
vya-backupdb backup --all
```

## Configuration Details

### Credential Reference

In `config.yaml`, reference vault credentials using `credential_name`:

```yaml
databases:
  - id: prod-mysql-01
    credential_name: mysql-prod  # ← Must match vault credential ID
```

### Database Filtering

Three filtering modes:

#### 1. All Databases (Default)
```yaml
database: []     # Empty = all databases
db_ignore: []    # No exclusions
```

#### 2. Blacklist Mode (Exclude Specific)
```yaml
database: []     # All databases
db_ignore:       # Except these
  - test_db
  - dev_db
  - information_schema
```

#### 3. Whitelist Mode (Include Specific)
```yaml
database:        # ONLY these databases
  - app_production
  - app_analytics
db_ignore: []    # Ignore blacklist
```

**Precedence Rules:**
1. If `database` has values → backup ONLY those (whitelist)
2. Else apply `db_ignore` exclusions (blacklist)
3. Always exclude system databases (information_schema, mysql, etc.)

### Multiple Instances with Same Credentials

You can reuse vault credentials for multiple instances:

```yaml
databases:
  # Instance 1: Backup all databases
  - id: mysql-all
    host: mysql.example.com
    port: 3306
    credential_name: mysql-prod  # Same credential
    database: []
    db_ignore: [test_db, dev_db]

  # Instance 2: Backup only specific databases
  - id: mysql-specific
    host: mysql.example.com
    port: 3306
    credential_name: mysql-prod  # Same credential, different filters
    database: [app_production]
    db_ignore: []
```

### SSL Configuration

For SSL/TLS connections:

```yaml
databases:
  - id: prod-mysql-ssl
    type: mysql
    host: secure-mysql.example.com
    port: 3306
    credential_name: mysql-prod
    ssl_enabled: true
    ssl_ca_cert: /etc/ssl/certs/mysql-ca.pem  # Path to CA certificate
```

## File Structure

```
enterprise-python-backup/
├── .secrets/
│   └── vault.json.enc          # ← Credentials (encrypted)
│
├── config/
│   ├── config.yaml             # ← Your config (create from example)
│   └── config.example.yaml     # ← Example config
│
└── /var/backups/vya_backupdb/  # ← Backup destination
```

## Security Best Practices

### 1. Protect Configuration Files

```bash
# Set restrictive permissions
chmod 600 config/config.yaml
chmod 600 .secrets/vault.json.enc

# Verify
ls -la config/config.yaml
ls -la .secrets/vault.json.enc
```

### 2. Never Commit Credentials

The `.gitignore` already excludes:
- `config/config.yaml` (your config)
- `.secrets/*.enc` (vault)
- `.secrets/vya_backupbd.json` (legacy)

**Safe to commit:**
- `config/config.example.yaml` (example only, no credentials)

### 3. Rotate Credentials Regularly

```bash
# Update credential in vault
vya-backupdb vault-add \
  --id mysql-prod \
  --username root \
  --password NewSecurePassword789

# Test connection
vya-backupdb test-connection --instance prod-mysql-01

# No changes needed to config.yaml!
```

### 4. Backup Your Vault

```bash
# Backup vault
cp .secrets/vault.json.enc .secrets/vault-backup-$(date +%Y%m%d).json.enc

# Move to secure location
mv .secrets/vault-backup-*.json.enc /secure/backup/location/
```

## Migration from Legacy System

If you have credentials in `.secrets/vya_backupbd.json`:

### Step 1: Extract credentials and add to vault

```bash
# Add each credential to vault
vya-backupdb vault-add \
  --id mysql-legacy \
  --username <from_vya_backupbd.json> \
  --password <from_vya_backupbd.json>
```

### Step 2: Create new config.yaml

Use `config.example.yaml` as template and add your instances.

### Step 3: Test

```bash
vya-backupdb test-connection --instance <instance-id>
```

### Step 4: Remove legacy file (after verification)

```bash
# Backup first
cp .secrets/vya_backupbd.json .secrets/vya_backupbd.json.backup

# Remove (after testing)
rm .secrets/vya_backupbd.json
```

## Troubleshooting

### Issue: "Credential not found in vault"

**Cause:** `credential_name` in config.yaml doesn't match vault credential ID

**Solution:**
```bash
# List vault credentials
vya-backupdb vault-list

# Update config.yaml with correct credential_name
vim config/config.yaml
```

### Issue: "Connection refused"

**Cause:** Wrong host, port, or database not accessible

**Solution:**
```bash
# Test connection manually
mysql -h <host> -P <port> -u <username> -p

# Check config.yaml host/port
vim config/config.yaml
```

### Issue: "No databases found"

**Cause:** All databases excluded by filters

**Solution:**
```bash
# Review filters in config.yaml
# Either:
# 1. Add databases to whitelist (database: [db1, db2])
# 2. Remove from blacklist (db_ignore: [])
```

## Examples

### Example 1: Single MySQL Instance

**Vault:**
```bash
vya-backupdb vault-add --id mysql-app --username app_backup --password SecurePass123
```

**config.yaml:**
```yaml
databases:
  - id: app-mysql
    type: mysql
    host: localhost
    port: 3306
    credential_name: mysql-app
    database: []
    db_ignore: [information_schema, mysql, sys, performance_schema]
```

### Example 2: Multiple Instances, Different Filters

**Vault:**
```bash
vya-backupdb vault-add --id mysql-prod --username root --password Pass123
```

**config.yaml:**
```yaml
databases:
  # All databases except test
  - id: mysql-all
    type: mysql
    host: mysql.example.com
    port: 3306
    credential_name: mysql-prod
    database: []
    db_ignore: [test_db, dev_db]

  # Only production databases
  - id: mysql-prod-only
    type: mysql
    host: mysql.example.com
    port: 3306
    credential_name: mysql-prod
    database: [app_production, app_analytics]
    db_ignore: []
```

### Example 3: Mixed MySQL and PostgreSQL

**Vault:**
```bash
vya-backupdb vault-add --id mysql-prod --username root --password MySQLPass123
vya-backupdb vault-add --id postgres-prod --username postgres --password PGPass456
```

**config.yaml:**
```yaml
databases:
  - id: prod-mysql
    type: mysql
    host: mysql.example.com
    port: 3306
    credential_name: mysql-prod
    database: []
    db_ignore: [information_schema, mysql, sys, performance_schema]

  - id: prod-postgres
    type: postgresql
    host: postgres.example.com
    port: 5432
    credential_name: postgres-prod
    database: []
    db_ignore: [postgres, template0, template1]
```

## Next Steps

- Read [VAULT_SYSTEM_GUIDE.md](../docs/guides/VAULT_SYSTEM_GUIDE.md) for vault details
- Read [DATABASE_FILTERING_SPECIFICATION.md](../docs/technical/DATABASE_FILTERING_SPECIFICATION.md) for filtering rules
- Read [SECRETS_DIRECTORY_GUIDE.md](../docs/guides/SECRETS_DIRECTORY_GUIDE.md) for security best practices

## Support

- **Documentation**: `docs/` directory
- **Examples**: `config/config.example.yaml`
- **Issues**: Report on GitHub

---

**Version**: 2.0.0  
**Updated**: 2026-01-26  
**Author**: DevOps Team
