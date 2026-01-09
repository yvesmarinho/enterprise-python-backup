# CLI Contract: VYA BackupDB v2.0.0

**Version**: 2.0.0  
**Date**: 2026-01-09  
**Interface Type**: Command Line Interface (Typer)

## Overview

Este documento define o contrato completo da CLI do VYA BackupDB, incluindo comandos, argumentos, opções, exit codes e outputs.

---

## 1. Global Options

Disponíveis para todos os comandos:

```bash
--config PATH          Path to config file [default: config/config.yaml]
--verbose, -v          Enable verbose output
--quiet, -q            Suppress non-error output
--help                 Show help message
--version              Show version and exit
```

---

## 2. Backup Commands

### 2.1 `backup` - Execute backup

**Synopsis**:
```bash
vya-backupdb backup [OPTIONS]
```

**Options**:
```bash
--instance TEXT        Database instance ID (required if --all not used)
--database TEXT        Specific database name (optional, defaults to all)
--all                  Backup all configured instances
--dry-run              Test mode (no actual backup)
--compression INT      Compression level 1-9 [default: 6]
--parallel             Enable parallel backups (future)
--workers INT          Number of parallel workers [default: 4]
```

**Examples**:
```bash
# Backup all databases from instance
vya-backupdb backup --instance prod-mysql-01

# Backup specific database
vya-backupdb backup --instance prod-mysql-01 --database mydb

# Backup multiple databases
vya-backupdb backup --instance prod-mysql-01 --database mydb,otherdb

# Backup all configured instances
vya-backupdb backup --all

# Dry-run (test only)
vya-backupdb backup --instance prod-mysql-01 --dry-run

# Custom compression
vya-backupdb backup --instance prod-mysql-01 --compression 9
```

**Output (Success)**:
```
[2026-01-09 02:00:00] INFO: Starting backup for prod-mysql-01
[2026-01-09 02:00:01] INFO: Connecting to mysql://localhost:3306
[2026-01-09 02:00:02] INFO: Found 3 databases: mydb, testdb, proddb
[2026-01-09 02:00:02] INFO: Excluding system databases: information_schema, mysql
[2026-01-09 02:00:03] INFO: Backing up database: mydb
[2026-01-09 02:00:45] SUCCESS: Backup completed: mydb_20260109_020000_full.sql.gz
[2026-01-09 02:00:45] INFO: Size: 1.5 MB | Duration: 42.3s | Checksum: e3b0c44...
[2026-01-09 02:00:45] INFO: Metadata saved: mydb_20260109_020000_full.metadata.json
[2026-01-09 02:01:30] SUCCESS: All backups completed successfully (3/3)
```

**Exit Codes**:
- `0`: Success (all backups completed)
- `1`: Partial failure (some backups failed)
- `2`: Complete failure (all backups failed)
- `3`: Configuration error
- `4`: Credentials error

---

## 3. Restore Commands

### 3.1 `restore list` - List available backups

**Synopsis**:
```bash
vya-backupdb restore list [OPTIONS]
```

**Options**:
```bash
--instance TEXT        Filter by instance ID
--database TEXT        Filter by database name
--date TEXT            Filter by date (YYYY-MM-DD)
--limit INT            Limit results [default: 20]
```

**Examples**:
```bash
# List all backups
vya-backupdb restore list

# List backups for specific database
vya-backupdb restore list --instance prod-mysql-01 --database mydb

# List backups from specific date
vya-backupdb restore list --date 2026-01-09
```

**Output**:
```
Available Backups:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Instance         Database   Date         Size      Status   File
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
prod-mysql-01    mydb       2026-01-09   1.5 MB    Success  mydb_20260109_020000_full.sql.gz
prod-mysql-01    testdb     2026-01-09   892 KB    Success  testdb_20260109_020100_full.sql.gz
prod-postgres-01 appdb      2026-01-09   3.2 MB    Success  appdb_20260109_020200_full.sql.gz
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 3 backups
```

### 3.2 `restore` - Restore from backup

**Synopsis**:
```bash
vya-backupdb restore [OPTIONS]
```

**Options**:
```bash
--instance TEXT        Database instance ID (required with --database)
--database TEXT        Database name (required with --instance)
--file PATH            Direct path to backup file (alternative to --instance/--database)
--latest               Use latest backup for database
--datetime TEXT        Restore from closest backup to datetime (YYYY-MM-DD HH:MM:SS)
--target-database TEXT Restore to different database name
--dry-run              Validate backup without restoring
--force                Skip confirmation prompt
```

