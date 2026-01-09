# VYA BackupDB - Quick Start Guide

**Version**: 2.0.0  
**Target**: Phase 2 Core Development  
**Audience**: Developers and System Administrators

---

## Prerequisites

- **Python**: 3.11 or higher
- **OS**: Linux (tested on RHEL, CentOS, Ubuntu)
- **Databases**: MySQL 8.0+ or PostgreSQL 13+
- **Git**: For version control

---

## Installation

### 1. Clone Repository

```bash
cd /opt
git clone https://github.com/your-org/vya-backupdb.git
cd vya-backupdb
git checkout 001-phase2-core-development
```

### 2. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -e ".[dev]"
```

This installs:
- **Core**: sqlalchemy, pydantic, typer, rich, cryptography
- **Drivers**: pymysql, psycopg[binary]
- **Dev**: pytest, pytest-cov, pytest-asyncio, testcontainers, black, ruff

---

## Configuration

### 1. Copy Configuration Template

```bash
mkdir -p config
cp config/config.example.yaml config/config.yaml
```

### 2. Edit Configuration

Edit [config/config.yaml](config/config.yaml):

```yaml
databases:
  - id: prod-mysql-01
    type: mysql
    host: localhost
    port: 3306
    exclude_databases:
      - information_schema
      - performance_schema
      - mysql
      - sys

storage:
  base_path: /var/backups/vya_backupdb
  compression_level: 6

retention:
  strategy: gfs
  daily_keep: 7
  weekly_keep: 4
  monthly_keep: 12

logging:
  level: INFO
  format: detailed
  file: /var/log/vya_backupdb/backup.log
```

### 3. Create Storage Directory

```bash
sudo mkdir -p /var/backups/vya_backupdb
sudo chown $(whoami):$(whoami) /var/backups/vya_backupdb
sudo chmod 750 /var/backups/vya_backupdb
```

---

## Credentials Setup

### 1. Create Credentials File

Create `.secrets/credentials.json` (plain-text template):

```json
{
  "credentials": [
    {
      "id": "prod-mysql-01",
      "username": "backup_user",
      "password": "your_secure_password"
    }
  ]
}
```

### 2. Encrypt Credentials

```bash
mkdir -p .secrets
chmod 700 .secrets

vya-backupdb credentials encrypt \
  --input .secrets/credentials.json \
  --output .secrets/credentials.encrypted.json
  
# Delete plain-text file
rm .secrets/credentials.json
```

Credentials are encrypted with Fernet using hostname-based key derivation.

---

## Database User Setup

> ℹ️ **User Backup Feature**: 
> 
> Phase 2 includes separate user backup/restore commands!
> 
> **Database backup**: ✅ Schema + Data  
> **User backup**: ✅ Users + Roles + GRANTs (separate command)
> 
> **For restore to different server**:
> 1. Backup users: `vya-backupdb users backup --instance prod-mysql-01`
> 2. Backup databases: `vya-backupdb backup --instance prod-mysql-01`
> 3. On target: Restore users first, then databases
> 
> See [User Backup & Restore](#user-backup--restore) section below.

### MySQL/MariaDB

**Backup User** (source server):
```sql
CREATE USER 'backup_user'@'localhost' IDENTIFIED BY 'your_secure_password';

-- Grant read permissions
GRANT SELECT, LOCK TABLES, SHOW VIEW, EVENT, TRIGGER 
ON *.* TO 'backup_user'@'localhost';

-- Grant restore permissions (optional)
GRANT CREATE, DROP, ALTER, INSERT, UPDATE, DELETE, INDEX, CREATE VIEW 
ON *.* TO 'backup_user'@'localhost';

FLUSH PRIVILEGES;
```

### PostgreSQL

```sql
CREATE ROLE backup_user WITH LOGIN PASSWORD 'your_secure_password';

-- Grant read permissions
GRANT CONNECT ON DATABASE your_database TO backup_user;
GRANT USAGE ON SCHEMA public TO backup_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO backup_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
  GRANT SELECT ON TABLES TO backup_user;

