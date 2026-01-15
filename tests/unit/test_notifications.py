"""
Unit tests for notification system (phase9.4).

Tests notification channels with multiple recipients for success vs failure/alerts.
"""

from datetime import datetime
from typing import Dict, Any
import pytest
from python_backup.monitoring.notifications import (
    NotificationChannel,
    EmailChannel,
    SlackChannel,
    WebhookChannel,
    NotificationManager,
    NotificationRecipient,
    NotificationPriority,
    NotificationType,
)
from python_backup.monitoring.alerts import AlertTrigger, AlertSeverity


class TestNotificationRecipient:
    """Test notification recipient model."""

    def test_create_email_recipient(self):
        """Test creating email recipient."""
        recipient = NotificationRecipient(
            name="Operations Team",
            email="ops@example.com",
            notification_types=[NotificationType.FAILURE, NotificationType.ALERT],
        )

        assert recipient.name == "Operations Team"
        assert recipient.email == "ops@example.com"
        assert NotificationType.FAILURE in recipient.notification_types
        assert NotificationType.SUCCESS not in recipient.notification_types

    def test_create_slack_recipient(self):
        """Test creating Slack recipient."""
        recipient = NotificationRecipient(
            name="Success Channel",
            slack_webhook="https://hooks.slack.com/services/XXX",
            notification_types=[NotificationType.SUCCESS],
        )

        assert recipient.slack_webhook is not None
        assert NotificationType.SUCCESS in recipient.notification_types

    def test_recipient_for_all_types(self):
        """Test recipient receiving all notification types."""
        recipient = NotificationRecipient(
            name="Admin",
            email="admin@example.com",
            notification_types=[
                NotificationType.SUCCESS,
                NotificationType.FAILURE,
                NotificationType.ALERT,
            ],
        )

        assert len(recipient.notification_types) == 3

    def test_recipient_should_receive(self):
        """Test if recipient should receive notification type."""
        recipient = NotificationRecipient(
            name="Failures Only",
            email="alerts@example.com",
            notification_types=[NotificationType.FAILURE, NotificationType.ALERT],
        )

        assert recipient.should_receive(NotificationType.FAILURE) is True
        assert recipient.should_receive(NotificationType.ALERT) is True
        assert recipient.should_receive(NotificationType.SUCCESS) is False


class TestEmailChannel:
    """Test email notification channel."""

    def test_create_email_channel(self):
        """Test creating email channel."""
        channel = EmailChannel(
            name="email",
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@example.com",
            smtp_password="password",
            from_address="noreply@example.com",
            use_tls=True,
        )

        assert channel.name == "email"
        assert channel.smtp_host == "smtp.gmail.com"
        assert channel.smtp_port == 587
        assert channel.use_tls is True

    def test_email_channel_validation(self):
        """Test email channel requires SMTP settings."""
        with pytest.raises(ValueError):
            EmailChannel(
                name="email",
                smtp_host="",
                smtp_port=587,
                smtp_user="user",
                smtp_password="password",
                from_address="noreply@example.com",
            )

    def test_format_success_message(self):
        """Test formatting success notification."""
        channel = EmailChannel(
            name="email",
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@example.com",
            smtp_password="password",
            from_address="noreply@example.com",
        )

        message = channel.format_message(
            notification_type=NotificationType.SUCCESS,
            subject="Backup Successful",
            body="Backup completed for database mydb",
            metadata={
                "instance": "prod-mysql-01",
                "database": "mydb",
                "duration": "120s",
            },
        )

        assert "Backup Successful" in message
        assert "mydb" in message

    def test_format_failure_message(self):
        """Test formatting failure notification."""
        channel = EmailChannel(
            name="email",
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@example.com",
            smtp_password="password",
            from_address="noreply@example.com",
        )

        message = channel.format_message(
            notification_type=NotificationType.FAILURE,
            subject="Backup Failed",
            body="Backup failed for database mydb: Connection timeout",
            metadata={
                "instance": "prod-mysql-01",
                "database": "mydb",
                "error": "Connection timeout",
            },
        )

        assert "Backup Failed" in message
        assert "Connection timeout" in message


