# Configuration Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      VYA BackupDB System                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│   Credentials (Vault)    │    │  Configuration (YAML)    │
│  .secrets/vault.json.enc │    │  config/config.yaml      │
└──────────────────────────┘    └──────────────────────────┘
│ Encrypted Storage        │    │ Plain Text Config        │
│ - username               │    │ - host                   │
│ - password               │    │ - port                   │
│ - description            │    │ - type                   │
│ - created_at             │    │ - database filters       │
│ - updated_at             │    │ - SSL settings           │
│                          │    │ - credential_name ───────┼─┐
└──────────────────────────┘    └──────────────────────────┘ │
              ▲                               ▲               │
              │                               │               │
              │                               │               │
              └───────────────┬───────────────┘               │
                              │                               │
                              ▼                               │
                    ┌──────────────────┐                      │
                    │  Backup Executor │                      │
                    └──────────────────┘                      │
                              │                               │
                              │                               │
              ┌───────────────┼───────────────┐              │
              │               │               │              │
              ▼               ▼               ▼              │
        ┌─────────┐     ┌─────────┐     ┌─────────┐         │
        │ MySQL   │     │ PostgreSQL    │ Files   │         │
        │ Adapter │     │ Adapter │     │ Adapter │         │
        └─────────┘     └─────────┘     └─────────┘         │
              │               │               │              │
              ▼               ▼               ▼              │
        Database        Database        Filesystem           │
         Server          Server          Backup              │
                                                             │
┌────────────────────────────────────────────────────────────┘
│ Credential Lookup Flow:
│ 1. Read config.yaml → get credential_name: "mysql-prod"
│ 2. Query vault.json.enc → get credentials for "mysql-prod"
│ 3. Decrypt username/password
│ 4. Connect to database with credentials + config settings
└─────────────────────────────────────────────────────────────
```

## Two-File System

### File 1: Vault (Credentials Only)

**Location:** `.secrets/vault.json.enc`

**Content (Encrypted):**
```json
{
  "version": "1.0.0",
  "credentials": {
    "mysql-prod": {
      "username": "gAAAAABl...",  // Encrypted
      "password": "gAAAAABl...",  // Encrypted
      "metadata": {
        "created_at": "2026-01-26T10:00:00Z",
        "updated_at": "2026-01-26T10:00:00Z",
        "description": "Production MySQL Server"
      }
    },
    "postgresql-prod": {
      "username": "gAAAAABl...",  // Encrypted
      "password": "gAAAAABl...",  // Encrypted
      "metadata": {
        "description": "Production PostgreSQL Server"
      }
    }
  }
}
```

**Management:**
```bash
vya-backupdb vault-add --id mysql-prod --username root --password pass
vya-backupdb vault-list
vya-backupdb vault-get --id mysql-prod
vya-backupdb vault-remove --id mysql-prod
```

### File 2: Config (Instance Settings)

**Location:** `config/config.yaml`

**Content (Plain Text):**
```yaml
databases:
  - id: prod-mysql-01
    type: mysql
    host: mysql.example.com
    port: 3306
    enabled: true
    credential_name: mysql-prod  # ← References vault credential
    
    # Database filtering
    database: []  # Whitelist (empty = all)
    db_ignore:    # Blacklist
      - information_schema
      - mysql
      - sys
    
    ssl_enabled: false

  - id: prod-postgres-01
    type: postgresql
    host: postgres.example.com
    port: 5432
    credential_name: postgresql-prod  # ← References vault credential
    database: []
    db_ignore:
      - postgres
      - template0
    ssl_enabled: false
```

## Data Flow

### Backup Execution Flow

```
┌──────────────────────────────────────────────────────────────┐
│ 1. User Command                                              │
│    $ vya-backupdb backup --instance prod-mysql-01           │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. Load Configuration                                        │
│    - Read config/config.yaml                                 │
│    - Find instance: prod-mysql-01                            │
│    - Extract: host, port, credential_name, filters           │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. Load Credentials from Vault                              │
│    - credential_name: "mysql-prod"                           │
│    - Decrypt vault.json.enc                                  │
│    - Get username, password                                  │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. Build Connection                                          │
│    - Host: mysql.example.com (from config)                   │
│    - Port: 3306 (from config)                                │
│    - Username: root (from vault)                             │
│    - Password: ••••• (from vault)                            │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│ 5. List Databases                                            │
│    - Connect to database                                     │
│    - SHOW DATABASES / \l                                     │
│    - Result: [db1, db2, db3, mysql, information_schema]     │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│ 6. Apply Filters                                             │
│    - database: [] (empty = all)                              │
│    - db_ignore: [mysql, information_schema]                  │
│    - Result: [db1, db2, db3]                                 │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│ 7. Execute Backup                                            │
│    - For each database: db1, db2, db3                        │
│    - Run mysqldump / pg_dump                                 │
│    - Save to: /var/backups/vya_backupdb/...                  │
└──────────────────────────────────────────────────────────────┘
```

## Credential Reuse Pattern

One credential, multiple instances with different filters:

```yaml
# config/config.yaml
databases:
  # Instance 1: All databases except test
  - id: mysql-all
    host: mysql.example.com
    port: 3306
    credential_name: mysql-prod  # ← Same credential
    database: []
    db_ignore: [test_db, dev_db]

  # Instance 2: Only production databases
  - id: mysql-prod-only
    host: mysql.example.com
    port: 3306
    credential_name: mysql-prod  # ← Same credential, different filters
    database: [app_production, app_analytics]
    db_ignore: []

  # Instance 3: Different server, same credential
  - id: mysql-replica
    host: mysql-replica.example.com
    port: 3306
    credential_name: mysql-prod  # ← Same credential, different host
    database: []
    db_ignore: []
