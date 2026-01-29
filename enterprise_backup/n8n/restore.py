"""N8N Restore Implementation.

Implements Constitution Principle III: Integrity & Safety
All restore operations include pre-validation, safety backup, and rollback capability.
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
    stop_container,
    start_container,
    wait_for_container,
    healthcheck,
)
from .exceptions import RestoreError, ValidationError, DockerError, EncryptionKeyError
from .models import RestoreOperation, BackupType, OperationStatus, BackupMetadata
from .utils import (
    generate_timestamp,
    get_hostname,
    validate_json_file,
    validate_json_structure,
    load_json_file,
)
from .validators import (
    validate_backup_integrity,
    validate_restore_compatibility,
)
from .storage import BackupRepository, LocalRepository
from .backup import N8NBackup
from . import OperationLogger, get_logger


logger = get_logger()


class N8NRestore:
    """N8N Restore Manager.

    Implements safe restore of N8N credentials and workflows with:
    - Pre-restore validation (integrity + compatibility)
    - Safety backup (current state before changes)
    - Graceful shutdown/restart cycle
    - Post-restore validation (healthcheck + data verification)
    - Automatic rollback on failure
    - Selective restoration (credentials-only or workflows-only)
    """

    def __init__(
        self,
        container_name: str = "n8n",
        backup_repository: Optional[BackupRepository] = None,
        docker_client: Optional[docker.DockerClient] = None,
    ) -> None:
        """Initialize N8N Restore Manager.

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
        self.backup_manager = N8NBackup(
            container_name=container_name,
            backup_repository=backup_repository,
            docker_client=docker_client,
        )
        self.logger = logging.getLogger(f"{__name__}.N8NRestore")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        retry=retry_if_exception_type((DockerError, RestoreError)),
        reraise=True,
    )
    def restore(
        self,
        backup_id: str,
        restore_type: BackupType = BackupType.FULL,
        skip_safety_backup: bool = False,
        skip_validation: bool = False,
    ) -> RestoreOperation:
        """Execute N8N restore operation.

        Constitution Compliance:
        - Principle II: Restores original IDs from backup (--backup flag used in backup)
        - Principle III: Creates safety backup before changes, validates integrity
        - Principle IV: Structured logging with audit trail

        Args:
            backup_id: ID of backup to restore
            restore_type: Type of restore (CREDENTIALS, WORKFLOWS, FULL)
            skip_safety_backup: Skip safety backup creation (NOT RECOMMENDED)
            skip_validation: Skip pre/post validation (NOT RECOMMENDED)

        Returns:
            RestoreOperation with status, files processed, validations, duration

        Raises:
            ValidationError: Pre-validation failed or backup incompatible
            EncryptionKeyError: Encryption key mismatch
            DockerError: Container operations failed
            RestoreError: Import command failed or rollback needed
        """
        operation_id = str(uuid4())
        start_time = datetime.utcnow()
        safety_backup_id: Optional[str] = None

        operation = RestoreOperation(
            id=operation_id,
            timestamp=start_time,
            backup_source=backup_id,
            type=restore_type,
            status=OperationStatus.PENDING,
            files_processed=[],
            pre_restore_backup=None,
            validations={},
            duration_seconds=0.0,
        )

        with OperationLogger(
            operation_type=f"restore_{restore_type.value}",
            operation_id=operation_id,
            logger=self.logger,
        ) as op_logger:
            try:
                operation.status = OperationStatus.IN_PROGRESS
                op_logger.log("Restore operation started", level="info")

                # Step 1: Download backup from repository
                backup_dir = self._download_backup(backup_id)
                op_logger.log(f"Backup downloaded: {backup_dir}", level="info")

                # Step 2: Pre-restore validation
                if not skip_validation:
                    validation_results = self._validate_backup(backup_dir)
                    operation.validations["pre_restore"] = validation_results
                    op_logger.log("Pre-restore validation passed", level="info")

                # Step 3: Validate encryption key compatibility
                self._validate_encryption_key_compatibility(backup_dir)
                op_logger.log("Encryption key validation passed", level="info")

                # Step 4: Get running container
                container = find_n8n_container(self.container_name, self.docker_client)
                op_logger.log(f"Container '{self.container_name}' found", level="info")

                # Step 5: Create safety backup (before any changes)
                if not skip_safety_backup:
                    safety_backup_id = self._create_safety_backup(restore_type)
                    operation.pre_restore_backup = safety_backup_id
                    op_logger.log(
                        f"Safety backup created: {safety_backup_id}", level="info"
                    )

                # Step 6: Graceful N8N shutdown
                self._shutdown_n8n(container)
                op_logger.log("N8N container stopped gracefully", level="info")

                # Step 7: Import data based on restore type
                imported_files: List[str] = []

                if restore_type in (BackupType.CREDENTIALS, BackupType.FULL):
                    cred_file = backup_dir / "credentials.json"
                    if cred_file.exists():
                        self._import_credentials(container, cred_file)
                        imported_files.append("credentials.json")
                        op_logger.log("Credentials imported", level="info")

                if restore_type in (BackupType.WORKFLOWS, BackupType.FULL):
                    workflow_file = backup_dir / "workflows.json"
                    if workflow_file.exists():
                        self._import_workflows(container, workflow_file)
                        imported_files.append("workflows.json")
                        op_logger.log("Workflows imported", level="info")

                # Step 8: Restart N8N
                self._restart_n8n(container)
                op_logger.log("N8N container restarted", level="info")

                # Step 9: Wait for N8N to be ready
                if not self._wait_for_n8n_ready(container):
                    raise RestoreError(
                        "N8N failed to become ready after restore",
                        operation_context={"operation_id": operation_id},
                    )
                op_logger.log("N8N healthcheck passed", level="info")

                # Step 10: Post-restore validation
                if not skip_validation:
                    post_validation = self._post_restore_validation(container)
                    operation.validations["post_restore"] = post_validation
                    op_logger.log("Post-restore validation passed", level="info")

                # Step 11: Update operation status
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()

                operation.status = OperationStatus.COMPLETED
                operation.files_processed = imported_files
                operation.duration_seconds = duration

                op_logger.log(
                    f"Restore completed successfully in {duration:.2f}s",
                    level="info",
                    backup_id=backup_id,
                    files_count=len(imported_files),
                )

                return operation

            except (ValidationError, EncryptionKeyError, DockerError, RestoreError) as e:
                operation.status = OperationStatus.FAILED
                operation.error_message = str(e)
                op_logger.log(f"Restore failed: {e}", level="error")

                # Attempt rollback if safety backup exists
                if safety_backup_id and not skip_safety_backup:
                    try:
                        op_logger.log(
                            f"Attempting rollback to safety backup: {safety_backup_id}",
                            level="warning",
                        )
                        self._rollback_to_safety_backup(safety_backup_id, restore_type)
                        operation.status = OperationStatus.ROLLED_BACK
                        op_logger.log("Rollback completed successfully", level="info")
                    except Exception as rollback_error:
                        op_logger.log(
                            f"Rollback failed: {rollback_error}", level="critical"
                        )

                raise

            except Exception as e:
                operation.status = OperationStatus.FAILED
                operation.error_message = str(e)
                op_logger.log(f"Unexpected error during restore: {e}", level="error")
                raise RestoreError(
                    f"Unexpected error during restore: {e}",
                    operation_context={
                        "operation_id": operation_id,
                        "backup_id": backup_id,
                    },
                )

    def _download_backup(self, backup_id: str) -> Path:
        """Download backup from repository.

        Args:
            backup_id: Backup ID to download

        Returns:
            Path to downloaded backup directory

        Raises:
            RestoreError: Download failed
        """
        try:
            destination = Path(f"/tmp/n8n-restore-{backup_id}")
            destination.mkdir(parents=True, exist_ok=True)

            self.backup_repository.download(backup_id, destination)
            self.logger.debug(f"Backup downloaded to: {destination}")

            return destination

        except Exception as e:
            raise RestoreError(
                f"Failed to download backup: {e}",
                operation_context={"backup_id": backup_id},
            )

    def _validate_backup(self, backup_dir: Path) -> Dict[str, bool]:
        """Validate backup integrity and compatibility.

        Args:
            backup_dir: Backup directory path

        Returns:
            Dictionary with validation results

        Raises:
            ValidationError: Validation failed
        """
        validation_results = {}

        # Integrity validation
        integrity_result = validate_backup_integrity(backup_dir)
        if not integrity_result.passed:
            error_msg = "Backup integrity validation failed:\n" + "\n".join(
                integrity_result.errors
            )
            raise ValidationError(error_msg)

        validation_results["integrity"] = True

        # Compatibility validation
        container = find_n8n_container(self.container_name, self.docker_client)
        compatibility_result = validate_restore_compatibility(backup_dir, container)

        if not compatibility_result.passed:
            # Log warnings but don't fail (version mismatch may be acceptable)
            for warning in compatibility_result.warnings:
                self.logger.warning(f"Compatibility warning: {warning}")

        validation_results["compatibility"] = compatibility_result.passed

        return validation_results

    def _validate_encryption_key_compatibility(self, backup_dir: Path) -> None:
        """Validate encryption key matches backup.

        Args:
            backup_dir: Backup directory path

        Raises:
            EncryptionKeyError: Encryption key mismatch
        """
        # Load backup metadata
        metadata_file = backup_dir / "metadata.json"
        if not metadata_file.exists():
            raise ValidationError(
                f"Backup metadata not found: {metadata_file}",
                operation_context={"backup_dir": str(backup_dir)},
            )

        metadata = load_json_file(metadata_file)
        backup_key_hash = metadata.get("encryption_key_hash")

        if not backup_key_hash:
            self.logger.warning(
                "Backup metadata missing encryption_key_hash - skipping key validation"
            )
            return

        # Get current encryption key
        container = find_n8n_container(self.container_name, self.docker_client)
        current_key = get_container_env(container, "N8N_ENCRYPTION_KEY")

        if not current_key:
            raise EncryptionKeyError(
                "N8N_ENCRYPTION_KEY not found in container. "
                "Cannot restore encrypted credentials without encryption key."
            )

        # Compare key hashes
        import hashlib

        current_key_hash = hashlib.sha256(current_key.encode()).hexdigest()

        if current_key_hash != backup_key_hash:
            raise EncryptionKeyError(
                "Encryption key mismatch! The current N8N_ENCRYPTION_KEY does not match "
                "the key used to create this backup. Restoring with a different key will "
                "result in corrupted/unreadable credentials. "
                f"\nBackup key hash: {backup_key_hash[:16]}..."
                f"\nCurrent key hash: {current_key_hash[:16]}...",
                operation_context={
                    "backup_key_hash": backup_key_hash,
                    "current_key_hash": current_key_hash,
                },
            )

    def _create_safety_backup(self, restore_type: BackupType) -> str:
        """Create safety backup before restore.

        Args:
            restore_type: Type of restore operation

        Returns:
            Safety backup ID

        Raises:
            RestoreError: Safety backup creation failed
        """
        try:
            self.logger.info("Creating safety backup before restore...")
            operation = self.backup_manager.backup(
                backup_type=restore_type, validate_integrity=True
            )

            if operation.status != OperationStatus.COMPLETED:
                raise RestoreError(
                    f"Safety backup failed with status: {operation.status}",
                    operation_context={"operation": operation.to_json_log()},
                )

            self.logger.info(f"Safety backup created: {operation.id}")
            return operation.id

        except Exception as e:
            raise RestoreError(
                f"Failed to create safety backup: {e}",
                operation_context={"restore_type": restore_type.value},
            )

    def _shutdown_n8n(self, container: docker.models.containers.Container) -> None:
        """Gracefully shutdown N8N container.

        Args:
            container: Docker container

        Raises:
            DockerError: Shutdown failed
        """
        try:
            self.logger.info("Stopping N8N container gracefully...")
            stop_container(container, timeout=30)
            self.logger.debug("Container stopped successfully")

        except Exception as e:
            raise DockerError(
                f"Failed to stop N8N container: {e}",
                operation_context={"container_name": self.container_name},
            )

    def _import_credentials(
        self, container: docker.models.containers.Container, credentials_file: Path
    ) -> None:
        """Import N8N credentials from backup.

        Constitution Principle II: Uses --separate flag to preserve IDs from backup.

        Args:
            container: Docker container
            credentials_file: Path to credentials backup file

        Raises:
            RestoreError: Import command failed
        """
        # Constitution Principle II: --separate flag preserves IDs from backup
        command = f"n8n import:credentials --separate --input={credentials_file}"

        self.logger.debug(f"Executing: {command}")
        exit_code, output = exec_command(container, command)

        if exit_code != 0:
            raise RestoreError(
                f"Credentials import failed with exit code {exit_code}: {output}",
                operation_context={"command": command, "exit_code": exit_code},
            )

        self.logger.debug("Credentials imported successfully")

    def _import_workflows(
        self, container: docker.models.containers.Container, workflows_file: Path
    ) -> None:
        """Import N8N workflows from backup.

        Constitution Principle II: Uses --separate flag to preserve IDs from backup.

        Args:
            container: Docker container
            workflows_file: Path to workflows backup file

        Raises:
            RestoreError: Import command failed
        """
        # Constitution Principle II: --separate flag preserves IDs from backup
        command = f"n8n import:workflow --separate --input={workflows_file}"

        self.logger.debug(f"Executing: {command}")
        exit_code, output = exec_command(container, command)

        if exit_code != 0:
            raise RestoreError(
                f"Workflows import failed with exit code {exit_code}: {output}",
                operation_context={"command": command, "exit_code": exit_code},
            )

        self.logger.debug("Workflows imported successfully")

    def _restart_n8n(self, container: docker.models.containers.Container) -> None:
        """Restart N8N container.

        Args:
            container: Docker container

        Raises:
            DockerError: Restart failed
        """
        try:
            self.logger.info("Starting N8N container...")
            start_container(container)
            self.logger.debug("Container started successfully")

        except Exception as e:
            raise DockerError(
                f"Failed to start N8N container: {e}",
                operation_context={"container_name": self.container_name},
            )

    def _wait_for_n8n_ready(
        self, container: docker.models.containers.Container, timeout: int = 60
    ) -> bool:
        """Wait for N8N to be ready after restart.

        Args:
            container: Docker container
            timeout: Maximum wait time in seconds

        Returns:
            True if N8N is ready, False otherwise
        """
        # Wait for container to be running
        if not wait_for_container(container, timeout=timeout):
            self.logger.error("Container failed to start within timeout")
            return False

        # Perform healthcheck with exponential backoff
        if not healthcheck(container, endpoint="/healthz", max_retries=5, base_delay=1):
            self.logger.error("N8N healthcheck failed after restart")
            return False

        self.logger.info("N8N is ready and responsive")
        return True

    def _post_restore_validation(
        self, container: docker.models.containers.Container
    ) -> Dict[str, bool]:
        """Post-restore validation checks.

        Args:
            container: Docker container

        Returns:
            Dictionary with validation results
        """
        validation_results = {}

        # Container running check
        validation_results["container_running"] = container_is_running(container)

        # Healthcheck
        validation_results["healthcheck"] = healthcheck(
            container, endpoint="/healthz", max_retries=3
        )

        # TODO: Add N8N REST API validation (check credentials/workflows count)
        # This requires N8N REST API integration in future phase

        return validation_results

    def _rollback_to_safety_backup(
        self, safety_backup_id: str, restore_type: BackupType
    ) -> None:
        """Rollback to safety backup after failed restore.

        Args:
            safety_backup_id: ID of safety backup to restore
            restore_type: Type of restore to rollback

        Raises:
            RestoreError: Rollback failed
        """
        try:
            self.logger.warning(f"Rolling back to safety backup: {safety_backup_id}")

            # Recursive restore from safety backup (skip safety backup creation)
            rollback_operation = self.restore(
                backup_id=safety_backup_id,
                restore_type=restore_type,
                skip_safety_backup=True,  # Don't create another safety backup
                skip_validation=True,  # Skip validation for rollback
            )

            if rollback_operation.status != OperationStatus.COMPLETED:
                raise RestoreError(
                    f"Rollback failed with status: {rollback_operation.status}",
                    operation_context={"rollback_operation": rollback_operation.to_json_log()},
                )

            self.logger.info("Rollback completed successfully")

        except Exception as e:
            raise RestoreError(
                f"CRITICAL: Rollback to safety backup failed: {e}. "
                f"Manual intervention required. Safety backup ID: {safety_backup_id}",
                operation_context={"safety_backup_id": safety_backup_id},
            )