**Examples**:
```bash
# Restore latest backup
vya-backupdb restore --instance prod-mysql-01 --database mydb --latest

# Restore from specific file
vya-backupdb restore --file /var/backups/.../mydb_20260109_020000_full.sql.gz

# Restore to specific datetime
vya-backupdb restore --instance prod-mysql-01 --database mydb --datetime "2026-01-09 10:00:00"

# Restore to different database
vya-backupdb restore --file backup.sql.gz --target-database mydb_restore

# Dry-run (validate only)
vya-backupdb restore --file backup.sql.gz --dry-run
```

**Output (Success)**:
```
[2026-01-09 10:00:00] INFO: Restore requested for prod-mysql-01/mydb
[2026-01-09 10:00:01] INFO: Found backup: mydb_20260109_020000_full.sql.gz (1.5 MB)
[2026-01-09 10:00:02] INFO: Validating backup integrity...
[2026-01-09 10:00:03] SUCCESS: Checksum verified: e3b0c44...
[2026-01-09 10:00:04] WARNING: Database mydb will be dropped and recreated
[2026-01-09 10:00:05] PROMPT: Continue? (y/N): y
[2026-01-09 10:00:06] INFO: Dropping database mydb...
[2026-01-09 10:00:07] INFO: Creating database mydb...
[2026-01-09 10:00:08] INFO: Restoring from backup...
[2026-01-09 10:02:30] SUCCESS: Restore completed successfully
[2026-01-09 10:02:30] INFO: Duration: 2m 26s | Tables: 25 | Rows: ~1.2M
```

**Exit Codes**:
- `0`: Success
- `1`: Restore failed
- `2`: Backup file not found
- `3`: Checksum verification failed
- `4`: Database connection error

---

## 4. Configuration Commands

### 4.1 `config validate` - Validate configuration

**Synopsis**:
```bash
vya-backupdb config validate [OPTIONS]
```

**Options**:
```bash
--config PATH          Path to config file [default: config/config.yaml]
```

**Examples**:
```bash
vya-backupdb config validate
vya-backupdb config validate --config /custom/path/config.yaml
```

**Output (Success)**:
```
✅ Configuration is valid
   - Databases: 3 configured
   - Storage: /var/backups/vya_backupdb (exists, writable)
   - Credentials: 3/3 found and encrypted
   - Retention policy: GFS (7d/4w/12m)
```

**Output (Error)**:
```
❌ Configuration validation failed:
   - databases[0].port: value must be between 1 and 65535
   - storage.base_path: directory does not exist
   - credentials: missing for database 'prod-mysql-01'
```

### 4.2 `config show` - Display configuration

**Synopsis**:
```bash
vya-backupdb config show [OPTIONS]
```

**Options**:
```bash
--config PATH          Path to config file
--format TEXT          Output format: yaml, json [default: yaml]
--no-secrets           Hide sensitive information
```

**Examples**:
```bash
vya-backupdb config show
vya-backupdb config show --format json
vya-backupdb config show --no-secrets
```

### 4.3 `config test-connections` - Test database connections

**Synopsis**:
```bash
vya-backupdb config test-connections [OPTIONS]
```

**Options**:
```bash
--instance TEXT        Test specific instance (optional)
```

**Examples**:
```bash
# Test all configured databases
vya-backupdb config test-connections

# Test specific instance
vya-backupdb config test-connections --instance prod-mysql-01
```

**Output**:
```
Testing Database Connections:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Instance         Type        Status     Latency
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
prod-mysql-01    MySQL 8.0   ✅ OK      12ms
prod-postgres-01 PostgreSQL  ✅ OK      8ms
test-mysql-01    MySQL 8.0   ❌ Failed  Connection refused
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Result: 2/3 successful
```

---

## 5. User Management Commands

### 5.1 `users backup` - Backup database users and permissions

**Synopsis**:
```bash
vya-backupdb users backup [OPTIONS]
```

**Options**:
```bash
--instance TEXT        Database instance ID (required)
--output PATH          Custom output path (optional)
--exclude-user TEXT    Users to exclude (comma-separated) [default: root,mysql.sys,postgres]
--dry-run              Test mode (no actual backup)
```

**Examples**:
```bash
# Backup all users from instance
vya-backupdb users backup --instance prod-mysql-01

# Backup with custom output
vya-backupdb users backup --instance prod-mysql-01 \
  --output /custom/path/users_backup.sql.gz

# Exclude specific users
vya-backupdb users backup --instance prod-mysql-01 \
  --exclude-user root,mysql.sys,test_user

# Dry-run
vya-backupdb users backup --instance prod-mysql-01 --dry-run
```

