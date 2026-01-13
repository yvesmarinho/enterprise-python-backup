"""
Backup file finder and lister utilities.

Provides functions to discover and list available backup files.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)


def list_backups(
    backup_dir: str,
    database: str = None,
    dbms_type: str = None,
    limit: int = 10
) -> list[dict]:
    """
    List available backup files.
    
    Args:
        backup_dir: Directory containing backups
        database: Filter by database name (optional)
        dbms_type: Filter by database type ('mysql' or 'postgresql')
        limit: Maximum number of backups to return
        
    Returns:
        List of backup file dictionaries with metadata
    """
    logger.debug(f"=== Função: list_backups ===")
    logger.debug(f"==> PARAM: backup_dir TYPE: {type(backup_dir)}, CONTENT: {backup_dir}")
    logger.debug(f"==> PARAM: database TYPE: {type(database)}, CONTENT: {database}")
    
    import os
    import glob
    from pathlib import Path
    from datetime import datetime
    
    backups = []
    
    # Search patterns
    patterns = [
        f"{backup_dir}/**/*{database}*.sql",
        f"{backup_dir}/**/*{database}*.sql.gz",
        f"{backup_dir}/**/*{database}*.zip"
    ]
    
    for pattern in patterns:
        for file in Path(backup_dir).rglob(pattern):
            if file.is_file():
                stat = file.stat()
                backups.append({
                    'file': str(file),
                    'database': database,
                    'size': stat.st_size,
                    'date': datetime.fromtimestamp(stat.st_mtime)
                })
    
    return sorted(backups, key=lambda x: x['date'], reverse=True)
"""

Agora vou adicionar o comando restore no CLI. Vou criar as funções necessárias.

<function_calls>
<invoke name="grep_search">
<parameter name="includePattern">cli.py