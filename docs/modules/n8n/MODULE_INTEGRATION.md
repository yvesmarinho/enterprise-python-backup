# Module Integration Guide - N8N Backup Module

**Last Updated**: 2026-01-20T12:00:00-03:00  
**Parent Project**: enterprise-python-backup  
**Module Name**: enterprise_backup.n8n  
**Integration Type**: Pluggable specialized module

---

## Integration Architecture

### Project Structure

```
/home/yves_marinho/VyaJobs/enterprise-python-backup/
├── enterprise_backup/
│   ├── __init__.py              # Package initialization
│   ├── core/                     # Shared utilities
│   │   ├── __init__.py
│   │   ├── config.py            # Configuration management
│   │   ├── logging.py           # Centralized logging
│   │   ├── storage.py           # Storage backends (S3, Azure, local)
│   │   └── docker_utils.py      # Common Docker operations
│   │
│   ├── n8n/                      # THIS MODULE
│   │   ├── __init__.py
│   │   ├── backup.py            # N8N backup implementation
│   │   ├── restore.py           # N8N restore implementation
│   │   ├── validators.py        # N8N-specific data validation
│   │   ├── models.py            # Pydantic models for N8N data
│   │   └── cli.py               # N8N-specific CLI commands
│   │
│   ├── postgres/                 # Other modules (future)
│   └── mongodb/
│
├── tests/
│   ├── unit/
│   │   └── n8n/                 # N8N module tests
│   └── integration/
│       └── n8n/
│
├── docs/
│   ├── modules/
│   │   └── n8n/                 # This module's documentation
│   │       ├── constitution.md
│   │       ├── constitution-explicacao.md
│   │       └── recursos-python-docker.md
│   └── api/
│
├── pyproject.toml               # uv project configuration
├── requirements.txt             # Locked dependencies
└── README.md                    # Main project documentation
```

---

## Module Interface

### Required API Compliance

All backup modules must implement the following interface:

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any

