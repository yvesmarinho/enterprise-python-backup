"""Utility functions for N8N backup and restore operations."""

import hashlib
import json
import platform
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .exceptions import ValidationError


def generate_timestamp() -> str:
    """Generate timestamp in YYYYMMDD-HHMMSS format for backup naming.

    Returns:
        Timestamp string (e.g., '20260120-140530')

    Example:
        >>> timestamp = generate_timestamp()
        >>> assert re.match(r'\d{8}-\d{6}', timestamp)
    """
    return datetime.utcnow().strftime("%Y%m%d-%H%M%S")


def calculate_sha256(file_path: Path) -> str:
    """Calculate SHA256 checksum of a file.

    Args:
        file_path: Path to file to checksum

    Returns:
        Hexadecimal SHA256 checksum string

    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file cannot be read

    Example:
        >>> checksum = calculate_sha256(Path('/tmp/backup.json'))
        >>> assert len(checksum) == 64  # SHA256 is 64 hex characters
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read file in chunks to handle large files efficiently
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()


def format_backup_path(
    base_path: Path,
    timestamp: str,
    hostname: str,
    backup_type: str,
) -> Path:
    """Format backup directory path following naming convention.

    Naming convention: YYYYMMDD-HHMMSS-{hostname}-n8n-{type}

    Args:
        base_path: Base directory for backups (e.g., /tmp/bkpfile)
        timestamp: Timestamp from generate_timestamp()
        hostname: Server hostname
        backup_type: Type of backup ('credentials' or 'workflows')

    Returns:
        Formatted Path object

    Example:
        >>> path = format_backup_path(
        ...     Path('/tmp/bkpfile'),
        ...     '20260120-140530',
        ...     'prod-server',
        ...     'credentials'
        ... )
        >>> assert 'n8n-credentials' in str(path)
    """
    # Sanitize hostname (replace spaces and special chars with dashes)
    safe_hostname = re.sub(r"[^\w\-]", "-", hostname.lower())

    directory_name = f"{timestamp}-{safe_hostname}-n8n-{backup_type}"
    return base_path / directory_name


def validate_json_file(file_path: Path) -> Dict[str, Any]:
    """Validate JSON file exists and has valid structure.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON data as dictionary

    Raises:
        ValidationError: If file doesn't exist, isn't valid JSON, or missing required fields

    Example:
        >>> data = validate_json_file(Path('/tmp/workflow.json'))
        >>> assert 'id' in data
        >>> assert 'name' in data
    """
    if not file_path.exists():
        raise ValidationError(
            f"JSON file not found: {file_path}",
            details={"file_path": str(file_path)},
        )

    if not file_path.is_file():
        raise ValidationError(
            f"Path is not a file: {file_path}",
            details={"file_path": str(file_path)},
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValidationError(
            f"Invalid JSON in file: {file_path}",
            details={"file_path": str(file_path), "error": str(e), "line": e.lineno},
        )
    except Exception as e:
        raise ValidationError(
            f"Failed to read JSON file: {file_path}",
            details={"file_path": str(file_path), "error": str(e)},
        )

    # Validate required fields for N8N export files
    if not isinstance(data, dict):
        raise ValidationError(
            f"JSON root must be an object/dict: {file_path}",
            details={"file_path": str(file_path), "type": type(data).__name__},
        )

    required_fields = ["id", "name"]
    missing_fields = [field for field in required_fields if field not in data]

    if missing_fields:
        raise ValidationError(
            f"JSON missing required fields: {', '.join(missing_fields)}",
            details={
                "file_path": str(file_path),
                "missing_fields": missing_fields,
                "available_fields": list(data.keys()),
            },
        )

    return data


def get_hostname() -> str:
    """Get system hostname for backup naming.

    Returns:
        System hostname (sanitized)

    Example:
        >>> hostname = get_hostname()
        >>> assert len(hostname) > 0
        >>> assert not hostname.isspace()
    """
    hostname = platform.node() or "unknown-host"
    # Sanitize hostname
    return re.sub(r"[^\w\-]", "-", hostname.lower())


def ensure_directory(path: Path, create: bool = True) -> Path:
    """Ensure directory exists, optionally creating it.

    Args:
        path: Directory path to check/create
        create: Whether to create directory if it doesn't exist

    Returns:
        Resolved absolute path

    Raises:
        ValidationError: If path exists but is not a directory

    Example:
        >>> dir_path = ensure_directory(Path('/tmp/backups'))
        >>> assert dir_path.is_dir()
    """
    path = path.resolve()

    if path.exists():
        if not path.is_dir():
            raise ValidationError(
                f"Path exists but is not a directory: {path}",
                details={"path": str(path)},
            )
    elif create:
        path.mkdir(parents=True, exist_ok=True)

    return path


def format_bytes(num_bytes: int) -> str:
    """Format bytes as human-readable string.

    Args:
        num_bytes: Number of bytes

    Returns:
        Formatted string (e.g., '1.5 GB', '256 MB')

    Example:
        >>> format_bytes(1073741824)
        '1.0 GB'
        >>> format_bytes(1536)
        '1.5 KB'
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


def get_disk_space(path: Path) -> Dict[str, int]:
    """Get disk space information for path.

    Args:
        path: Path to check disk space for

    Returns:
        Dictionary with 'total', 'used', 'free' in bytes

    Example:
        >>> space = get_disk_space(Path('/tmp'))
        >>> assert 'total' in space
        >>> assert space['free'] > 0
    """
    import shutil

    stat = shutil.disk_usage(path)
    return {
        "total": stat.total,
        "used": stat.used,
        "free": stat.free,
    }


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing/replacing unsafe characters.

    Args:
        filename: Original filename

    Returns:
        Safe filename

    Example:
        >>> sanitize_filename('my file: test.json')
        'my-file-test.json'
    """
    # Replace spaces and special chars with dash
    safe = re.sub(r"[^\w\.\-]", "-", filename)
    # Remove multiple consecutive dashes
    safe = re.sub(r"-+", "-", safe)
    # Remove leading/trailing dashes
    safe = safe.strip("-")
    return safe or "unnamed"


def parse_timestamp_from_path(path: Path) -> Optional[datetime]:
    """Extract timestamp from backup path following naming convention.

    Args:
        path: Backup directory path

    Returns:
        Parsed datetime or None if pattern not found

    Example:
        >>> path = Path('/tmp/20260120-140530-prod-n8n-credentials')
        >>> dt = parse_timestamp_from_path(path)
        >>> assert dt.year == 2026
        >>> assert dt.month == 1
        >>> assert dt.day == 20
    """
    # Pattern: YYYYMMDD-HHMMSS
    pattern = r"(\d{8})-(\d{6})"
    match = re.search(pattern, path.name)

    if not match:
        return None

    date_str = match.group(1)  # YYYYMMDD
    time_str = match.group(2)  # HHMMSS

    try:
        return datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
    except ValueError:
        return None
