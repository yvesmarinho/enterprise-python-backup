# .secrets/ Directory

## Purpose
This directory stores **encrypted and sensitive files** that should **NEVER** be committed to version control.

## Contents
- `credentials.json.enc` - Encrypted database credentials (Fernet encryption)
- `vault.json.enc` - Encrypted vault (future: T-SECURITY-001)
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
```

### 🔐 Encryption
- All credentials use Fernet encryption (AES-256-CBC)
- Keys derived from hostname (non-portable by design)
- See `CredentialsManager` class for implementation

## Usage

### Encrypt credentials
```bash
python -m python_backup.cli credentials add \
  --id-dbms 1 \
  --username postgres \
  --password <secure-password>
```

### View credentials (requires proper permissions)
```bash
python -m python_backup.cli credentials list
```

## Backup Strategy

### Production Servers
1. Backup `.secrets/` directory separately
2. Store encrypted backup in secure location
3. Never backup to public cloud without additional encryption

### Development
1. Use example files (`credentials.example.json`)
2. Copy and modify for local dev
3. Never commit real credentials

## Recovery

If credentials are lost:
1. Regenerate on original machine (keys are hostname-based)
2. Or restore from secure backup
3. Update `vya_backupbd.json` temporarily with plain text
4. Run migration to re-encrypt: `python -m python_backup.cli credentials migrate`

## Audit Trail

See `docs/SECURITY_AUDIT_2026-01-15.md` for full security audit and remediation.

---

**Created**: 2026-01-15  
**Last Updated**: 2026-01-15  
**Security Level**: 🔴 CRITICAL
