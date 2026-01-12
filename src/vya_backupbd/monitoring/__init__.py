"""
Monitoring module for Phase 9.

Exports:
- MetricsCollector: Collect and export Prometheus metrics (phase9.2)
- AlertManager: Alert rules and evaluation (phase9.3)
- NotificationManager: Multi-recipient notification system (phase9.4)
"""

from vya_backupbd.monitoring.metrics import (
    MetricsCollector,
    BackupMetrics,
    RestoreMetrics,
    ScheduleMetrics,
    StorageMetrics,
    MetricType,
)
from vya_backupbd.monitoring.alerts import (
    AlertManager,
    AlertRule,
    AlertCondition,
    AlertSeverity,
    AlertTrigger,
    ThresholdType,
)
from vya_backupbd.monitoring.notifications import (
    NotificationManager,
    NotificationRecipient,
    NotificationChannel,
    EmailChannel,
    SlackChannel,
    WebhookChannel,
    NotificationType,
    NotificationPriority,
)

__all__ = [
    # Metrics (phase9.2)
    "MetricsCollector",
    "BackupMetrics",
    "RestoreMetrics",
    "ScheduleMetrics",
    "StorageMetrics",
    "MetricType",
    # Alerts (phase9.3)
    "AlertManager",
    "AlertRule",
    "AlertCondition",
    "AlertSeverity",
    "AlertTrigger",
    "ThresholdType",
    # Notifications (phase9.4)
    "NotificationManager",
    "NotificationRecipient",
    "NotificationChannel",
    "EmailChannel",
    "SlackChannel",
    "WebhookChannel",
    "NotificationType",
    "NotificationPriority",
]