class TestSlackChannel:
    """Test Slack notification channel."""

    def test_create_slack_channel(self):
        """Test creating Slack channel."""
        channel = SlackChannel(
            name="slack",
            webhook_url="https://hooks.slack.com/services/XXX/YYY/ZZZ",
        )

        assert channel.name == "slack"
        assert channel.webhook_url.startswith("https://hooks.slack.com")

    def test_slack_channel_validation(self):
        """Test Slack channel requires webhook URL."""
        with pytest.raises(ValueError):
            SlackChannel(
                name="slack",
                webhook_url="",
            )

    def test_format_slack_success_payload(self):
        """Test formatting Slack success notification."""
        channel = SlackChannel(
            name="slack",
            webhook_url="https://hooks.slack.com/services/XXX",
        )

        payload = channel.format_payload(
            notification_type=NotificationType.SUCCESS,
            subject="Backup Successful",
            body="Backup completed for database mydb",
            metadata={
                "instance": "prod-mysql-01",
                "database": "mydb",
                "duration": "120s",
                "size": "500MB",
            },
        )

        assert payload["text"] or payload.get("blocks")
        assert "Backup Successful" in str(payload)

    def test_format_slack_alert_payload(self):
        """Test formatting Slack alert notification."""
        channel = SlackChannel(
            name="slack",
            webhook_url="https://hooks.slack.com/services/XXX",
        )

        payload = channel.format_payload(
            notification_type=NotificationType.ALERT,
            subject="Alert: Backup Duration Warning",
            body="Backup took longer than expected",
            metadata={
                "severity": "warning",
                "threshold": "300s",
                "actual": "350s",
            },
        )

        assert "warning" in str(payload).lower() or "alert" in str(payload).lower()


class TestWebhookChannel:
    """Test webhook notification channel."""

    def test_create_webhook_channel(self):
        """Test creating webhook channel."""
        channel = WebhookChannel(
            name="webhook",
            url="https://api.example.com/webhooks/backup-notifications",
            headers={"Authorization": "Bearer token123"},
        )

        assert channel.name == "webhook"
        assert channel.url.startswith("https://")
        assert "Authorization" in channel.headers

    def test_webhook_channel_validation(self):
        """Test webhook channel requires URL."""
        with pytest.raises(ValueError):
            WebhookChannel(
                name="webhook",
                url="",
            )

    def test_format_webhook_payload(self):
        """Test formatting webhook payload."""
        channel = WebhookChannel(
            name="webhook",
            url="https://api.example.com/webhooks/notifications",
        )

        payload = channel.format_payload(
            notification_type=NotificationType.FAILURE,
            subject="Backup Failed",
            body="Backup failed for database mydb",
            metadata={
                "instance": "prod-mysql-01",
                "database": "mydb",
                "error": "Connection timeout",
                "timestamp": datetime.now().isoformat(),
            },
        )

        assert payload["type"] == NotificationType.FAILURE
        assert payload["subject"] == "Backup Failed"
        assert "metadata" in payload
        assert payload["metadata"]["instance"] == "prod-mysql-01"