-- Grant restore permissions (optional)
GRANT CREATE ON DATABASE your_database TO backup_user;
```

---

## Usage Examples

### Test Configuration

```bash
# Validate config file
vya-backupdb config validate

# Test database connections
vya-backupdb config test-connections

# Show configuration
vya-backupdb config show --no-secrets
```

### Create Backup

```bash
# Backup all databases from instance
vya-backupdb backup --instance prod-mysql-01

# Backup specific database
vya-backupdb backup --instance prod-mysql-01 --database mydb

# Backup all configured instances
vya-backupdb backup --all

# Dry-run (test only)
vya-backupdb backup --instance prod-mysql-01 --dry-run
```

### List Backups

```bash
# List all backups
vya-backupdb restore list

# List backups for specific database
vya-backupdb restore list --instance prod-mysql-01 --database mydb

# List recent backups (last 10)
vya-backupdb restore list --limit 10
```

### User Backup & Restore

```bash
# Backup all users from instance
vya-backupdb users backup --instance prod-mysql-01

# List backed-up users
vya-backupdb users list --instance prod-mysql-01

# Restore all users to target server
vya-backupdb users restore \
  --file /var/backups/.../users_20260109_020000.sql.gz \
  --target-instance staging-mysql-01 \
  --all

# Restore single user
vya-backupdb users restore \
  --file /var/backups/.../users_20260109_020000.sql.gz \
  --target-instance staging-mysql-01 \
  --user myapp_user

# Dry-run (validate without restoring)
vya-backupdb users restore --file backup.sql.gz --dry-run --all
```

### Restore Backup

> ℹ️ **Recommended Order for Empty Server**:
> 
> ```bash
> # 1. Restore users first
> vya-backupdb users restore --file users_backup.sql.gz --target-instance new-server --all
> 
> # 2. Then restore databases
> vya-backupdb restore --instance prod-mysql-01 --database mydb --latest
> ```

```bash
# Restore latest backup
vya-backupdb restore --instance prod-mysql-01 --database mydb --latest

# Restore from specific file
vya-backupdb restore --file /var/backups/.../mydb_20260109_020000_full.sql.gz

# Restore to different database
vya-backupdb restore \
  --instance prod-mysql-01 \
  --database mydb \
  --target-database mydb_restore \
  --latest

# Dry-run (validate without restoring)
vya-backupdb restore --file backup.sql.gz --dry-run
```

### System Status

```bash
# Check overall status
vya-backupdb status

# Check last backup
vya-backupdb status --last-backup

# Health check (for monitoring)
vya-backupdb health
```

---

## Automation with Cron

### Daily Backups

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /opt/vya-backupdb/venv/bin/vya-backupdb backup --all >> /var/log/vya_backupdb/cron.log 2>&1
```

### Retention Cleanup

Retention cleanup runs automatically after each backup (GFS strategy).

Manual cleanup (if needed):

```bash
vya-backupdb retention apply --dry-run
vya-backupdb retention apply --force
```

---

## Project Structure

```
vya-backupdb/
├── pyproject.toml              # Project configuration
├── README.md                   # Main documentation
├── config/
│   ├── config.yaml             # Main configuration
│   └── config.example.yaml     # Template
├── .secrets/
│   └── credentials.encrypted.json  # Encrypted credentials
├── src/vya_backupbd/
│   ├── __init__.py
│   ├── __main__.py             # Entry point
│   ├── cli.py                  # CLI commands (Typer)
│   ├── config.py               # Config loader (Pydantic)
│   ├── core/
│   │   ├── backup.py           # Backup orchestrator
│   │   └── restore.py          # Restore orchestrator
│   ├── db/
│   │   ├── base.py             # Base DB adapter
│   │   ├── engine.py           # SQLAlchemy engine manager
│   │   ├── mysql.py            # MySQL adapter
│   │   └── postgresql.py       # PostgreSQL adapter
│   ├── security/
│   │   ├── credentials.py      # Credentials manager
│   │   └── encryption.py       # Fernet encryption
│   └── utils/
│       ├── filesystem.py       # File operations
│       ├── compression.py      # Gzip compression
│       └── metadata.py         # Metadata JSON handler
├── tests/
│   ├── unit/                   # Unit tests (pytest)
│   └── integration/            # Integration tests (testcontainers)
├── specs/
│   └── 001-phase2-core-development/
│       ├── spec.md             # Feature specification
│       ├── plan.md             # Implementation plan
│       ├── research.md         # Technical research
│       ├── data-model.md       # Data models
│       ├── contracts/          # API contracts
│       └── quickstart.md       # This file
└── logs/
    └── backup.log              # Application logs
```