class BackupModule(ABC):
    """Base class for all backup modules"""
    
    @abstractmethod
    def backup(
        self,
        output_path: Path,
        container_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute backup operation
        
        Returns:
            Dict with backup metadata (path, size, checksum, etc.)
        """
        pass
    
    @abstractmethod
    def restore(
        self,
        backup_path: Path,
        container_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Execute restore operation
        
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def validate(self, backup_path: Path) -> bool:
        """
        Validate backup integrity
        
        Returns:
            True if backup is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def list_backups(self, backup_root: Path) -> list[Dict[str, Any]]:
        """
        List available backups
        
        Returns:
            List of backup metadata dicts
        """
        pass
```

### N8N Module Implementation

```python
# enterprise_backup/n8n/__init__.py
from .backup import N8NBackup
from .restore import N8NRestore
from .models import N8NCredential, N8NWorkflow

__all__ = ['N8NBackup', 'N8NRestore', 'N8NCredential', 'N8NWorkflow']
__version__ = '1.1.0'
```

```python
# enterprise_backup/n8n/backup.py
from pathlib import Path
from typing import Optional, Dict, Any
from enterprise_backup.core.base import BackupModule
from enterprise_backup.core.logging import get_logger

logger = get_logger(__name__)

class N8NBackup(BackupModule):
    """N8N-specific backup implementation"""
    
    def __init__(self, encryption_key: str):
        self.encryption_key = encryption_key
        logger.info("N8NBackup module initialized")
    
    def backup(
        self,
        output_path: Path,
        container_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Backup N8N credentials and workflows
        
        Follows Constitution v1.1.0 principles:
        - Preserves IDs with --backup flag
        - Validates encryption key
        - Creates timestamped directories
        """
        logger.info(f"Starting N8N backup for container: {container_name}")
        # Implementation follows constitution guidelines...
        pass
```

---

## Shared Dependencies

### Core Utilities Available

The N8N module can leverage shared utilities from `enterprise_backup.core`:

#### **Configuration Management**
```python
from enterprise_backup.core.config import Config

config = Config.from_env()
encryption_key = config.get('N8N_ENCRYPTION_KEY')
backup_path = config.get('BACKUP_BASE_PATH', default='/tmp/bkpfile')
```

#### **Centralized Logging**
```python
from enterprise_backup.core.logging import get_logger

logger = get_logger(__name__)  # Auto-configured with parent settings
logger.info("N8N backup started")
```

#### **Docker Utilities**
```python
from enterprise_backup.core.docker_utils import (
    get_container,
    stop_container_gracefully,
    start_container,
    wait_for_healthy
)

container = get_container('n8n-container')
stop_container_gracefully(container, timeout=30)
```

#### **Storage Backends**
```python
from enterprise_backup.core.storage import S3Storage, AzureStorage

storage = S3Storage(bucket='empresa-backups')
storage.upload(local_path, remote_key='n8n/backup-20260120.tar.gz')
```

---

## Integration Points

### CLI Integration

The parent project provides a unified CLI with subcommands:

```bash
# Parent CLI
enterprise-backup --help

# N8N module commands (registered automatically)
enterprise-backup n8n backup --container n8n-container
enterprise-backup n8n restore --backup-id 20260120-140000
enterprise-backup n8n list-backups
enterprise-backup n8n validate --backup-path /tmp/backup.tar.gz
```

### Module Registration

```python
# enterprise_backup/__init__.py (parent)
from enterprise_backup.n8n import N8NBackup, N8NRestore

REGISTERED_MODULES = {
    'n8n': {
        'backup': N8NBackup,
        'restore': N8NRestore,
        'description': 'N8N workflow automation platform',
        'constitution_version': '1.1.0'
    },
    'postgres': {...},
    'mongodb': {...}
}
```

### Configuration Inheritance

```yaml
# config.yaml (parent project)
backup:
  base_path: /tmp/bkpfile
  retention_days: 7
  
storage:
  backend: s3
  s3:
    bucket: empresa-backups
    region: us-east-1
  
modules:
  n8n:
    encryption_key: ${N8N_ENCRYPTION_KEY}  # From environment
    container_name: n8n-container
    docker_image: n8nio/n8n:latest
    healthcheck_url: http://localhost:5678/healthz
    
  postgres:
    # Other module configs...
```

---

## Development Workflow

### Local Development

1. **Clone this repository** (development workspace):
   ```bash
   cd /home/yves_marinho/Documentos/DevOps/Vya-Jobs/enterprise-python-n8n-backup
   ```

2. **Develop N8N module** with full documentation and tests here

3. **When ready**, copy module to parent project:
   ```bash
   # Sync module code
   rsync -av --delete \
     src/enterprise_backup/n8n/ \
     /home/yves_marinho/VyaJobs/enterprise-python-backup/enterprise_backup/n8n/
   
   # Sync documentation
   rsync -av --delete \
     docs/ \
     /home/yves_marinho/VyaJobs/enterprise-python-backup/docs/modules/n8n/
   
   # Sync tests
   rsync -av --delete \
     tests/ \
     /home/yves_marinho/VyaJobs/enterprise-python-backup/tests/unit/n8n/
   ```

4. **Test in parent context**:
   ```bash
   cd /home/yves_marinho/VyaJobs/enterprise-python-backup
   pytest tests/unit/n8n/
   enterprise-backup n8n backup --help
   ```

### Continuous Integration

Module updates should trigger CI in parent project:

```yaml
# .github/workflows/test-n8n-module.yml (in parent project)
name: Test N8N Module
on:
  push:
    paths:
      - 'enterprise_backup/n8n/**'
      - 'tests/unit/n8n/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: uv pip sync requirements.txt
      - name: Test N8N module
        run: pytest tests/unit/n8n/ -v
```

---

## Dependencies Management

### Module-Specific Dependencies

N8N module has specific dependencies documented in `recursos-python-docker.md`:

```toml
# pyproject.toml (parent project)
[project]
name = "enterprise-backup"
version = "1.0.0"
dependencies = [
    "docker>=7.0.0",
    "requests>=2.31.0",
    "pydantic>=2.5.0",
    "python-dotenv>=1.0.0",
    "click>=8.1.0",
]

[project.optional-dependencies]
n8n = [
    "tenacity>=8.2.0",    # Retry logic for N8N healthchecks
    # Other N8N-specific dependencies
]

postgres = [
    "psycopg2-binary>=2.9.0",
]

all = [
    "enterprise-backup[n8n,postgres,mongodb]"
]
```

### Installation

```bash
# Install only N8N module
uv pip install enterprise-backup[n8n]

# Install all modules
uv pip install enterprise-backup[all]
```

---

## Testing Strategy

### Module-Specific Tests

```python
# tests/unit/n8n/test_backup.py
import pytest
from enterprise_backup.n8n import N8NBackup

def test_backup_preserves_ids():
    """Verify --backup flag preserves credential IDs"""
    backup = N8NBackup(encryption_key='test-key')
    # Test implementation...
    
def test_backup_validates_encryption_key():
    """Verify encryption key is validated"""
    with pytest.raises(ValueError):
        N8NBackup(encryption_key='')
```

### Integration Tests

```python
# tests/integration/n8n/test_backup_restore.py
import pytest
from enterprise_backup.n8n import N8NBackup, N8NRestore
from enterprise_backup.core.docker_utils import get_container

@pytest.mark.integration
def test_full_backup_restore_cycle(docker_client):
    """Test complete backup and restore cycle"""
    # Requires Docker daemon and N8N container running
    pass
```

---

## Documentation Synchronization

### Documentation Structure

```
docs/modules/n8n/
├── constitution.md                  # Governance (from this repo)
├── constitution-explicacao.md       # Detailed explanation
├── recursos-python-docker.md        # Technical resources
├── api/
│   ├── backup.md                    # API documentation
│   ├── restore.md
│   └── models.md
└── examples/
    ├── basic-backup.md
    ├── aws-s3-integration.md
    └── advanced-scenarios.md
```

### Auto-Generated API Docs

Use `pdoc` or `sphinx` to generate API documentation:

```bash
# In parent project
pdoc enterprise_backup.n8n --output-dir docs/api/n8n/
```

---

## Version Compatibility

### Module Versioning

- **Module Version**: Follows constitution version (currently 1.1.0)
- **Parent Project Version**: Independent versioning
- **Compatibility Matrix**:

| Parent Version | N8N Module Version | Python Version | Status |
|----------------|-------------------|----------------|--------|
| 1.0.x          | 1.1.0             | 3.11+          | ✅ Active |
| 2.0.x          | 2.0.0             | 3.12+          | 🔄 Planned |

### Compatibility Checks

```python
# enterprise_backup/n8n/__init__.py
from importlib.metadata import version, PackageNotFoundError

MIN_PARENT_VERSION = '1.0.0'

try:
    parent_version = version('enterprise-backup')
    if parent_version < MIN_PARENT_VERSION:
        raise RuntimeError(
            f"N8N module requires enterprise-backup>={MIN_PARENT_VERSION}, "
            f"found {parent_version}"
        )
except PackageNotFoundError:
    raise RuntimeError("N8N module must be installed within enterprise-backup")
```

---

## Migration Path

### Phase 1: Development (Current)
- Develop N8N module in standalone repository
- Full documentation and constitution in place
- Comprehensive testing

### Phase 2: Integration
1. Create module structure in parent project
2. Copy code, tests, and documentation
3. Update imports and dependencies
4. Test in parent context

### Phase 3: Deployment
1. Package with parent project
2. Deploy to production environment
3. Monitor module performance
4. Iterate based on feedback

### Phase 4: Maintenance
1. Develop new features in standalone repo
2. Sync to parent project when stable
3. Maintain documentation synchronization
4. Track module-specific issues

---

## Communication Channels

### Module-Specific Issues
- **Repository**: This standalone repo (development)
- **Issues**: Track N8N-specific bugs and features here
- **Documentation**: Maintain constitution and guides here

### Parent Project Integration
- **Repository**: enterprise-python-backup (production)
- **Issues**: Integration and cross-module concerns
- **CI/CD**: Parent project's GitHub Actions

---

## Best Practices

### 1. **Maintain Module Independence**
   - N8N module should not import from other modules (postgres, mongodb)
   - Only import from `enterprise_backup.core.*`

### 2. **Follow Constitution**
   - All N8N-specific logic must comply with constitution v1.1.0
   - Security, identity preservation, and integrity principles are NON-NEGOTIABLE

### 3. **Logging Standards**
   - Use centralized logger from `enterprise_backup.core.logging`
   - Include module name in log messages: `logger = get_logger(__name__)`

### 4. **Configuration Management**
   - Module configuration via parent's `config.yaml`
   - Environment variables prefixed: `N8N_*`
   - No hardcoded paths or credentials

### 5. **Error Handling**
   - Raise module-specific exceptions (inherit from `enterprise_backup.core.exceptions`)
   - Provide clear error messages with recovery suggestions
   - Log all errors with context

---

## References

### Internal Documentation
- [Constitution](constitution.md) - Governance and principles
- [Constitution Explanation](../../../docs/constitution-explicacao.md) - Detailed guide
- [Python Resources](../../../docs/recursos-python-docker.md) - Technical analysis

### Parent Project
- Location: `/home/yves_marinho/VyaJobs/enterprise-python-backup`
- Documentation: `docs/modules/n8n/`
- Tests: `tests/unit/n8n/`

### External References
- [N8N Documentation](https://docs.n8n.io)
- [Docker SDK for Python](https://docker-py.readthedocs.io)
- [uv Package Manager](https://github.com/astral-sh/uv)

---

**Last Updated**: 2026-01-20T12:00:00-03:00  
**Constitution Version**: 1.1.0  
**Module Status**: Ready for integration  
**Next Steps**: Implement module structure in parent project