```

**Benefits:**
- Single credential rotation affects all instances
- Different backup strategies per instance
- Flexible filtering without credential duplication

## Security Layers

```
┌─────────────────────────────────────────────────────────┐
│ Layer 1: File System Permissions                       │
│ - vault.json.enc: 600 (owner read/write only)          │
│ - config.yaml: 600 (owner read/write only)             │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 2: Encryption                                     │
│ - Fernet (AES-128-CBC + HMAC-SHA256)                    │
│ - Key derived from hostname                             │
│ - Non-portable by design                                │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 3: Separation of Concerns                        │
│ - Credentials: vault.json.enc (encrypted)               │
│ - Config: config.yaml (plain, no secrets)              │
│ - Different backup/access patterns                      │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 4: Access Control                                │
│ - CLI commands require proper permissions               │
│ - Vault operations logged                               │
│ - Audit trail in metadata                               │
└─────────────────────────────────────────────────────────┘
```

## Configuration Update Workflow

### Scenario 1: Change Database Filters

**What:** Add/remove databases from backup

**Steps:**
1. Edit `config/config.yaml`
2. Update `database` or `db_ignore` fields
3. Test: `vya-backupdb test-connection --instance <id>`
4. No credential changes needed ✅

**Example:**
```yaml
# Before
database: []
db_ignore: [test_db]

# After
database: [app_production, app_analytics]  # Only these
db_ignore: []
```

### Scenario 2: Rotate Credentials

**What:** Change username/password

**Steps:**
1. Update vault: `vya-backupdb vault-add --id mysql-prod --username root --password NewPass`
2. Test: `vya-backupdb test-connection --instance prod-mysql-01`
3. No config changes needed ✅

### Scenario 3: Add New Instance

**What:** Add new database server

**Steps:**
1. Add credential to vault (if new):
   ```bash
   vya-backupdb vault-add --id mysql-new --username user --password pass
   ```

2. Add instance to config:
   ```yaml
   # config/config.yaml
   databases:
     - id: new-mysql
       type: mysql
       host: new-server.example.com
       port: 3306
       credential_name: mysql-new
       database: []
       db_ignore: []
   ```

3. Test:
   ```bash
   vya-backupdb test-connection --instance new-mysql
   ```

### Scenario 4: Change Database Host/Port

**What:** Database server moved to new host

**Steps:**
1. Edit `config/config.yaml`
2. Update `host` and/or `port`
3. Test connection
4. No credential changes needed ✅

**Example:**
```yaml
# Before
host: old-mysql.example.com
port: 3306

# After
host: new-mysql.example.com
port: 3307
```

## Comparison: Legacy vs New System

### Legacy System (vya_backupbd.json)

```json
{
  "db_config": [
    {
      "id_dbms": 1,
      "dbms": "mysql",
      "host": "localhost",
      "port": "3306",
      "user": "backup",              // ❌ Credentials in config
      "secret": "encrypted_password", // ❌ Credentials in config
      "db_ignore": "mysql,sys,information_schema"
    }
  ]
}
```

**Issues:**
- Credentials mixed with configuration
- Hard to rotate credentials
- Single file = single point of failure
- No credential reuse

### New System (Vault + YAML)

**Vault (.secrets/vault.json.enc):**
```json
{
  "credentials": {
    "mysql-prod": {
      "username": "encrypted...",
      "password": "encrypted..."
    }
  }
}
```

**Config (config/config.yaml):**
```yaml
databases:
  - id: prod-mysql-01
    host: localhost
    port: 3306
    credential_name: mysql-prod  # ✅ Reference only
    db_ignore: [mysql, sys, information_schema]
```

**Benefits:**
- ✅ Clear separation of secrets and config
- ✅ Easy credential rotation
- ✅ Credential reuse across instances
- ✅ Config can be version controlled (no secrets)
- ✅ Different backup strategies for same credential

## File Locations

```
enterprise-python-backup/
├── .secrets/                    # Secrets directory (chmod 700)
│   ├── .gitignore              # Ensures secrets not committed
│   ├── vault.json.enc          # ✅ Credentials (encrypted, chmod 600)
│   └── vya_backupbd.json       # ❌ Legacy (deprecated)
│
├── config/                      # Configuration directory
│   ├── config.yaml             # ✅ Your config (chmod 600)
│   └── config.example.yaml     # 📝 Example (safe to commit)
│
└── /var/backups/vya_backupdb/  # Backup destination
    └── {hostname}/
        └── {instance_id}/
            └── {database}/
                └── {date}/
```

## Related Documentation

- [QUICK_SETUP_GUIDE.md](../guides/QUICK_SETUP_GUIDE.md) - Quick setup walkthrough
- [VAULT_SYSTEM_GUIDE.md](../guides/VAULT_SYSTEM_GUIDE.md) - Vault management
- [DATABASE_FILTERING_SPECIFICATION.md](../technical/DATABASE_FILTERING_SPECIFICATION.md) - Filtering rules
- [SECRETS_DIRECTORY_GUIDE.md](../guides/SECRETS_DIRECTORY_GUIDE.md) - Security practices

---

**Version**: 2.0.0  
**Updated**: 2026-01-26