**Output (Success)**:
```
[2026-01-09 10:00:00] INFO: Starting user backup for prod-mysql-01
[2026-01-09 10:00:01] INFO: Connecting to mysql://localhost:3306
[2026-01-09 10:00:02] INFO: Found 5 users (excluding system users)
[2026-01-09 10:00:03] INFO: Extracting user: myapp_user@'%'
[2026-01-09 10:00:03] INFO: Extracting GRANTs for myapp_user@'%'
[2026-01-09 10:00:04] INFO: Extracting user: readonly_user@'localhost'
[2026-01-09 10:00:04] INFO: Extracting GRANTs for readonly_user@'localhost'
[2026-01-09 10:00:05] SUCCESS: User backup completed
[2026-01-09 10:00:05] INFO: File: /var/backups/.../prod-mysql-01/users_20260109_100000.sql.gz
[2026-01-09 10:00:05] INFO: Size: 15.2 KB | Users: 5 | Duration: 5.1s
[2026-01-09 10:00:05] INFO: Metadata: users_20260109_100000.metadata.json
```

**Exit Codes**:
- `0`: Success
- `1`: Backup failed
- `6`: Connection error

### 5.2 `users list` - List backed-up users

**Synopsis**:
```bash
vya-backupdb users list [OPTIONS]
```

**Options**:
```bash
--instance TEXT        Filter by instance ID
--file PATH            Show users from specific backup file
--date TEXT            Filter by date (YYYY-MM-DD)
```

**Examples**:
```bash
# List all user backups
vya-backupdb users list --instance prod-mysql-01

# List users in specific backup file
vya-backupdb users list --file /var/backups/.../users_20260109_100000.sql.gz
```

**Output**:
```
User Backups for prod-mysql-01:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Date         Size      Users   File
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2026-01-09   15.2 KB   5       users_20260109_100000.sql.gz
2026-01-08   14.8 KB   5       users_20260108_020000.sql.gz
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Users in users_20260109_100000.sql.gz:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
User              Host        Privileges
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
myapp_user        %           ALL on mydb.*
readonly_user     localhost   SELECT on *.*
backup_user       localhost   SELECT, LOCK TABLES, ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 5.3 `users restore` - Restore database users

**Synopsis**:
```bash
vya-backupdb users restore [OPTIONS]
```

**Options**:
```bash
--file PATH            Path to user backup file (required)
--target-instance TEXT Target instance ID (required)
--all                  Restore all users
--user TEXT            Restore specific user only
--skip-existing        Skip users that already exist
--dry-run              Validate without restoring
--force                Skip confirmation prompt
```

**Examples**:
```bash
# Restore all users
vya-backupdb users restore \
  --file /var/backups/.../users_20260109_100000.sql.gz \
  --target-instance staging-mysql-01 \
  --all

# Restore single user
vya-backupdb users restore \
  --file /var/backups/.../users_20260109_100000.sql.gz \
  --target-instance staging-mysql-01 \
  --user myapp_user

# Dry-run (validate only)
vya-backupdb users restore \
  --file backup.sql.gz \
  --target-instance staging-mysql-01 \
  --all \
  --dry-run

# Skip existing users
vya-backupdb users restore \
  --file backup.sql.gz \
  --target-instance staging-mysql-01 \
  --all \
  --skip-existing