---

## Development Workflow

### 1. Run Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# Coverage report
pytest --cov=src/vya_backupbd --cov-report=html
```

### 2. Code Quality

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking (optional)
mypy src/
```

### 3. Run Development Version

```bash
# Install in editable mode
pip install -e .

# Run CLI
vya-backupdb --help
```

---

## Troubleshooting

### Issue: "Config file not found"

**Solution**: Ensure [config/config.yaml](config/config.yaml) exists. Copy from template:

```bash
cp config/config.example.yaml config/config.yaml
```

### Issue: "Cannot decrypt credentials"

**Cause**: Credentials encrypted on different hostname.

**Solution**: Re-encrypt credentials on current host:

```bash
vya-backupdb credentials encrypt \
  --input plain.json \
  --output .secrets/credentials.encrypted.json
```

### Issue: "Permission denied" on storage directory

**Solution**: Fix permissions:

```bash
sudo chown $(whoami):$(whoami) /var/backups/vya_backupdb
sudo chmod 750 /var/backups/vya_backupdb
```

### Issue: Database connection fails

**Check**:
1. Database is running: `systemctl status mysql`
2. Credentials are correct
3. User has required permissions (see [Database User Setup](#database-user-setup))
4. Firewall allows connection: `telnet localhost 3306`

```bash
# Test connection
vya-backupdb config test-connections --instance prod-mysql-01
```

### Issue: Import errors

**Solution**: Reinstall dependencies:

```bash
pip install --upgrade pip
pip install -e ".[dev]"
```

---

## Performance Tips

1. **Compression Level**: Default is 6 (balanced). Use 1 for speed, 9 for size.
2. **Parallel Backups**: Phase 6 feature (not yet available).
3. **Storage**: Use local SSD for better I/O performance.
4. **Retention**: Adjust GFS policy to balance storage vs history.

---

## Security Best Practices

1. **Never commit credentials**: Add `.secrets/` to `.gitignore`
2. **Restrict permissions**: `chmod 600 .secrets/credentials.encrypted.json`
3. **Use strong passwords**: Minimum 16 characters, mixed case, symbols
4. **Rotate credentials**: Change database passwords quarterly
5. **Audit logs**: Monitor [/var/log/vya_backupdb/backup.log](/var/log/vya_backupdb/backup.log)
6. **Network security**: Use SSL/TLS for remote database connections

---

## Monitoring

### Cron Email Alerts

Cron sends email on failure. Test:

```bash
# Set MAILTO in crontab
crontab -e

MAILTO=admin@example.com
0 2 * * * /path/to/vya-backupdb backup --all
```

### Health Check (for Monitoring Tools)

```bash
# Returns exit code 0 if healthy
vya-backupdb health

# JSON output for monitoring
vya-backupdb health --format json
```

### Integration with Nagios/Prometheus (Phase 5+)

Phase 5 will add metrics export and alerting integration.

---

## Next Steps

1. **Review Spec**: Read [spec.md](spec.md) for feature requirements
2. **Review Plan**: Read [plan.md](plan.md) for implementation details
3. **Review Research**: Read [research.md](research.md) for technical decisions
4. **Review Data Model**: Read [data-model.md](data-model.md) for Pydantic models
5. **Review Contracts**: Read [contracts/cli-contract.md](contracts/cli-contract.md) for CLI specification
6. **Start Development**: Follow tasks in `tasks.md` (generated by `/speckit.tasks`)

---

## Support

- **Documentation**: [README.md](../../README.md)
- **Issues**: GitHub Issues (TBD)
- **Email**: devops@vya-jobs.com

---

## License

Proprietary - VYA Jobs © 2026