class TestNotificationManager:
    """Test notification manager."""

    @pytest.fixture
    def manager(self):
        """Create notification manager."""
        return NotificationManager()

    def test_add_recipient(self, manager):
        """Test adding recipient."""
        recipient = NotificationRecipient(
            name="Ops Team",
            email="ops@example.com",
            notification_types=[NotificationType.FAILURE, NotificationType.ALERT],
        )

        manager.add_recipient(recipient)
        assert len(manager.get_recipients()) == 1

    def test_add_multiple_recipients(self, manager):
        """Test adding multiple recipients with different types."""
        # Success recipient
        success_recipient = NotificationRecipient(
            name="Success Channel",
            slack_webhook="https://hooks.slack.com/success",
            notification_types=[NotificationType.SUCCESS],
        )

        # Failure/alert recipient
        failure_recipient = NotificationRecipient(
            name="Alerts Team",
            email="alerts@example.com",
            notification_types=[NotificationType.FAILURE, NotificationType.ALERT],
        )

        manager.add_recipient(success_recipient)
        manager.add_recipient(failure_recipient)

        assert len(manager.get_recipients()) == 2

    def test_get_recipients_by_type(self, manager):
        """Test getting recipients by notification type."""
        # Add success-only recipient
        manager.add_recipient(
            NotificationRecipient(
                name="Success Channel",
                email="success@example.com",
                notification_types=[NotificationType.SUCCESS],
            )
        )

        # Add failure-only recipient
        manager.add_recipient(
            NotificationRecipient(
                name="Alerts Team",
                email="alerts@example.com",
                notification_types=[NotificationType.FAILURE, NotificationType.ALERT],
            )
        )

        success_recipients = manager.get_recipients_by_type(NotificationType.SUCCESS)
        assert len(success_recipients) == 1
        assert success_recipients[0].name == "Success Channel"

        failure_recipients = manager.get_recipients_by_type(NotificationType.FAILURE)
        assert len(failure_recipients) == 1
        assert failure_recipients[0].name == "Alerts Team"

    def test_add_channel(self, manager):
        """Test adding notification channel."""
        channel = EmailChannel(
            name="email",
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@example.com",
            smtp_password="password",
            from_address="noreply@example.com",
        )

        manager.add_channel(channel)
        assert len(manager.get_channels()) == 1

    def test_send_success_notification(self, manager):
        """Test sending success notification to correct recipients."""
        # Add success recipient
        success_recipient = NotificationRecipient(
            name="Success Channel",
            email="success@example.com",
            notification_types=[NotificationType.SUCCESS],
        )
        manager.add_recipient(success_recipient)

        # Add failure recipient (should not receive success notifications)
        failure_recipient = NotificationRecipient(
            name="Alerts",
            email="alerts@example.com",
            notification_types=[NotificationType.FAILURE],
        )
        manager.add_recipient(failure_recipient)

        # Get recipients for success notification
        recipients = manager.get_recipients_by_type(NotificationType.SUCCESS)
        assert len(recipients) == 1
        assert recipients[0].name == "Success Channel"

    def test_send_failure_notification(self, manager):
        """Test sending failure notification to correct recipients."""
        # Add success recipient (should not receive failures)
        success_recipient = NotificationRecipient(
            name="Success Channel",
            email="success@example.com",
            notification_types=[NotificationType.SUCCESS],
        )
        manager.add_recipient(success_recipient)

        # Add failure recipient
        failure_recipient = NotificationRecipient(
            name="Alerts",
            email="alerts@example.com",
            notification_types=[NotificationType.FAILURE, NotificationType.ALERT],
        )
        manager.add_recipient(failure_recipient)

        # Get recipients for failure notification
        recipients = manager.get_recipients_by_type(NotificationType.FAILURE)
        assert len(recipients) == 1
        assert recipients[0].name == "Alerts"

    def test_send_alert_notification(self, manager):
        """Test sending alert notification."""
        # Add alert recipient
        alert_recipient = NotificationRecipient(
            name="Alert Channel",
            email="alerts@example.com",
            notification_types=[NotificationType.ALERT],
        )
        manager.add_recipient(alert_recipient)

        # Create alert trigger
        trigger = AlertTrigger(
            rule_name="backup_duration_warning",
            severity=AlertSeverity.WARNING,
            message="Backup duration exceeded threshold",
            timestamp=datetime.now(),
            metric_value=350.0,
            instance_name="prod-mysql-01",
            database_name="mydb",
        )

        # Get recipients for alert
        recipients = manager.get_recipients_by_type(NotificationType.ALERT)
        assert len(recipients) == 1

    def test_notification_priority(self, manager):
        """Test notification priority levels."""
        # Critical failure should have high priority
        critical_recipient = NotificationRecipient(
            name="Critical Alerts",
            email="critical@example.com",
            notification_types=[NotificationType.FAILURE],
            priority=NotificationPriority.HIGH,
        )

        # Success should have low priority
        success_recipient = NotificationRecipient(
            name="Success",
            email="success@example.com",
            notification_types=[NotificationType.SUCCESS],
            priority=NotificationPriority.LOW,
        )

        manager.add_recipient(critical_recipient)
        manager.add_recipient(success_recipient)

        recipients = manager.get_recipients()
        assert any(r.priority == NotificationPriority.HIGH for r in recipients)
        assert any(r.priority == NotificationPriority.LOW for r in recipients)

    def test_remove_recipient(self, manager):
        """Test removing recipient."""
        recipient = NotificationRecipient(
            name="Test",
            email="test@example.com",
            notification_types=[NotificationType.SUCCESS],
        )

        manager.add_recipient(recipient)
        assert len(manager.get_recipients()) == 1

        manager.remove_recipient("Test")
        assert len(manager.get_recipients()) == 0

    def test_notification_with_multiple_channels(self, manager):
        """Test notification through multiple channels."""
        # Add email channel
        email_channel = EmailChannel(
            name="email",
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            smtp_user="noreply@example.com",
            smtp_password="password",
            from_address="noreply@example.com",
        )
        manager.add_channel(email_channel)

        # Add Slack channel
        slack_channel = SlackChannel(
            name="slack",
            webhook_url="https://hooks.slack.com/services/XXX",
        )
        manager.add_channel(slack_channel)

        assert len(manager.get_channels()) == 2
