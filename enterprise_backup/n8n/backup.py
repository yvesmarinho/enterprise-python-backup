"""N8N Backup Implementation.

Implements Constitution Principle II: ID Preservation
All backup operations use --backup flag to maintain original IDs.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

import docker
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .docker_manager import (
    find_n8n_container,
    exec_command,
    container_is_running,
    get_container_env,
)
from .exceptions import BackupError, ValidationError, DockerError, EncryptionKeyError
from .models import BackupOperation, BackupType, OperationStatus, BackupMetadata
from .utils import (
    generate_timestamp,
    get_hostname,
    calculate_sha256,
    calculate_directory_sha256,
    format_backup_path,
    validate_json_file,
    validate_json_structure,
    load_json_file,
    save_json_file,
)
from .validators import validate_prerequisites, validate_disk_space_available
from .storage import BackupRepository, LocalRepository
from . import OperationLogger, get_logger


logger = get_logger()


class N8NBackup:
    """N8N Backup Manager.

    Implements automatic backup of N8N credentials and workflows with:
    - ID preservation (--backup flag enforcement)
    - Integrity validation (JSON schema + checksums)
    - Structured logging (audit trail)
    - Retry logic (transient failure handling)
    - Storage abstraction (local/cloud agnostic)
    """

    def __init__(
        self,
        container_name: str = "n8n",
        backup_repository: Optional[BackupRepository] = None,
        docker_client: Optional[docker.DockerClient] = None,
    ) -> None:
        """Initialize N8N Backup Manager.

        Args:
            container_name: Name of the N8N Docker container
            backup_repository: Storage backend (defaults to LocalRepository)
            docker_client: Docker client (creates new if None)
        """
        self.container_name = container_name
        self.docker_client = docker_client or docker.from_env()
        self.backup_repository = backup_repository or LocalRepository(
            base_path=Path("/tmp/bkpfile/n8n")
        )
        self.logger = logging.getLogger(f"{__name__}.N8NBackup")

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        retry=retry_if_exception_type((DockerError, BackupError)),
        reraise=True,
    )
    def backup(
        self,
        backup_type: BackupType = BackupType.FULL,
        validate_integrity: bool = True,
    ) -> BackupOperation:
        """Execute N8N backup operation.

        Constitution Compliance:
        - Principle II: Uses --backup flag to preserve original IDs
        - Principle III: Validates JSON integrity and checksums
        - Principle IV: Structured logging with audit trail

        Args:
            backup_type: Type of backup (CREDENTIALS, WORKFLOWS, FULL)
            validate_integrity: Whether to validate JSON after export

        Returns:
            BackupOperation with status, files, checksums, duration

        Raises:
            ValidationError: Prerequisites failed or JSON validation failed
            EncryptionKeyError: N8N_ENCRYPTION_KEY not present
            DockerError: Container not running or exec failed
            BackupError: Export command failed or file not created
        """
        operation_id = str(uuid4())
        timestamp = generate_timestamp()
        hostname = get_hostname()
        start_time = datetime.utcnow()

        operation = BackupOperation(
            id=operation_id,
            timestamp=start_time,
            hostname=hostname,
            type=backup_type,
            status=OperationStatus.PENDING,
            files=[],
            duration_seconds=0.0,
            checksum_sha256="",
        )

        with OperationLogger(
            operation_type=f"backup_{backup_type.value}",
            operation_id=operation_id,
            logger=self.logger,
        ) as op_logger:
            try:
                operation.status = OperationStatus.IN_PROGRESS
                op_logger.log("Backup operation started", level="info")

                # Step 1: Validate prerequisites
                self._validate_prerequisites()
                op_logger.log("Prerequisites validation passed", level="info")

                # Step 2: Validate encryption key
                encryption_key = self._validate_encryption_key()
                op_logger.log("Encryption key validation passed", level="info")

                # Step 3: Find and validate container
                container = self._get_running_container()
                op_logger.log(
                    f"Container '{self.container_name}' found and running", level="info"
                )

                # Step 4: Create backup directory
                backup_dir = self._create_backup_directory(timestamp, hostname, backup_type)
                op_logger.log(f"Backup directory created: {backup_dir}", level="info")

                # Step 5: Export data based on backup type
                exported_files: List[Path] = []

                if backup_type in (BackupType.CREDENTIALS, BackupType.FULL):
                    cred_file = self._export_credentials(container, backup_dir)
                    exported_files.append(cred_file)
                    op_logger.log(f"Credentials exported: {cred_file.name}", level="info")

                if backup_type in (BackupType.WORKFLOWS, BackupType.FULL):
                    workflow_file = self._export_workflows(container, backup_dir)
                    exported_files.append(workflow_file)
                    op_logger.log(f"Workflows exported: {workflow_file.name}", level="info")

                # Step 6: Validate JSON integrity
                if validate_integrity:
                    self._validate_exported_files(exported_files, backup_type)
                    op_logger.log("JSON integrity validation passed", level="info")

                # Step 7: Calculate checksums
                file_checksums = self._calculate_checksums(exported_files)
                directory_checksum = calculate_directory_sha256(backup_dir)
                op_logger.log(f"Checksums calculated: {directory_checksum[:16]}...", level="info")

                # Step 8: Create backup metadata
                metadata = self._create_backup_metadata(
                    operation_id=operation_id,
                    backup_dir=backup_dir,
                    backup_type=backup_type,
                    file_checksums=file_checksums,
                    directory_checksum=directory_checksum,
                    encryption_key=encryption_key,
                    container=container,
                )
                self._save_metadata(backup_dir, metadata)
                op_logger.log("Backup metadata created", level="info")

                # Step 9: Upload to repository
                self.backup_repository.upload(backup_dir, operation_id)
                op_logger.log(f"Backup uploaded to repository", level="info")

                # Step 10: Update operation status
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()

                operation.status = OperationStatus.COMPLETED
                operation.files = [f.name for f in exported_files]
                operation.duration_seconds = duration
                operation.checksum_sha256 = directory_checksum

                op_logger.log(
                    f"Backup completed successfully in {duration:.2f}s",
                    level="info",
                    backup_id=operation_id,
                    files_count=len(exported_files),
                )

                return operation

            except (ValidationError, EncryptionKeyError, DockerError, BackupError) as e:
                operation.status = OperationStatus.FAILED
                operation.error_message = str(e)
                op_logger.log(f"Backup failed: {e}", level="error")
                raise

            except Exception as e:
                operation.status = OperationStatus.FAILED
                operation.error_message = str(e)
                op_logger.log(f"Unexpected error during backup: {e}", level="error")
                raise BackupError(
                    f"Unexpected error during backup: {e}",
                    operation_context={"operation_id": operation_id, "backup_type": backup_type.value},
                )

    def _validate_prerequisites(self) -> None:
        """Validate backup prerequisites.

        Raises:
            ValidationError: Prerequisites validation failed
        """
        result = validate_prerequisites(
            container_name=self.container_name,
            backup_path=Path("/tmp/bkpfile/n8n"),
            client=self.docker_client,
        )

        if not result.passed:
            error_msg = "Prerequisites validation failed:\n" + "\n".join(result.errors)
            raise ValidationError(error_msg)

        if result.warnings:
            for warning in result.warnings:
                self.logger.warning(f"Prerequisite warning: {warning}")

    def _validate_encryption_key(self) -> str:
        """Validate N8N encryption key is present.

        Returns:
            Encryption key value

        Raises:
            EncryptionKeyError: Encryption key not found
        """
        try:
            container = find_n8n_container(self.container_name, self.docker_client)
            encryption_key = get_container_env(container, "N8N_ENCRYPTION_KEY")

            if not encryption_key:
                raise EncryptionKeyError(
                    "N8N_ENCRYPTION_KEY environment variable not found in container. "
                    "This key is required to encrypt/decrypt credentials."
                )

            return encryption_key

        except DockerError as e:
            raise EncryptionKeyError(f"Failed to validate encryption key: {e}")

    def _get_running_container(self) -> docker.models.containers.Container:
        """Get running N8N container.

        Returns:
            Docker container object

        Raises:
            DockerError: Container not found or not running
        """
        container = find_n8n_container(self.container_name, self.docker_client)

        if not container_is_running(container):
            raise DockerError(
                f"Container '{self.container_name}' is not running. "
                f"Current status: {container.status}",
                operation_context={"container_name": self.container_name},
            )

        return container

    def _create_backup_directory(
        self, timestamp: str, hostname: str, backup_type: BackupType
    ) -> Path:
        """Create backup directory with timestamp naming.

        Args:
            timestamp: Timestamp string (YYYYMMDD-HHMMSS)
            hostname: Hostname identifier
            backup_type: Type of backup

        Returns:
            Path to created backup directory

        Raises:
            BackupError: Directory creation failed
        """
        try:
            backup_dir = format_backup_path(
                base_path=Path("/tmp/bkpfile/n8n"),
                timestamp=timestamp,
                hostname=hostname,
                backup_type=backup_type,
            )

            backup_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created backup directory: {backup_dir}")

            return backup_dir

        except Exception as e:
            raise BackupError(
                f"Failed to create backup directory: {e}",
                operation_context={"timestamp": timestamp, "hostname": hostname},
            )

    def _export_credentials(
        self, container: docker.models.containers.Container, backup_dir: Path
    ) -> Path:
        """Export N8N credentials with ID preservation.

        Constitution Principle II: Uses --backup flag to preserve original IDs.

        Args:
            container: Docker container
            backup_dir: Backup directory path

        Returns:
            Path to exported credentials file

        Raises:
            BackupError: Export command failed
        """
        output_file = backup_dir / "credentials.json"

        # Constitution Principle II: --backup flag MUST be used to preserve IDs
        command = f"n8n export:credentials --backup --output={output_file}"

        self.logger.debug(f"Executing: {command}")
        exit_code, output = exec_command(container, command)

        if exit_code != 0:
            raise BackupError(
                f"Credentials export failed with exit code {exit_code}: {output}",
                operation_context={"command": command, "exit_code": exit_code},
            )

        if not output_file.exists():
            raise BackupError(
                f"Credentials file not created: {output_file}",
                operation_context={"expected_file": str(output_file)},
            )

        self.logger.debug(f"Credentials exported successfully: {output_file}")
        return output_file

    def _export_workflows(
        self, container: docker.models.containers.Container, backup_dir: Path
    ) -> Path:
        """Export N8N workflows with ID preservation.

        Constitution Principle II: Uses --backup flag to preserve original IDs.

        Args:
            container: Docker container
            backup_dir: Backup directory path

        Returns:
            Path to exported workflows file

        Raises:
            BackupError: Export command failed
        """
        output_file = backup_dir / "workflows.json"

        # Constitution Principle II: --backup flag MUST be used to preserve IDs
        command = f"n8n export:workflow --backup --output={output_file}"

        self.logger.debug(f"Executing: {command}")
        exit_code, output = exec_command(container, command)

        if exit_code != 0:
            raise BackupError(
                f"Workflows export failed with exit code {exit_code}: {output}",
                operation_context={"command": command, "exit_code": exit_code},
            )

        if not output_file.exists():
            raise BackupError(
                f"Workflows file not created: {output_file}",
                operation_context={"expected_file": str(output_file)},
            )

        self.logger.debug(f"Workflows exported successfully: {output_file}")
        return output_file

    def _validate_exported_files(
        self, exported_files: List[Path], backup_type: BackupType
    ) -> None:
        """Validate JSON integrity of exported files.

        Constitution Principle III: Integrity validation before considering backup complete.

        Args:
            exported_files: List of exported file paths
            backup_type: Type of backup

        Raises:
            ValidationError: JSON validation failed
        """
        for file_path in exported_files:
            # Basic JSON syntax validation
            if not validate_json_file(file_path):
                raise ValidationError(
                    f"Invalid JSON in exported file: {file_path.name}",
                    operation_context={"file": str(file_path)},
                )

            # Validate required fields based on file type
            if "credentials" in file_path.name:
                required_fields = ["id", "name", "type", "data"]
                if not validate_json_structure(file_path, required_fields):
                    raise ValidationError(
                        f"Credentials file missing required fields: {required_fields}",
                        operation_context={"file": str(file_path)},
                    )

            elif "workflows" in file_path.name:
                required_fields = ["id", "name", "nodes", "connections"]
                if not validate_json_structure(file_path, required_fields):
                    raise ValidationError(
                        f"Workflows file missing required fields: {required_fields}",
                        operation_context={"file": str(file_path)},
                    )

            self.logger.debug(f"JSON validation passed: {file_path.name}")

    def _calculate_checksums(self, exported_files: List[Path]) -> Dict[str, str]:
        """Calculate SHA256 checksums for exported files.

        Args:
            exported_files: List of exported file paths

        Returns:
            Dictionary mapping file names to SHA256 checksums
        """
        checksums = {}
        for file_path in exported_files:
            checksum = calculate_sha256(file_path)
            checksums[file_path.name] = checksum
            self.logger.debug(f"Checksum for {file_path.name}: {checksum[:16]}...")

        return checksums

    def _create_backup_metadata(
        self,
        operation_id: str,
        backup_dir: Path,
        backup_type: BackupType,
        file_checksums: Dict[str, str],
        directory_checksum: str,
        encryption_key: str,
        container: docker.models.containers.Container,
    ) -> BackupMetadata:
        """Create backup metadata.

        Args:
            operation_id: Unique operation ID
            backup_dir: Backup directory path
            backup_type: Type of backup
            file_checksums: Individual file checksums
            directory_checksum: Combined directory checksum
            encryption_key: N8N encryption key
            container: Docker container

        Returns:
            BackupMetadata object
        """
        # Calculate total size
        total_size = sum(f.stat().st_size for f in backup_dir.glob("*.json"))

        # Get N8N version from container
        exit_code, version_output = exec_command(container, "n8n --version")
        n8n_version = version_output.strip() if exit_code == 0 else "unknown"

        # Hash encryption key for verification (don't store plaintext)
        import hashlib
        key_hash = hashlib.sha256(encryption_key.encode()).hexdigest()

        metadata = BackupMetadata(
            backup_id=operation_id,
            created_at=datetime.utcnow(),
            hostname=get_hostname(),
            type=backup_type,
            file_count=len(file_checksums),
            total_size_bytes=total_size,
            checksum_sha256=directory_checksum,
            encryption_key_hash=key_hash,
            n8n_version=n8n_version,
        )

        return metadata

    def _save_metadata(self, backup_dir: Path, metadata: BackupMetadata) -> None:
        """Save backup metadata to JSON file.

        Args:
            backup_dir: Backup directory path
            metadata: Backup metadata object
        """
        metadata_file = backup_dir / "metadata.json"
        metadata_dict = metadata.model_dump(mode="json")
        save_json_file(metadata_dict, metadata_file)
        self.logger.debug(f"Metadata saved: {metadata_file}")
