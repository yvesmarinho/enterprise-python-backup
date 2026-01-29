"""Pydantic models for N8N backup and restore operations."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class OperationStatus(str, Enum):
    """Status of backup/restore operations."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class OperationType(str, Enum):
    """Type of data being backed up or restored."""

    CREDENTIALS = "credentials"
    WORKFLOWS = "workflows"
    BOTH = "both"


class N8NCredential(BaseModel):
    """Model for N8N credential export/import.

    Represents a single N8N credential with encrypted data.
    Follows N8N CLI export schema.
    """

    id: UUID = Field(..., description="Unique credential ID (preserved with --backup flag)")
    name: str = Field(..., min_length=1, description="Credential name")
    type: str = Field(..., description="Credential type (e.g., 'httpBasicAuth', 'awsS3')")
    data: Dict[str, Any] = Field(
        ..., description="Encrypted credential data (base64 AES-256-CBC)"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "AWS Production",
                "type": "awsS3",
                "data": {"encrypted": "base64_encrypted_data_here"},
                "createdAt": "2026-01-20T10:00:00Z",
                "updatedAt": "2026-01-20T10:00:00Z",
            }
        }


class N8NWorkflow(BaseModel):
    """Model for N8N workflow export/import.

    Represents a complete N8N workflow with nodes and connections.
    Follows N8N CLI export schema.
    """

    id: UUID = Field(..., description="Unique workflow ID (preserved with --backup flag)")
    name: str = Field(..., min_length=1, description="Workflow name")
    active: bool = Field(default=False, description="Whether workflow is active")
    nodes: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of workflow nodes"
    )
    connections: Dict[str, Any] = Field(
        default_factory=dict, description="Node connections mapping"
    )
    settings: Optional[Dict[str, Any]] = Field(
        default=None, description="Workflow settings"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")

    class Config:
        """Pydantic model configuration."""

        populate_by_name = True
        json_schema_extra = {
            "example": {
                "id": "223e4567-e89b-12d3-a456-426614174001",
                "name": "Data Sync Workflow",
                "active": True,
                "nodes": [
                    {"id": "node-1", "type": "trigger", "parameters": {}},
                    {"id": "node-2", "type": "httpRequest", "parameters": {}},
                ],
                "connections": {"node-1": {"main": [[{"node": "node-2"}]]}},
                "createdAt": "2026-01-20T10:00:00Z",
                "updatedAt": "2026-01-20T10:00:00Z",
            }
        }


class BackupOperation(BaseModel):
    """Model for tracking backup operations.

    Used for audit trail, logging, and operation history.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique operation ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Operation start time")
    hostname: str = Field(..., description="Server hostname where backup was created")
    operation_type: OperationType = Field(..., description="Type of data backed up")
    status: OperationStatus = Field(
        default=OperationStatus.PENDING, description="Current operation status"
    )
    files_created: List[str] = Field(
        default_factory=list, description="List of backup file paths created"
    )
    duration_seconds: Optional[float] = Field(
        default=None, description="Operation duration in seconds"
    )
    checksum_sha256: Optional[Dict[str, str]] = Field(
        default=None, description="SHA256 checksums for each file {filename: checksum}"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if operation failed"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata (e.g., N8N version, container ID)"
    )

    @field_validator("files_created")
    @classmethod
    def validate_files_list(cls, v: List[str]) -> List[str]:
        """Ensure files list contains valid paths."""
        return [f for f in v if f and isinstance(f, str)]

    def to_json_log(self) -> Dict[str, Any]:
        """Convert to structured JSON log format."""
        return {
            "event": "backup_operation",
            "operation_id": str(self.id),
            "timestamp": self.timestamp.isoformat(),
            "hostname": self.hostname,
            "type": self.operation_type.value,
            "status": self.status.value,
            "files_count": len(self.files_created),
            "duration": self.duration_seconds,
            "has_checksums": bool(self.checksum_sha256),
            "error": self.error_message,
            "metadata": self.metadata,
        }

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "323e4567-e89b-12d3-a456-426614174002",
                "timestamp": "2026-01-20T14:00:00Z",
                "hostname": "prod-server-01",
                "operation_type": "both",
                "status": "completed",
                "files_created": [
                    "/tmp/bkpfile/20260120-140000-prod-credentials/cred_001.json",
                    "/tmp/bkpfile/20260120-140000-prod-workflows/workflow_001.json",
                ],
                "duration_seconds": 45.3,
                "checksum_sha256": {
                    "cred_001.json": "abc123...",
                    "workflow_001.json": "def456...",
                },
            }
        }


class RestoreOperation(BaseModel):
    """Model for tracking restore operations.

    Used for audit trail, logging, and operation history.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique operation ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Operation start time")
    backup_source: str = Field(..., description="Path or ID of backup being restored")
    operation_type: OperationType = Field(..., description="Type of data being restored")
    status: OperationStatus = Field(
        default=OperationStatus.PENDING, description="Current operation status"
    )
    files_processed: List[str] = Field(
        default_factory=list, description="List of files processed during restore"
    )
    pre_restore_backup_path: Optional[str] = Field(
        default=None, description="Path to safety backup created before restore"
    )
    validations: Dict[str, bool] = Field(
        default_factory=dict,
        description="Validation checks performed {check_name: passed}",
    )
    duration_seconds: Optional[float] = Field(
        default=None, description="Operation duration in seconds"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if operation failed"
    )
    rolled_back: bool = Field(
        default=False, description="Whether operation was rolled back due to failure"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata (e.g., N8N version, container ID)"
    )

    def to_json_log(self) -> Dict[str, Any]:
        """Convert to structured JSON log format."""
        return {
            "event": "restore_operation",
            "operation_id": str(self.id),
            "timestamp": self.timestamp.isoformat(),
            "backup_source": self.backup_source,
            "type": self.operation_type.value,
            "status": self.status.value,
            "files_count": len(self.files_processed),
            "validations_passed": sum(1 for v in self.validations.values() if v),
            "validations_total": len(self.validations),
            "duration": self.duration_seconds,
            "rolled_back": self.rolled_back,
            "error": self.error_message,
            "metadata": self.metadata,
        }

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "example": {
                "id": "423e4567-e89b-12d3-a456-426614174003",
                "timestamp": "2026-01-20T15:00:00Z",
                "backup_source": "/tmp/bkpfile/20260120-140000-prod-n8n-credentials",
                "operation_type": "credentials",
                "status": "completed",
                "files_processed": ["cred_001.json", "cred_002.json"],
                "pre_restore_backup_path": "/tmp/bkpfile/20260120-150000-prod-n8n-safety-backup",
                "validations": {
                    "json_valid": True,
                    "encryption_key_match": True,
                    "container_running": True,
                },
                "duration_seconds": 120.5,
            }
        }
