# File Backup Guide

**VYA BackupDB v2.0.0** - Comprehensive Guide for File Backup and Restore

---

## 📖 Table of Contents

1. [Overview](#overview)
2. [Configuration](#configuration)
3. [Glob Patterns](#glob-patterns)
4. [Usage Examples](#usage-examples)
5. [CLI Commands](#cli-commands)
6. [Common Use Cases](#common-use-cases)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

---

## Overview

The File Backup feature allows you to backup and restore files and directories using glob patterns, similar to traditional database backups. Files are compressed into tar.gz archives with full path preservation.

### Key Features

- ✅ **Glob Pattern Support**: Use `*`, `**`, `{}` for flexible file matching
- ✅ **Compression**: Automatic tar.gz compression
- ✅ **Path Preservation**: Maintains original directory structure
- ✅ **Permission Preservation**: Keeps file permissions and timestamps
- ✅ **Selective Backup**: Target specific file types or directories
- ✅ **Restore Flexibility**: Restore to original or custom location
- ✅ **Email Notifications**: Success/failure notifications with logs
- ✅ **Retention Policy**: Automatic cleanup of old backups

---

## Configuration

### Basic Configuration

Add a file backup instance to `python_backup.json`:

```json
{
  "db_config": [
    {
      "id_dbms": 1,
      "dbms": "files",
      "host": "localhost",
      "port": 0,
      "user": "",
      "secret": "",
      "db_ignore": "",
      "db_list": [
        "/docker/volumes/**/*",
        "/opt/app/config/*.json"
      ],
      "enabled": true
    }
  ],
  "bkp_system": {
    "path_sql": "/backup/sql",
    "path_zip": "/backup/compressed",
    "path_files": "/backup/files",
    "retention_files": 7
  }
}
```

### Configuration Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `id_dbms` | integer | Unique instance identifier |
| `dbms` | string | Must be `"files"` |
| `host` | string | Always `"localhost"` |
| `port` | integer | Use `0` for files |
| `db_list` | array | List of glob patterns to backup |
| `enabled` | boolean | Enable/disable this instance |
| `path_files` | string | Destination directory for file backups |

---

## Glob Patterns

### Pattern Syntax

| Pattern | Description | Example |
|---------|-------------|---------|
| `*` | Matches any characters in a single directory level | `/app/*.json` → all JSON files in /app |
| `**` | Matches recursively through directories | `/app/**/*.log` → all .log files under /app |
| `?` | Matches single character | `/app/file?.txt` → file1.txt, file2.txt |
| `{}` | Matches multiple alternatives | `/app/*.{json,yaml}` → .json or .yaml files |
| `[abc]` | Matches any character in brackets | `/app/file[123].txt` |
| `[!abc]` | Matches any character NOT in brackets | `/app/file[!0-9].txt` |

### Pattern Examples

```json
"db_list": [
  // Single directory, all files
  "/opt/app/config/*",
  
  // Recursive, all files
  "/docker/volumes/**/*",
  
  // Specific extensions
  "/var/www/uploads/**/*.{jpg,png,pdf}",
  
  // Multiple patterns
  "/etc/nginx/**/*",
  "/etc/systemd/system/*.service",
  
  // Exclude pattern (use carefully)
  "/app/**/!(*.tmp)"
]
```

---

## Usage Examples

### Example 1: Backup Docker Volumes

```json
{
  "id_dbms": 1,
  "dbms": "files",
  "host": "localhost",
  "port": 0,
  "db_list": [
    "/var/lib/docker/volumes/**/*"
  ],
  "enabled": true
}
```

```bash
# Backup
vya-backupdb backup --instance 1

# Result:
# /backup/files/20260114_120000_files_var_lib_docker_volumes.tar.gz
```

### Example 2: Backup Configuration Files

```json
{
  "id_dbms": 2,
  "dbms": "files",
  "host": "localhost",
  "port": 0,
  "db_list": [
    "/opt/app/config/*.{yaml,yml,json}",
    "/opt/app/.env",
    "/opt/app/secrets/*.key"
  ],
  "enabled": true
}
```

### Example 3: Backup User Uploads

```json
{
  "id_dbms": 3,
  "dbms": "files",
  "host": "localhost",
  "port": 0,
  "db_list": [
    "/var/www/html/uploads/**/*.{jpg,jpeg,png,gif}",
    "/var/www/html/documents/**/*.pdf"
  ],
  "enabled": true
}
```

### Example 4: System Configuration Backup

```json
{
  "id_dbms": 4,
  "dbms": "files",
  "host": "localhost",
  "port": 0,
  "db_list": [
    "/etc/nginx/**/*",
    "/etc/apache2/**/*",
    "/etc/systemd/system/*.service",
    "/etc/cron.d/*",
    "/etc/hosts",
    "/etc/fstab"
  ],
  "enabled": true
}
```

---

## CLI Commands

### Backup Files

```bash
# Backup specific instance
vya-backupdb backup --instance 1

# Backup all file instances
vya-backupdb backup --all

# Dry run (test without backup)
vya-backupdb backup --instance 1 --dry-run

# With compression (already compressed by default)
vya-backupdb backup --instance 1 --compression
```

### List Available Backups

```bash
# List all file backups
vya-backupdb restore-list --instance 1

# Filter by pattern
vya-backupdb restore-list --instance 1 --database "docker"

# Show more results
vya-backupdb restore-list --instance 1 --limit 50
```

### Restore Files

```bash
# Restore to original location
vya-backupdb restore --file /backup/files/20260114_120000_files_docker.tar.gz

# Restore to custom location
vya-backupdb restore \
  --file /backup/files/20260114_120000_files_docker.tar.gz \
  --target /tmp/restored_files

# Dry run restore
vya-backupdb restore \
  --file /backup/files/20260114_120000_files_docker.tar.gz \
  --target /tmp/restored_files \
  --dry-run
```

### Test Connection

```bash
# Verify file patterns are accessible
vya-backupdb test-connection --instance 1
```

---

## Common Use Cases

### Use Case 1: Docker Environment Backup

**Scenario**: Backup all Docker volumes and compose files

```json
{
  "db_list": [
    "/var/lib/docker/volumes/**/*",
    "/opt/docker-compose/**/*.yml",
    "/opt/docker-compose/**/.env"
  ]
}
```

**Schedule**: Daily at 2 AM

```json
{
  "schedule_settings": {
    "enabled": true,
    "days_of_week": [1, 2, 3, 4, 5, 6, 7],
    "time": "02:00"
  }
}
```

### Use Case 2: Web Application Assets

**Scenario**: Backup user-uploaded files and media

```json
{
  "db_list": [
    "/var/www/html/uploads/**/*.{jpg,jpeg,png,gif,pdf}",
    "/var/www/html/media/**/*",
    "/var/www/html/storage/**/*"
  ]
}
```

**Retention**: Keep 14 days

```json
{
  "bkp_system": {
    "retention_files": 14
  }
}
```

### Use Case 3: Configuration Management

**Scenario**: Backup critical system configurations

```json
{
  "db_list": [
    "/etc/nginx/**/*",
    "/etc/systemd/system/**/*.service",
    "/etc/cron.d/*",
    "/etc/ssl/certs/**/*",
    "/root/.ssh/authorized_keys"
  ]
}
```

### Use Case 4: Application Data

**Scenario**: Backup application-specific data directories

```json
{
  "db_list": [
    "/opt/myapp/data/**/*",
    "/opt/myapp/logs/**/*.log",
    "/opt/myapp/cache/**/*"
  ]
}
```

---

## Troubleshooting

### Issue 1: Permission Denied

**Error**: `Permission denied: '/path/to/file'`

**Solution**:
```bash
# Run as root or with sudo
sudo vya-backupdb backup --instance 1

# Or adjust file permissions
sudo chmod +r /path/to/file

# Or run as specific user
sudo -u backupuser vya-backupdb backup --instance 1
```

### Issue 2: Pattern Matches No Files

**Error**: `No files found matching pattern`

**Solution**:
```bash
# Test pattern manually
ls -la /path/to/files/**/*.json

# Verify pattern in config
cat python_backup.json | jq '.db_config[] | select(.id_dbms==1) | .db_list'

# Use absolute paths
"/opt/app/**/*"  # ✅ Good
"./app/**/*"     # ❌ Bad (relative path)
```

### Issue 3: Backup Too Large

**Error**: `No space left on device`

**Solution**:
```bash
# Check available space
df -h /backup/files

# Use more specific patterns
"/app/**/*.{jpg,png}"  # Instead of "/app/**/*"

# Implement retention cleanup
vya-backupdb retention cleanup --instance 1

# Change backup destination
# Edit python_backup.json:
"path_files": "/mnt/external/backup/files"
```

### Issue 4: Slow Backup

**Problem**: Backup takes too long

**Solution**:
```bash
# Exclude unnecessary files
"/app/**/*"                    # All files
"/app/**/!(*.tmp|*.cache)"     # Exclude temp files

# Split into multiple instances
# Instance 1: Critical files
# Instance 2: Less critical files

# Use compression (already enabled by default)
tar.gz format provides good balance
```

### Issue 5: Restore Fails

**Error**: `Failed to extract backup`

**Solution**:
```bash
# Verify backup integrity
tar -tzf /backup/files/backup.tar.gz

# Check target directory permissions
sudo chmod +w /target/directory

# Manually extract for debugging
tar -xzvf /backup/files/backup.tar.gz -C /tmp/test
```

---

## Best Practices

### 1. Pattern Design

✅ **Good Patterns**:
```json
"/opt/app/config/*.{yaml,json}"        // Specific extensions
"/docker/volumes/postgres_data/**/*"   // Named volume
"/var/www/uploads/2026/**/*.pdf"       // Date-based
```

❌ **Avoid**:
```json
"/**/*"                      // Too broad
"/home/**/*"                 // May include huge directories
"*.txt"                      // Relative path
```

### 2. Organization

Organize instances by:
- **Purpose**: config, data, uploads, logs
- **Criticality**: critical, important, optional
- **Change Frequency**: hourly, daily, weekly

Example:
```json
{
  "id_dbms": 1,
  "comment": "CRITICAL - Application config",
  "db_list": ["/opt/app/config/**/*"],
  "enabled": true
}
{
  "id_dbms": 2,
  "comment": "DAILY - User uploads",
  "db_list": ["/var/www/uploads/**/*"],
  "enabled": true
}
```

### 3. Testing

Always test your configuration:

```bash
# Dry run first
vya-backupdb backup --instance 1 --dry-run

# Test restore to temporary location
vya-backupdb restore \
  --file /backup/files/latest.tar.gz \
  --target /tmp/restore_test \
  --dry-run

# Verify backup contents
tar -tzf /backup/files/backup.tar.gz | head -20
```

### 4. Monitoring

Set up monitoring:

```json
{
  "email_settings": {
    "enabled": true,
    "failure_recipients": ["ops@company.com"],
    "test_mode": false
  },
  "prometheus_settings": {
    "enabled": true,
    "job_name": "backup-files"
  }
}
```

### 5. Security

Protect sensitive files:

```bash
# Restrict backup directory permissions
sudo chmod 700 /backup/files

# Encrypt sensitive backups (manual step)
gpg --encrypt /backup/files/sensitive.tar.gz

# Use secure patterns (avoid including secrets in patterns)
"/app/config/database.yml"  # ❌ May contain passwords
"/app/config/*.sample"      # ✅ Safe
```

### 6. Performance

Optimize backup performance:

```json
// Split large backups
{
  "id_dbms": 1,
  "db_list": ["/large_dir/part1/**/*"]
},
{
  "id_dbms": 2,
  "db_list": ["/large_dir/part2/**/*"]
}

// Use specific patterns
"/uploads/**/*.{jpg,png}"  // Instead of "/uploads/**/*"
```

### 7. Retention Strategy

Configure appropriate retention:

```json
{
  "bkp_system": {
    "retention_files": 7  // Keep 7 days
  }
}
```

Typical retention periods:
- **Configuration files**: 30 days
- **User uploads**: 14 days  
- **Logs**: 7 days
- **Temporary data**: 1 day

---

## Advanced Topics

### Combining with Database Backups

```json
{
  "db_config": [
    {
      "id_dbms": 1,
      "dbms": "postgresql",
      "db_list": ["app_db"]
    },
    {
      "id_dbms": 2,
      "dbms": "files",
      "db_list": ["/opt/app/config/**/*"]
    }
  ]
}
```

Backup both with:
```bash
vya-backupdb backup --all
```

### Incremental Backups

Currently not supported. All file backups are full backups.

**Workaround**: Use date-based patterns
```json
{
  "db_list": [
    "/uploads/2026/01/**/*"  // Only current month
  ]
}
```

### Custom Backup Scripts

Integrate with custom scripts:

```bash
#!/bin/bash
# pre-backup.sh

# Stop service
systemctl stop myapp

# Run backup
vya-backupdb backup --instance 1

# Start service
systemctl start myapp
```

---

## Quick Reference

### Pattern Cheat Sheet

```
*           Any files in current directory
**/*        All files recursively
*.txt       All .txt files
**/*.log    All .log files recursively
*.{a,b}     Files ending in .a or .b
[0-9]*      Files starting with digit
```

### Common Commands

```bash
# Backup
vya-backupdb backup --instance 1

# List backups
vya-backupdb restore-list --instance 1

# Restore
vya-backupdb restore --file <path> --target <dir>

# Test
vya-backupdb test-connection --instance 1
```

---

## Support

For issues or questions:
- Check logs: `/var/log/enterprise/vya_backupdb_*.log`
- Email notifications: Configured in `email_settings`
- Documentation: `docs/` directory

---

**Last Updated**: 2026-01-14  
**Version**: 2.0.0
