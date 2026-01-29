"""Validators for pre-operation and post-operation checks."""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from .docker_manager import DockerManager
from .exceptions import EncryptionKeyError, ValidationError, DiskSpaceError


class PrerequisiteValidator:
    """Validates prerequisites before backup/restore operations.

    Implements comprehensive validation checks to ensure operations can proceed safely.
    """

    def __init__(
        self,
        docker_manager: DockerManager,
        backup_path: Path,
        min_disk_percent: float = 10.0,
        min_disk_bytes: int = 1073741824,  # 1 GB
    ) -> None:
        """Initialize validator.

        Args:
            docker_manager: Docker manager instance
            backup_path: Base path for backups
            min_disk_percent: Minimum free disk space percentage
            min_disk_bytes: Minimum free disk space in bytes
        """
        self.docker_manager = docker_manager
        self.backup_path = backup_path
        self.min_disk_percent = min_disk_percent
        self.min_disk_bytes = min_disk_bytes

    def validate_all(self) -> Dict[str, bool]:
        """Run all prerequisite validations.

        Returns:
            Dictionary of validation results {check_name: passed}

        Raises:
            ValidationError: If any critical validation fails
        """
        results = {}
        errors = []

        # Container exists and is accessible
        try:
            self.validate_container_exists()
            results["container_exists"] = True
        except ValidationError as e:
            results["container_exists"] = False
            errors.append(str(e))

        # Volume mounted (N8N data directory)
        try:
            self.validate_volume_mounted()
            results["volume_mounted"] = True
        except ValidationError as e:
            results["volume_mounted"] = False
            errors.append(str(e))

        # Encryption key present
        try:
            self.validate_encryption_key_present()
            results["encryption_key_present"] = True
        except EncryptionKeyError as e:
            results["encryption_key_present"] = False
            errors.append(str(e))

        # Disk space available
        try:
            self.validate_disk_space_available()
            results["disk_space_available"] = True
        except DiskSpaceError as e:
            results["disk_space_available"] = False
            errors.append(str(e))

        # Backup path writable
        try:
            self.validate_backup_path_writable()
            results["backup_path_writable"] = True
        except ValidationError as e:
            results["backup_path_writable"] = False
            errors.append(str(e))

        # If any critical validation failed, raise error
        if errors:
            raise ValidationError(
                f"Prerequisite validation failed: {len(errors)} check(s) failed",
                details={
                    "failed_checks": [k for k, v in results.items() if not v],
                    "errors": errors,
                    "results": results,
                },
            )

        return results

    def validate_container_exists(self) -> None:
        """Validate N8N container exists and is accessible.

        Raises:
            ValidationError: If container doesn't exist or isn't accessible
        """
        try:
            container = self.docker_manager.find_n8n_container()

            if container.status not in ["running", "paused"]:
                raise ValidationError(
                    f"N8N container exists but is not running: {container.status}",
                    details={
                        "container_name": container.name,
                        "status": container.status,
                        "suggestion": f"Start container: docker start {container.name}",
                    },
                )

        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(
                "Failed to validate container existence",
                details={"error": str(e)},
            )

    def validate_volume_mounted(self) -> None:
        """Validate N8N data volume is mounted.

        N8N stores data in /home/node/.n8n directory inside container.
        This should be mounted as a volume for persistence.

        Raises:
            ValidationError: If volume not properly mounted
        """
        try:
            container = self.docker_manager.find_n8n_container()
            mounts = container.attrs.get("Mounts", [])

            # Check if /home/node/.n8n is mounted as a volume
            n8n_data_mounted = False
            for mount in mounts:
                destination = mount.get("Destination", "")
                if "/home/node/.n8n" in destination:
                    n8n_data_mounted = True
                    break

            if not n8n_data_mounted:
                raise ValidationError(
                    "N8N data directory not mounted as volume",
                    details={
                        "expected_path": "/home/node/.n8n",
                        "mounts": [m.get("Destination") for m in mounts],
                        "suggestion": "Mount N8N data directory as volume for persistence",
                    },
                )

        except Exception as e:
            if isinstance(e, ValidationError):
                raise
            raise ValidationError(
                "Failed to validate volume mount",
                details={"error": str(e)},
            )

    def validate_encryption_key_present(self) -> None:
        """Validate N8N_ENCRYPTION_KEY is set in container.

        Raises:
            EncryptionKeyError: If key is missing or empty
        """
        key = self.docker_manager.get_container_env("N8N_ENCRYPTION_KEY")

        if not key:
            raise EncryptionKeyError(
                "N8N_ENCRYPTION_KEY not found in container environment",
                details={
                    "container": self.docker_manager.container_name,
                    "suggestion": "Set N8N_ENCRYPTION_KEY environment variable in container",
                },
            )

        if len(key.strip()) < 10:
            raise EncryptionKeyError(
                "N8N_ENCRYPTION_KEY appears invalid (too short)",
                details={
                    "key_length": len(key),
                    "suggestion": "Verify encryption key is properly configured",
                },
            )

    def validate_disk_space_available(self) -> None:
        """Validate sufficient disk space is available for backup.

        Raises:
            DiskSpaceError: If insufficient disk space
        """
        # Ensure backup path exists to check its filesystem
        self.backup_path.mkdir(parents=True, exist_ok=True)

        stat = shutil.disk_usage(self.backup_path)
        total = stat.total
        free = stat.free
        percent_free = (free / total * 100) if total > 0 else 0

        # Check percentage threshold
        if percent_free < self.min_disk_percent:
            raise DiskSpaceError(
                f"Insufficient disk space: {percent_free:.1f}% free (minimum: {self.min_disk_percent}%)",
                details={
                    "path": str(self.backup_path),
                    "total_bytes": total,
                    "free_bytes": free,
                    "percent_free": percent_free,
                    "threshold_percent": self.min_disk_percent,
                    "suggestion": "Clean up old backups or increase disk space",
                },
            )

        # Check absolute threshold
        if free < self.min_disk_bytes:
            raise DiskSpaceError(
                f"Insufficient disk space: {free} bytes free (minimum: {self.min_disk_bytes} bytes)",
                details={
                    "path": str(self.backup_path),
                    "free_bytes": free,
                    "threshold_bytes": self.min_disk_bytes,
                    "suggestion": "Clean up old backups or increase disk space",
                },
            )

    def validate_backup_path_writable(self) -> None:
        """Validate backup path is writable.

        Raises:
            ValidationError: If path is not writable
        """
        # Ensure path exists
        self.backup_path.mkdir(parents=True, exist_ok=True)

        # Try to create a test file
        test_file = self.backup_path / ".write_test"
        try:
            test_file.write_text("test")
            test_file.unlink()
        except Exception as e:
            raise ValidationError(
                f"Backup path is not writable: {self.backup_path}",
                details={
                    "path": str(self.backup_path),
                    "error": str(e),
                    "suggestion": "Check file permissions and ownership",
                },
            )

    def validate_encryption_key_match(
        self, expected_key_hash: Optional[str] = None
    ) -> bool:
        """Validate encryption key matches expected hash (for restore).

        Args:
            expected_key_hash: SHA256 hash of expected encryption key

        Returns:
            True if keys match or no expected hash provided

        Raises:
            EncryptionKeyError: If keys don't match
        """
        if not expected_key_hash:
            return True  # No comparison needed

        current_key = self.docker_manager.get_container_env("N8N_ENCRYPTION_KEY")

        if not current_key:
            raise EncryptionKeyError(
                "N8N_ENCRYPTION_KEY not found for comparison",
                details={
                    "expected_hash": expected_key_hash[:16] + "...",
                    "suggestion": "Set N8N_ENCRYPTION_KEY in container",
                },
            )

        # Hash current key
        import hashlib

        current_hash = hashlib.sha256(current_key.encode()).hexdigest()

        if current_hash != expected_key_hash:
            raise EncryptionKeyError(
                "N8N_ENCRYPTION_KEY mismatch between backup and current container",
                details={
                    "expected_hash": expected_key_hash[:16] + "...",
                    "current_hash": current_hash[:16] + "...",
                    "suggestion": "Use the same encryption key as the source backup",
                },
            )

        return True


def validate_backup_integrity(backup_path: Path) -> List[str]:
    """Validate backup directory structure and files.

    Args:
        backup_path: Path to backup directory

    Returns:
        List of validation warnings (empty if all OK)

    Raises:
        ValidationError: If backup is invalid
    """
    if not backup_path.exists():
        raise ValidationError(
            f"Backup directory not found: {backup_path}",
            details={"path": str(backup_path)},
        )

    if not backup_path.is_dir():
        raise ValidationError(
            f"Backup path is not a directory: {backup_path}",
            details={"path": str(backup_path)},
        )

    # Check for JSON files
    json_files = list(backup_path.glob("*.json"))

    if not json_files:
        raise ValidationError(
            f"No JSON files found in backup directory: {backup_path}",
            details={
                "path": str(backup_path),
                "files_found": [f.name for f in backup_path.iterdir()],
            },
        )

    warnings = []

    # Validate each JSON file
    from .utils import validate_json_file

    for json_file in json_files:
        try:
            validate_json_file(json_file)
        except ValidationError as e:
            warnings.append(f"Invalid JSON in {json_file.name}: {e.message}")

    return warnings
