"""Storage abstraction for backup repositories (local, S3, Azure)."""

import os
import tarfile
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

from .exceptions import StorageError
from .utils import calculate_sha256, parse_timestamp_from_path


class BackupRepository(ABC):
    """Abstract base class for backup storage backends."""

    @abstractmethod
    def upload(
        self,
        local_path: Path,
        remote_key: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Upload backup to storage.

        Args:
            local_path: Local file or directory path
            remote_key: Remote storage key/path
            metadata: Optional metadata to store with backup

        Returns:
            Remote URI or key of uploaded backup

        Raises:
            StorageError: If upload fails
        """
        pass

    @abstractmethod
    def download(self, remote_key: str, local_path: Path) -> Path:
        """Download backup from storage.

        Args:
            remote_key: Remote storage key/path
            local_path: Local destination path

        Returns:
            Path to downloaded file

        Raises:
            StorageError: If download fails
        """
        pass

    @abstractmethod
    def list_backups(
        self, prefix: Optional[str] = None, max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """List available backups in storage.

        Args:
            prefix: Optional prefix to filter backups
            max_results: Maximum number of results

        Returns:
            List of backup metadata dictionaries

        Raises:
            StorageError: If listing fails
        """
        pass

    @abstractmethod
    def delete(self, remote_key: str) -> None:
        """Delete backup from storage.

        Args:
            remote_key: Remote storage key/path

        Raises:
            StorageError: If deletion fails
        """
        pass

    @abstractmethod
    def exists(self, remote_key: str) -> bool:
        """Check if backup exists in storage.

        Args:
            remote_key: Remote storage key/path

        Returns:
            True if backup exists
        """
        pass


class LocalRepository(BackupRepository):
    """Local filesystem storage for backups.

    Implements retention policy with automatic cleanup of old backups.
    """

    def __init__(
        self,
        base_path: Path,
        retention_days: int = 7,
        compress: bool = True,
    ) -> None:
        """Initialize local repository.

        Args:
            base_path: Base directory for backups
            retention_days: Days to keep backups (0 = keep forever)
            compress: Whether to compress backups as tar.gz
        """
        self.base_path = Path(base_path).resolve()
        self.retention_days = retention_days
        self.compress = compress

        # Ensure base path exists
        self.base_path.mkdir(parents=True, exist_ok=True)

    def upload(
        self,
        local_path: Path,
        remote_key: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Copy backup to local storage (optionally compressed).

        Args:
            local_path: Source file or directory
            remote_key: Destination filename/directory name
            metadata: Optional metadata (saved as .meta file)

        Returns:
            Absolute path to stored backup
        """
        local_path = Path(local_path)
        destination = self.base_path / remote_key

        try:
            if local_path.is_dir():
                if self.compress:
                    # Compress directory to tar.gz
                    destination = destination.with_suffix(".tar.gz")
                    with tarfile.open(destination, "w:gz") as tar:
                        tar.add(local_path, arcname=local_path.name)
                else:
                    # Copy directory recursively
                    import shutil

                    if destination.exists():
                        shutil.rmtree(destination)
                    shutil.copytree(local_path, destination)
            else:
                # Copy single file
                import shutil

                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(local_path, destination)

            # Save metadata if provided
            if metadata:
                meta_file = destination.with_suffix(destination.suffix + ".meta")
                import json

                meta_file.write_text(json.dumps(metadata, indent=2))

            return str(destination)

        except Exception as e:
            raise StorageError(
                f"Failed to upload to local storage: {local_path} -> {remote_key}",
                details={"error": str(e), "destination": str(destination)},
            )

    def download(self, remote_key: str, local_path: Path) -> Path:
        """Copy backup from local storage to specified path.

        Args:
            remote_key: Source filename/directory name
            local_path: Destination path

        Returns:
            Path to downloaded file
        """
        source = self.base_path / remote_key
        local_path = Path(local_path)

        if not source.exists():
            raise StorageError(
                f"Backup not found in local storage: {remote_key}",
                details={"source": str(source)},
            )

        try:
            if source.suffix == ".gz" and tarfile.is_tarfile(source):
                # Extract tar.gz
                local_path.mkdir(parents=True, exist_ok=True)
                with tarfile.open(source, "r:gz") as tar:
                    tar.extractall(local_path)
            elif source.is_dir():
                # Copy directory
                import shutil

                if local_path.exists():
                    shutil.rmtree(local_path)
                shutil.copytree(source, local_path)
            else:
                # Copy file
                import shutil

                local_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, local_path)

            return local_path

        except Exception as e:
            raise StorageError(
                f"Failed to download from local storage: {remote_key}",
                details={"error": str(e), "source": str(source)},
            )

    def list_backups(
        self, prefix: Optional[str] = None, max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """List available backups in local storage.

        Returns:
            List of backup metadata sorted by timestamp (newest first)
        """
        backups = []

        try:
            # Find all backup directories and archives
            pattern = f"{prefix}*" if prefix else "*"

            for path in self.base_path.glob(pattern):
                if path.name.startswith("."):
                    continue  # Skip hidden files

                # Parse timestamp from path name
                timestamp = parse_timestamp_from_path(path)

                # Get file/dir info
                if path.is_dir():
                    size = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
                else:
                    size = path.stat().st_size

                backups.append(
                    {
                        "key": path.name,
                        "path": str(path),
                        "size": size,
                        "timestamp": timestamp,
                        "modified": datetime.fromtimestamp(path.stat().st_mtime),
                        "type": "directory" if path.is_dir() else "file",
                    }
                )

            # Sort by timestamp (newest first)
            backups.sort(key=lambda x: x["timestamp"] or x["modified"], reverse=True)

            return backups[:max_results]

        except Exception as e:
            raise StorageError(
                "Failed to list local backups",
                details={"error": str(e), "base_path": str(self.base_path)},
            )

    def delete(self, remote_key: str) -> None:
        """Delete backup from local storage.

        Args:
            remote_key: Backup filename/directory name
        """
        path = self.base_path / remote_key

        if not path.exists():
            return  # Already deleted

        try:
            if path.is_dir():
                import shutil

                shutil.rmtree(path)
            else:
                path.unlink()

            # Delete metadata file if exists
            meta_file = path.with_suffix(path.suffix + ".meta")
            if meta_file.exists():
                meta_file.unlink()

        except Exception as e:
            raise StorageError(
                f"Failed to delete backup: {remote_key}",
                details={"error": str(e), "path": str(path)},
            )

    def exists(self, remote_key: str) -> bool:
        """Check if backup exists in local storage."""
        return (self.base_path / remote_key).exists()

    def cleanup_old_backups(self) -> List[str]:
        """Remove backups older than retention period.

        Returns:
            List of deleted backup keys
        """
        if self.retention_days <= 0:
            return []  # Keep forever

        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        deleted = []

        for backup in self.list_backups():
            backup_date = backup["timestamp"] or backup["modified"]

            if backup_date < cutoff_date:
                try:
                    self.delete(backup["key"])
                    deleted.append(backup["key"])
                except StorageError:
                    pass  # Continue with other backups

        return deleted


# Placeholder classes for cloud storage (to be implemented in Phase 5: US3)


class S3Repository(BackupRepository):
    """AWS S3 storage for backups (placeholder for Phase 5)."""

    def __init__(
        self,
        bucket: str,
        region: str = "us-east-1",
        prefix: str = "",
        **kwargs: Any,
    ) -> None:
        """Initialize S3 repository."""
        raise NotImplementedError("S3Repository will be implemented in Phase 5 (US3)")

    def upload(
        self,
        local_path: Path,
        remote_key: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Upload to S3."""
        raise NotImplementedError("S3Repository will be implemented in Phase 5 (US3)")

    def download(self, remote_key: str, local_path: Path) -> Path:
        """Download from S3."""
        raise NotImplementedError("S3Repository will be implemented in Phase 5 (US3)")

    def list_backups(
        self, prefix: Optional[str] = None, max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """List S3 backups."""
        raise NotImplementedError("S3Repository will be implemented in Phase 5 (US3)")

    def delete(self, remote_key: str) -> None:
        """Delete from S3."""
        raise NotImplementedError("S3Repository will be implemented in Phase 5 (US3)")

    def exists(self, remote_key: str) -> bool:
        """Check if exists in S3."""
        raise NotImplementedError("S3Repository will be implemented in Phase 5 (US3)")


class AzureRepository(BackupRepository):
    """Azure Blob Storage for backups (placeholder for Phase 5)."""

    def __init__(
        self,
        container: str,
        account_name: str,
        account_key: str,
        prefix: str = "",
        **kwargs: Any,
    ) -> None:
        """Initialize Azure repository."""
        raise NotImplementedError("AzureRepository will be implemented in Phase 5 (US3)")

    def upload(
        self,
        local_path: Path,
        remote_key: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """Upload to Azure."""
        raise NotImplementedError("AzureRepository will be implemented in Phase 5 (US3)")

    def download(self, remote_key: str, local_path: Path) -> Path:
        """Download from Azure."""
        raise NotImplementedError("AzureRepository will be implemented in Phase 5 (US3)")

    def list_backups(
        self, prefix: Optional[str] = None, max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """List Azure backups."""
        raise NotImplementedError("AzureRepository will be implemented in Phase 5 (US3)")

    def delete(self, remote_key: str) -> None:
        """Delete from Azure."""
        raise NotImplementedError("AzureRepository will be implemented in Phase 5 (US3)")

    def exists(self, remote_key: str) -> bool:
        """Check if exists in Azure."""
        raise NotImplementedError("AzureRepository will be implemented in Phase 5 (US3)")
