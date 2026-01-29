# Credentials Import Template

This file provides templates for importing credentials into the vault system using `vya-backupdb vault-add --from-file`.

## Usage

1. Copy this file or create your own JSON file
2. Fill in the credentials
3. Import: `vya-backupdb vault-add --from-file your-credentials.json`
4. Securely delete: `shred -vfz -n 10 your-credentials.json`

## Template: Database Credentials

```json
[
  {
    "id": "mysql-prod",
    "username": "root",
    "password": "YOUR_SECURE_PASSWORD_HERE",
    "description": "Production MySQL Server"
  },
  {
    "id": "mysql-staging",
    "username": "staging_user",
    "password": "YOUR_SECURE_PASSWORD_HERE",
    "description": "Staging MySQL Server"
  },
  {
    "id": "mysql-dev",
    "username": "dev_user",
    "password": "YOUR_SECURE_PASSWORD_HERE",
    "description": "Development MySQL Server"
  },
  {
    "id": "postgresql-prod",
    "username": "postgres",
    "password": "YOUR_SECURE_PASSWORD_HERE",
    "description": "Production PostgreSQL Server"
  },
  {
    "id": "postgresql-staging",
    "username": "postgres",
    "password": "YOUR_SECURE_PASSWORD_HERE",
    "description": "Staging PostgreSQL Server"
  }
]
```

## Template: Multi-Service Credentials

```json
[
  {
    "id": "mysql-app-db",
    "username": "app_user",
    "password": "YOUR_SECURE_PASSWORD_HERE",
    "description": "Application Database"
  },
  {
    "id": "postgresql-analytics",
    "username": "analytics",
    "password": "YOUR_SECURE_PASSWORD_HERE",
    "description": "Analytics Database"
  },
  {
    "id": "smtp-notifications",
    "username": "notifications@company.com",
    "password": "YOUR_SECURE_PASSWORD_HERE",
    "description": "SMTP Server for Email Notifications"
  },
  {
    "id": "s3-backups",
    "username": "AWS_ACCESS_KEY_ID",
    "password": "AWS_SECRET_ACCESS_KEY",
    "description": "S3 Bucket for Backups"
  }
]
```

## Template: Multi-Region Setup

```json
[
  {
    "id": "mysql-us-east",
    "username": "root",
    "password": "YOUR_SECURE_PASSWORD_HERE",
    "description": "MySQL US East Region"
  },
  {
    "id": "mysql-eu-west",
    "username": "root",
    "password": "YOUR_SECURE_PASSWORD_HERE",
    "description": "MySQL EU West Region"
  },
  {
    "id": "mysql-ap-south",
    "username": "root",
    "password": "YOUR_SECURE_PASSWORD_HERE",
    "description": "MySQL Asia Pacific South Region"
  }
]
```

## Template: Team Environment

```json
[
  {
    "id": "team-mysql-shared",
    "username": "team_user",
    "password": "YOUR_SECURE_PASSWORD_HERE",
    "description": "Shared Team MySQL Database"
  },
  {
    "id": "ci-cd-database",
    "username": "cicd",
    "password": "YOUR_SECURE_PASSWORD_HERE",
    "description": "CI/CD Pipeline Database"
  },
  {
    "id": "monitoring-db",
    "username": "monitoring",
    "password": "YOUR_SECURE_PASSWORD_HERE",
    "description": "Monitoring System Database"
  }
]
```

## Field Reference

### Required Fields

- **id**: Unique identifier (lowercase, hyphens, no spaces)
  - Good: `mysql-prod`, `db-app-1`, `postgres-analytics`
  - Bad: `MySQL Prod`, `db app 1`, `POSTGRES_ANALYTICS`

- **username**: Authentication username
  - Database user, email address, or access key

- **password**: Authentication password
  - Database password, API key, or secret

### Optional Fields

- **description**: Human-readable description
  - Helps identify purpose and context
  - Recommended for all credentials

## Best Practices

### 1. Naming Convention

Use consistent ID naming:
- Format: `{service}-{environment}` or `{service}-{purpose}`
- Examples:
  - `mysql-prod`, `mysql-staging`, `mysql-dev`
  - `postgres-analytics`, `postgres-app`, `postgres-logs`
  - `smtp-notifications`, `smtp-marketing`

### 2. Password Security

- Use strong, unique passwords
- Minimum 12 characters
- Mix of uppercase, lowercase, numbers, symbols
- Never reuse passwords across services

### 3. Description Guidelines

Good descriptions include:
- Service type (MySQL, PostgreSQL, SMTP)
- Environment (Production, Staging, Development)
- Purpose (Analytics, Application, Backup)
- Location (if multi-region)

Examples:
- "Production MySQL - Application Database"
- "Staging PostgreSQL - Analytics Pipeline"
- "Development MySQL - Local Testing"

### 4. File Security

**Before Import:**
```bash
# Set restrictive permissions
chmod 600 credentials.json

# Verify file
ls -l credentials.json
```

**After Import:**
```bash
# Verify import
vya-backupdb vault-list

# Securely delete source file
shred -vfz -n 10 credentials.json

# Verify deletion
ls -l credentials.json  # Should not exist
```

### 5. Backup Strategy

```bash
# Export current vault for backup
cp .secrets/vault.json.enc .secrets/vault-backup-$(date +%Y%m%d).json.enc

# Store in secure location
mv .secrets/vault-backup-*.json.enc /secure/backup/location/
```

## Migration Examples

### From Legacy vya_backupbd.json

If you have credentials in `vya_backupbd.json`:

1. Extract credentials manually or with script
2. Format as JSON array
3. Import: `vya-backupdb vault-add --from-file legacy-credentials.json`

### From Environment Variables

```bash
# Create JSON from environment variables
cat > env-credentials.json <<EOF
[
  {
    "id": "mysql-prod",
    "username": "$MYSQL_USER",
    "password": "$MYSQL_PASSWORD",
    "description": "Production MySQL from ENV"
  }
]
EOF

# Import
vya-backupdb vault-add --from-file env-credentials.json

# Cleanup
shred -vfz -n 10 env-credentials.json
```

### From Another Vault System

```bash
# Export from old system (example using HashiCorp Vault)
vault kv get -format=json secret/mysql-prod | jq '{id: "mysql-prod", username: .data.username, password: .data.password, description: "Migrated from Vault"}' > temp.json

# Import
vya-backupdb vault-add --from-file temp.json

# Cleanup
shred -vfz -n 10 temp.json
```

## Validation

Before importing, validate your JSON:

```bash
# Check JSON syntax
python3 -m json.tool credentials.json

# Or with jq
jq . credentials.json

# Check required fields
jq '.[] | select(.id == null or .username == null or .password == null)' credentials.json
```

## Related Documentation

- [VAULT_BATCH_IMPORT_GUIDE.md](../docs/guides/VAULT_BATCH_IMPORT_GUIDE.md) - Complete batch import guide
- [VAULT_SYSTEM_GUIDE.md](../docs/guides/VAULT_SYSTEM_GUIDE.md) - Complete vault documentation
- [SECRETS_DIRECTORY_GUIDE.md](../docs/guides/SECRETS_DIRECTORY_GUIDE.md) - Security best practices

---

**Template Version**: 1.0.0  
**Created**: 2026-01-26  
**Compatible With**: vya-backupdb 2.0.0+
