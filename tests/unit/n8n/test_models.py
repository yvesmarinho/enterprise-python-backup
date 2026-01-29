"""Unit tests for N8N Pydantic models."""

import pytest
from datetime import datetime
from uuid import uuid4, UUID
from pydantic import ValidationError

from enterprise_backup.n8n.models import (
    OperationStatus,
    BackupType,
    N8NCredential,
    N8NWorkflow,
    BackupOperation,
    RestoreOperation,
    BackupMetadata,
)


class TestEnums:
    """Test enum types."""

    def test_operation_status_values(self):
        """Test OperationStatus enum values."""
        assert OperationStatus.PENDING.value == "pending"
        assert OperationStatus.IN_PROGRESS.value == "in_progress"
        assert OperationStatus.COMPLETED.value == "completed"
        assert OperationStatus.FAILED.value == "failed"
        assert OperationStatus.ROLLED_BACK.value == "rolled_back"

    def test_backup_type_values(self):
        """Test BackupType enum values."""
        assert BackupType.CREDENTIALS.value == "credentials"
        assert BackupType.WORKFLOWS.value == "workflows"
        assert BackupType.FULL.value == "full"


class TestN8NCredential:
    """Test N8NCredential model."""

    def test_valid_credential(self):
        """Test creating valid credential."""
        credential = N8NCredential(
            id=uuid4(),
            name="Test Credential",
            type="oauth2Api",
            data='{"encrypted": "data"}',
        )

        assert isinstance(credential.id, UUID)
        assert credential.name == "Test Credential"
        assert credential.type == "oauth2Api"
        assert credential.data == '{"encrypted": "data"}'
        assert isinstance(credential.created_at, datetime)
        assert isinstance(credential.updated_at, datetime)

    def test_credential_missing_required_fields(self):
        """Test credential validation with missing fields."""
        with pytest.raises(ValidationError) as exc_info:
            N8NCredential(
                id=uuid4(),
                name="Test",
                # Missing 'type' and 'data'
            )

        errors = exc_info.value.errors()
        assert len(errors) == 2
        assert any(e["loc"] == ("type",) for e in errors)
        assert any(e["loc"] == ("data",) for e in errors)


class TestN8NWorkflow:
    """Test N8NWorkflow model."""

    def test_valid_workflow(self):
        """Test creating valid workflow."""
        workflow = N8NWorkflow(
            id=uuid4(),
            name="Test Workflow",
            active=True,
            nodes=[{"name": "Start", "type": "n8n-nodes-base.start"}],
            connections={"Start": {"main": [[{"node": "HTTP Request", "type": "main", "index": 0}]]}},
        )

        assert isinstance(workflow.id, UUID)
        assert workflow.name == "Test Workflow"
        assert workflow.active is True
        assert len(workflow.nodes) == 1
        assert "Start" in workflow.connections

    def test_workflow_defaults(self):
        """Test workflow default values."""
        workflow = N8NWorkflow(
            id=uuid4(),
            name="Test",
            nodes=[],
            connections={},
        )

        assert workflow.active is False
        assert workflow.settings == {}


class TestBackupOperation:
    """Test BackupOperation model."""

    def test_valid_backup_operation(self):
        """Test creating valid backup operation."""
        operation = BackupOperation(
            id=str(uuid4()),
            timestamp=datetime.utcnow(),
            hostname="server01",
            type=BackupType.FULL,
            status=OperationStatus.COMPLETED,
            files=["credentials.json", "workflows.json"],
            duration_seconds=15.5,
            checksum_sha256="abc123def456",
        )

        assert operation.hostname == "server01"
        assert operation.type == BackupType.FULL
        assert operation.status == OperationStatus.COMPLETED
        assert len(operation.files) == 2
        assert operation.duration_seconds == 15.5

    def test_backup_operation_to_json_log(self):
        """Test to_json_log() serialization."""
        operation = BackupOperation(
            id=str(uuid4()),
            timestamp=datetime.utcnow(),
            hostname="server01",
            type=BackupType.CREDENTIALS,
            status=OperationStatus.COMPLETED,
            files=["credentials.json"],
            duration_seconds=10.0,
            checksum_sha256="abc123",
        )

        log_dict = operation.to_json_log()

        assert log_dict["operation_type"] == "backup"
        assert log_dict["hostname"] == "server01"
        assert log_dict["backup_type"] == "credentials"
        assert log_dict["status"] == "completed"
        assert log_dict["duration_seconds"] == 10.0


class TestRestoreOperation:
    """Test RestoreOperation model."""

    def test_valid_restore_operation(self):
        """Test creating valid restore operation."""
        operation = RestoreOperation(
            id=str(uuid4()),
            timestamp=datetime.utcnow(),
            backup_source="backup-123",
            type=BackupType.FULL,
            status=OperationStatus.COMPLETED,
            files_processed=["credentials.json", "workflows.json"],
            validations={"integrity": True, "compatibility": True},
            duration_seconds=25.3,
        )

        assert operation.backup_source == "backup-123"
        assert operation.type == BackupType.FULL
        assert len(operation.files_processed) == 2
        assert operation.validations["integrity"] is True

    def test_restore_operation_with_safety_backup(self):
        """Test restore operation with safety backup."""
        operation = RestoreOperation(
            id=str(uuid4()),
            timestamp=datetime.utcnow(),
            backup_source="backup-123",
            type=BackupType.FULL,
            status=OperationStatus.COMPLETED,
            files_processed=["credentials.json"],
            pre_restore_backup="safety-backup-456",
            validations={},
            duration_seconds=30.0,
        )

        assert operation.pre_restore_backup == "safety-backup-456"


class TestBackupMetadata:
    """Test BackupMetadata model."""

    def test_valid_metadata(self):
        """Test creating valid backup metadata."""
        metadata = BackupMetadata(
            backup_id=uuid4(),
            created_at=datetime.utcnow(),
            hostname="server01",
            type=BackupType.FULL,
            file_count=2,
            total_size_bytes=1024000,
            checksum_sha256="abc123def456",
            encryption_key_hash="key_hash_123",
            n8n_version="1.0.0",
        )

        assert metadata.file_count == 2
        assert metadata.total_size_bytes == 1024000
        assert metadata.n8n_version == "1.0.0"

    def test_metadata_required_fields(self):
        """Test metadata validation."""
        with pytest.raises(ValidationError) as exc_info:
            BackupMetadata(
                backup_id=uuid4(),
                # Missing required fields
            )

        errors = exc_info.value.errors()
        assert len(errors) > 0