```

**Output (Success - All Users)**:
```
[2026-01-09 11:00:00] INFO: User restore requested for staging-mysql-01
[2026-01-09 11:00:01] INFO: Loading user backup: users_20260109_100000.sql.gz
[2026-01-09 11:00:02] INFO: Found 5 users in backup
[2026-01-09 11:00:03] INFO: Target instance: staging-mysql-01 (MySQL 8.0.32)
[2026-01-09 11:00:04] WARNING: This will create 5 users on staging-mysql-01
[2026-01-09 11:00:05] PROMPT: Continue? (y/N): y
[2026-01-09 11:00:06] INFO: Creating user: myapp_user@'%'
[2026-01-09 11:00:07] INFO: Applying GRANTs for myapp_user@'%'
[2026-01-09 11:00:08] INFO: Creating user: readonly_user@'localhost'
[2026-01-09 11:00:09] INFO: Applying GRANTs for readonly_user@'localhost'
[2026-01-09 11:00:15] SUCCESS: User restore completed
[2026-01-09 11:00:15] INFO: Created: 5 users | Skipped: 0 | Failed: 0
```

**Output (Success - Single User)**:
```
[2026-01-09 11:00:00] INFO: User restore requested for staging-mysql-01
[2026-01-09 11:00:01] INFO: Loading user backup: users_20260109_100000.sql.gz
[2026-01-09 11:00:02] INFO: Searching for user: myapp_user
[2026-01-09 11:00:03] SUCCESS: Found user: myapp_user@'%'
[2026-01-09 11:00:04] INFO: Creating user: myapp_user@'%'
[2026-01-09 11:00:05] INFO: Applying GRANTs for myapp_user@'%'
[2026-01-09 11:00:06] SUCCESS: User restored successfully
```

**Exit Codes**:
- `0`: Success
- `1`: Restore failed
- `2`: Backup file not found
- `6`: Connection error
- `9`: Permission error (insufficient privileges to create users)

---

## 6. Credentials Commands

### 6.1 `credentials encrypt` - Encrypt credentials file

**Synopsis**:
```bash
vya-backupdb credentials encrypt [OPTIONS]
```

**Options**:
```bash
--input PATH           Path to plain-text credentials JSON (required)
--output PATH          Path to output encrypted file [default: .secrets/credentials.json]
--force                Overwrite existing file
```

**Input Format** (plain-text):
```json
{
  "credentials": [
    {
      "id": "prod-mysql-01",
      "username": "backup_user",
      "password": "plain_text_password"
    }
  ]
}
```

**Examples**:
```bash
vya-backupdb credentials encrypt --input plain.json --output .secrets/credentials.json
```

**Output**:
```
[2026-01-09 14:00:00] INFO: Deriving encryption key from hostname: wfdb02
[2026-01-09 14:00:01] INFO: Encrypting 2 credentials...
[2026-01-09 14:00:02] SUCCESS: Credentials encrypted and saved
[2026-01-09 14:00:02] INFO: Output: .secrets/credentials.json (permissions: 0600)
[2026-01-09 14:00:02] WARNING: Delete plain-text file: plain.json
```

---

## 7. Status Commands

### 7.1 `status` - Show system status

**Synopsis**:
```bash
vya-backupdb status [OPTIONS]
```

**Options**:
```bash
--last-backup          Show last backup status
--summary              Show summary only
```

**Examples**:
```bash
vya-backupdb status
vya-backupdb status --last-backup
vya-backupdb status --summary
```

**Output**:
```
VYA BackupDB Status:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
System:
  Version: 2.0.0
  Hostname: wfdb02
  Config: /etc/vya_backupdb/config.yaml
  
Last Backup:
  Instance: prod-mysql-01
  Database: mydb
  Date: 2026-01-09 02:00:00
  Status: ✅ Success
  Size: 1.5 MB
  Duration: 42.3s
  
Storage:
  Base Path: /var/backups/vya_backupdb
  Used Space: 15.3 GB / 100 GB (15.3%)
  Total Backups: 127
  
Retention:
  Strategy: GFS
  Daily: 7 days
  Weekly: 4 weeks
  Monthly: 12 months
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 8. Health Commands

### 8.1 `health` - Health check

**Synopsis**:
```bash
vya-backupdb health
```

**Output (Healthy)**:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-09T14:00:00Z",
  "checks": {
    "config": "ok",
    "credentials": "ok",
    "storage": "ok",
    "databases": "ok"
  }
}
```

**Exit Codes**:
- `0`: Healthy
- `1`: Unhealthy

---

## 9. Exit Codes Summary

| Code | Meaning | Description |
|------|---------|-------------|
| 0 | Success | Operation completed successfully |
| 1 | Partial Failure | Some operations failed |
| 2 | Complete Failure | All operations failed |
| 3 | Configuration Error | Invalid configuration |
| 4 | Credentials Error | Missing or invalid credentials |
| 5 | Storage Error | Storage not accessible |
| 6 | Connection Error | Cannot connect to database |
| 7 | File Not Found | Backup file not found |
| 8 | Validation Error | Backup validation failed |
| 9 | Permission Error | Insufficient permissions |
| 10 | Unknown Error | Unexpected error |

---

## 10. Environment Variables

```bash
VYA_CONFIG_PATH        Override default config path
VYA_SECRETS_PATH       Override default secrets path
VYA_LOG_LEVEL          Override log level (DEBUG, INFO, WARNING, ERROR)
VYA_DRY_RUN            Enable dry-run mode globally (true/false)
```

---

## 11. Output Formats

### JSON Output (--format json)

All commands support `--format json` for machine-readable output:

```bash
vya-backupdb backup --instance prod-mysql-01 --format json
```

Output:
```json
{
  "status": "success",
  "timestamp": "2026-01-09T02:00:00Z",
  "results": [
    {
      "database": "mydb",
      "status": "success",
      "file": "/var/backups/.../mydb_20260109_020000_full.sql.gz",
      "size_bytes": 1572864,
      "duration_seconds": 42.3,
      "checksum": "e3b0c44..."
    }
  ],
  "summary": {
    "total": 1,
    "successful": 1,
    "failed": 0
  }
}
```

---

## Contract Compliance

Este contrato CLI segue:
- ✅ POSIX-compliant options
- ✅ GNU long options (`--option`)
- ✅ Rich terminal output com cores
- ✅ Progress indicators para operações longas
- ✅ JSON output para integração
- ✅ Consistent exit codes
- ✅ Help messages auto-generated (Typer)
