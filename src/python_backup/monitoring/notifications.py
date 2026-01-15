"""
Notification system with multiple recipients (phase9.4).

Supports multiple notification channels (Email, Slack, Webhook) with
separate recipients for success vs failure/alerts.
"""

from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from python_backup.monitoring.alerts import AlertTrigger, AlertSeverity


class NotificationType(str, Enum):
    """Notification type."""

    SUCCESS = "success"
    FAILURE = "failure"
    ALERT = "alert"


class NotificationPriority(str, Enum):
    """Notification priority level."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class NotificationRecipient:
    """
    Notification recipient configuration.

    Supports multiple contact methods and selective notification types.
    """

    name: str
    notification_types: List[NotificationType]
    email: Optional[str] = None
    slack_webhook: Optional[str] = None
    webhook_url: Optional[str] = None
    priority: NotificationPriority = NotificationPriority.NORMAL

    def should_receive(self, notification_type: NotificationType) -> bool:
        """
        Check if recipient should receive notification type.

        Args:
            notification_type: Type of notification

        Returns:
            True if recipient should receive this type
        """
        return notification_type in self.notification_types

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "notification_types": [t.value for t in self.notification_types],
            "email": self.email,
            "slack_webhook": self.slack_webhook,
            "webhook_url": self.webhook_url,
            "priority": self.priority.value,
        }


class NotificationChannel(ABC):
    """
    Abstract base class for notification channels.

    Subclasses implement specific delivery mechanisms (Email, Slack, etc.).
    """

    def __init__(self, name: str):
        """
        Initialize notification channel.

        Args:
            name: Channel name
        """
        self.name = name

    @abstractmethod
    def send(
        self,
        recipient: NotificationRecipient,
        notification_type: NotificationType,
        subject: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send notification.

        Args:
            recipient: Notification recipient
            notification_type: Type of notification
            subject: Notification subject
            body: Notification body
            metadata: Additional metadata

        Returns:
            True if sent successfully, False otherwise
        """
        pass

    @abstractmethod
    def format_message(
        self,
        notification_type: NotificationType,
        subject: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Format message for this channel.

        Args:
            notification_type: Type of notification
            subject: Message subject
            body: Message body
            metadata: Additional metadata

        Returns:
            Formatted message
        """
        pass


@dataclass
class EmailChannel(NotificationChannel):
    """
    Email notification channel.

    Sends notifications via SMTP.
    """

    name: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    from_address: str
    use_tls: bool = True

    def __post_init__(self):
        """Validate email channel configuration."""
        if not self.smtp_host:
            raise ValueError("SMTP host is required")
        if not self.from_address:
            raise ValueError("From address is required")

    def format_message(
        self,
        notification_type: NotificationType,
        subject: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Format email message."""
        lines = [
            f"Subject: {subject}",
            f"Type: {notification_type.value}",
            "",
            body,
        ]

        if metadata:
            lines.append("")
            lines.append("Details:")
            for key, value in metadata.items():
                lines.append(f"  {key}: {value}")

        return "\n".join(lines)

    def send(
        self,
        recipient: NotificationRecipient,
        notification_type: NotificationType,
        subject: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send email notification.

        Args:
            recipient: Recipient configuration
            notification_type: Type of notification
            subject: Email subject
            body: Email body
            metadata: Additional metadata

        Returns:
            True if sent successfully
        """
        if not recipient.email:
            return False

        # Format message
        message = self.format_message(notification_type, subject, body, metadata)

        # In real implementation, this would use smtplib to send email
        # For now, we'll just log the intent
        print(f"[EMAIL] Sending to {recipient.email}: {subject}")

        return True


@dataclass
class SlackChannel(NotificationChannel):
    """
    Slack notification channel.

    Sends notifications via Slack webhook.
    """

    name: str
    webhook_url: str

    def __post_init__(self):
        """Validate Slack channel configuration."""
        if not self.webhook_url:
            raise ValueError("Webhook URL is required")
        if not self.webhook_url.startswith("https://hooks.slack.com"):
            raise ValueError("Invalid Slack webhook URL")

    def format_payload(
        self,
        notification_type: NotificationType,
        subject: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Format Slack message payload.

        Args:
            notification_type: Type of notification
            subject: Message subject
            body: Message body
            metadata: Additional metadata

        Returns:
            Slack webhook payload
        """
        # Choose color based on notification type
        color_map = {
            NotificationType.SUCCESS: "good",
            NotificationType.FAILURE: "danger",
            NotificationType.ALERT: "warning",
        }
        color = color_map.get(notification_type, "good")

        # Build fields
        fields = []
        if metadata:
            for key, value in metadata.items():
                fields.append({"title": key, "value": str(value), "short": True})

        payload = {
            "text": subject,
            "attachments": [
                {
                    "color": color,
                    "text": body,
                    "fields": fields,
                    "footer": "Vya BackupDB",
                    "ts": int(datetime.now().timestamp()),
                }
            ],
        }

        return payload

    def send(
        self,
        recipient: NotificationRecipient,
        notification_type: NotificationType,
        subject: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send Slack notification.

        Args:
            recipient: Recipient configuration
            notification_type: Type of notification
            subject: Message subject
            body: Message body
            metadata: Additional metadata

        Returns:
            True if sent successfully
        """
        if not recipient.slack_webhook:
            return False

        # Format payload
        payload = self.format_payload(notification_type, subject, body, metadata)

        # In real implementation, this would use requests to POST to webhook
        # For now, we'll just log the intent
        print(f"[SLACK] Sending to {recipient.slack_webhook}: {subject}")

        return True

    def format_message(
        self,
        notification_type: NotificationType,
        subject: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Format Slack message (returns JSON string)."""
        import json

        payload = self.format_payload(notification_type, subject, body, metadata)
        return json.dumps(payload)


@dataclass
class WebhookChannel(NotificationChannel):
    """
    Generic webhook notification channel.

    Sends JSON payloads to custom webhook endpoints.
    """

    name: str
    url: str
    headers: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        """Validate webhook channel configuration."""
        if not self.url:
            raise ValueError("Webhook URL is required")

    def format_payload(
        self,
        notification_type: NotificationType,
        subject: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Format webhook payload.

        Args:
            notification_type: Type of notification
            subject: Message subject
            body: Message body
            metadata: Additional metadata

        Returns:
            Webhook payload
        """
        payload = {
            "type": notification_type.value,
            "subject": subject,
            "body": body,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        return payload

    def send(
        self,
        recipient: NotificationRecipient,
        notification_type: NotificationType,
        subject: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send webhook notification.

        Args:
            recipient: Recipient configuration
            notification_type: Type of notification
            subject: Message subject
            body: Message body
            metadata: Additional metadata

        Returns:
            True if sent successfully
        """
        if not recipient.webhook_url:
            return False

        # Format payload
        payload = self.format_payload(notification_type, subject, body, metadata)

        # In real implementation, this would use requests to POST to webhook
        # For now, we'll just log the intent
        print(f"[WEBHOOK] Sending to {recipient.webhook_url}: {subject}")

        return True

    def format_message(
        self,
        notification_type: NotificationType,
        subject: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Format webhook message (returns JSON string)."""
        import json

        payload = self.format_payload(notification_type, subject, body, metadata)
        return json.dumps(payload)


class NotificationManager:
    """
    Manage notification recipients and channels.

    Responsibilities:
    - Store and manage recipients
    - Route notifications to correct recipients based on type
    - Support multiple notification channels
    - Handle notification priorities
    """

    def __init__(self):
        """Initialize notification manager."""
        self._recipients: Dict[str, NotificationRecipient] = {}
        self._channels: Dict[str, NotificationChannel] = {}

    def add_recipient(self, recipient: NotificationRecipient) -> None:
        """
        Add notification recipient.

        Args:
            recipient: Recipient configuration
        """
        self._recipients[recipient.name] = recipient

    def remove_recipient(self, name: str) -> None:
        """
        Remove notification recipient.

        Args:
            name: Recipient name
        """
        if name in self._recipients:
            del self._recipients[name]

    def get_recipient(self, name: str) -> Optional[NotificationRecipient]:
        """
        Get recipient by name.

        Args:
            name: Recipient name

        Returns:
            Recipient if found, None otherwise
        """
        return self._recipients.get(name)

    def get_recipients(self) -> List[NotificationRecipient]:
        """Get all recipients."""
        return list(self._recipients.values())

    def get_recipients_by_type(
        self, notification_type: NotificationType
    ) -> List[NotificationRecipient]:
        """
        Get recipients for specific notification type.

        Args:
            notification_type: Type of notification

        Returns:
            List of recipients that should receive this type
        """
        return [
            recipient
            for recipient in self._recipients.values()
            if recipient.should_receive(notification_type)
        ]

    def add_channel(self, channel: NotificationChannel) -> None:
        """
        Add notification channel.

        Args:
            channel: Notification channel
        """
        self._channels[channel.name] = channel

    def remove_channel(self, name: str) -> None:
        """
        Remove notification channel.

        Args:
            name: Channel name
        """
        if name in self._channels:
            del self._channels[name]

    def get_channel(self, name: str) -> Optional[NotificationChannel]:
        """
        Get channel by name.

        Args:
            name: Channel name

        Returns:
            Channel if found, None otherwise
        """
        return self._channels.get(name)

    def get_channels(self) -> List[NotificationChannel]:
        """Get all channels."""
        return list(self._channels.values())

    def send_notification(
        self,
        notification_type: NotificationType,
        subject: str,
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Send notification to all appropriate recipients.

        Args:
            notification_type: Type of notification
            subject: Notification subject
            body: Notification body
            metadata: Additional metadata

        Returns:
            List of recipient names that received notification
        """
        recipients = self.get_recipients_by_type(notification_type)
        sent_to = []

        for recipient in recipients:
            # Try each channel type
            sent = False

            # Email
            if recipient.email and "email" in self._channels:
                channel = self._channels["email"]
                if channel.send(recipient, notification_type, subject, body, metadata):
                    sent = True

            # Slack
            if recipient.slack_webhook and "slack" in self._channels:
                channel = self._channels["slack"]
                if channel.send(recipient, notification_type, subject, body, metadata):
                    sent = True

            # Webhook
            if recipient.webhook_url and "webhook" in self._channels:
                channel = self._channels["webhook"]
                if channel.send(recipient, notification_type, subject, body, metadata):
                    sent = True

            if sent:
                sent_to.append(recipient.name)

        return sent_to

    def send_alert_notification(self, alert_trigger: AlertTrigger) -> List[str]:
        """
        Send notification for alert trigger.

        Args:
            alert_trigger: Alert trigger event

        Returns:
            List of recipient names that received notification
        """
        # Map alert severity to notification type
        notification_type = NotificationType.ALERT

        subject = f"Alert: {alert_trigger.rule_name}"
        body = alert_trigger.message

        metadata = {
            "severity": alert_trigger.severity.value,
            "instance": alert_trigger.instance_name,
            "database": alert_trigger.database_name or "N/A",
            "timestamp": alert_trigger.timestamp.isoformat(),
            "metric_value": str(alert_trigger.metric_value),
        }

        return self.send_notification(notification_type, subject, body, metadata)
