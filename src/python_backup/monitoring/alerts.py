"""
Alert configuration system (phase9.3).

Defines alert rules, conditions, and evaluates metrics against thresholds.
"""

from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field

from python_backup.monitoring.metrics import (
    BackupMetrics,
    RestoreMetrics,
    ScheduleMetrics,
    StorageMetrics,
)


class ThresholdType(str, Enum):
    """Threshold comparison type."""

    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_OR_EQUAL = "ge"
    LESS_OR_EQUAL = "le"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AlertCondition:
    """
    Alert condition definition.

    Defines a threshold-based condition for triggering alerts.
    """

    metric_name: str
    threshold_type: ThresholdType
    threshold_value: Union[float, int, bool, str]

    def evaluate(self, value: Union[float, int, bool, str]) -> bool:
        """
        Evaluate condition against a value.

        Args:
            value: Value to evaluate

        Returns:
            True if condition is met, False otherwise
        """
        if self.threshold_type == ThresholdType.GREATER_THAN:
            return value > self.threshold_value
        elif self.threshold_type == ThresholdType.LESS_THAN:
            return value < self.threshold_value
        elif self.threshold_type == ThresholdType.EQUALS:
            return value == self.threshold_value
        elif self.threshold_type == ThresholdType.NOT_EQUALS:
            return value != self.threshold_value
        elif self.threshold_type == ThresholdType.GREATER_OR_EQUAL:
            return value >= self.threshold_value
        elif self.threshold_type == ThresholdType.LESS_OR_EQUAL:
            return value <= self.threshold_value
        return False


@dataclass
class AlertRule:
    """
    Alert rule definition.

    Defines when and how to trigger alerts based on metric conditions.
    """

    name: str
    description: str
    severity: AlertSeverity
    condition: AlertCondition
    enabled: bool = True
    additional_conditions: List[AlertCondition] = field(default_factory=list)
    cooldown_seconds: int = 300  # 5 minutes default cooldown

    def evaluate_all_conditions(self, metric_data: Dict[str, Any]) -> bool:
        """
        Evaluate all conditions (primary + additional).

        Args:
            metric_data: Dictionary of metric values

        Returns:
            True if all conditions are met
        """
        if not self.enabled:
            return False

        # Evaluate primary condition
        if self.condition.metric_name not in metric_data:
            return False

        if not self.condition.evaluate(metric_data[self.condition.metric_name]):
            return False

        # Evaluate additional conditions (AND logic)
        for condition in self.additional_conditions:
            if condition.metric_name not in metric_data:
                return False
            if not condition.evaluate(metric_data[condition.metric_name]):
                return False

        return True


@dataclass
class AlertTrigger:
    """
    Alert trigger event.

    Represents an alert that was triggered by a rule.
    """

    rule_name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    metric_value: Any
    instance_name: str
    database_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_name": self.rule_name,
            "severity": self.severity,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "metric_value": self.metric_value,
            "instance_name": self.instance_name,
            "database_name": self.database_name,
            "metadata": self.metadata,
        }


class AlertManager:
    """
    Manage alert rules and evaluate metrics.

    Responsibilities:
    - Store and manage alert rules
    - Evaluate metrics against rules
    - Generate alert triggers
    - Track alert history
    """

    def __init__(self):
        """Initialize alert manager."""
        self._rules: Dict[str, AlertRule] = {}
        self._triggers_history: List[AlertTrigger] = []
        self._last_trigger_time: Dict[str, datetime] = {}

    def add_rule(self, rule: AlertRule) -> None:
        """
        Add alert rule.

        Args:
            rule: Alert rule to add
        """
        self._rules[rule.name] = rule

    def remove_rule(self, rule_name: str) -> None:
        """
        Remove alert rule.

        Args:
            rule_name: Name of rule to remove
        """
        if rule_name in self._rules:
            del self._rules[rule_name]

    def get_rule(self, rule_name: str) -> Optional[AlertRule]:
        """
        Get alert rule by name.

        Args:
            rule_name: Name of rule

        Returns:
            Alert rule if found, None otherwise
        """
        return self._rules.get(rule_name)

    def get_rules(self) -> List[AlertRule]:
        """Get all alert rules."""
        return list(self._rules.values())

    def enable_rule(self, rule_name: str) -> None:
        """
        Enable alert rule.

        Args:
            rule_name: Name of rule to enable
        """
        if rule_name in self._rules:
            self._rules[rule_name].enabled = True

    def disable_rule(self, rule_name: str) -> None:
        """
        Disable alert rule.

        Args:
            rule_name: Name of rule to disable
        """
        if rule_name in self._rules:
            self._rules[rule_name].enabled = False

    def _is_in_cooldown(self, rule_name: str, cooldown_seconds: int) -> bool:
        """
        Check if rule is in cooldown period.

        Args:
            rule_name: Name of rule
            cooldown_seconds: Cooldown period in seconds

        Returns:
            True if in cooldown, False otherwise
        """
        if rule_name not in self._last_trigger_time:
            return False

        elapsed = (datetime.now() - self._last_trigger_time[rule_name]).total_seconds()
        return elapsed < cooldown_seconds

    def evaluate_metrics(
        self, metrics: List[Union[BackupMetrics, RestoreMetrics, ScheduleMetrics]]
    ) -> List[AlertTrigger]:
        """
        Evaluate metrics against all rules.

        Args:
            metrics: List of metrics to evaluate

        Returns:
            List of triggered alerts
        """
        triggers = []

        for metric in metrics:
            metric_data = metric.to_dict()

            for rule in self._rules.values():
                if not rule.enabled:
                    continue

                # Check cooldown
                if self._is_in_cooldown(rule.name, rule.cooldown_seconds):
                    continue

                # Evaluate rule
                if rule.evaluate_all_conditions(metric_data):
                    # Get instance and database names
                    instance_name = metric_data.get("instance_name", "unknown")
                    database_name = metric_data.get("database_name")

                    # Create trigger
                    trigger = AlertTrigger(
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=rule.description,
                        timestamp=datetime.now(),
                        metric_value=metric_data.get(rule.condition.metric_name),
                        instance_name=instance_name,
                        database_name=database_name,
                        metadata=metric_data,
                    )

                    triggers.append(trigger)
                    self._triggers_history.append(trigger)
                    self._last_trigger_time[rule.name] = datetime.now()

        return triggers

    def get_triggers_history(
        self, limit: Optional[int] = None
    ) -> List[AlertTrigger]:
        """
        Get alert triggers history.

        Args:
            limit: Maximum number of triggers to return

        Returns:
            List of alert triggers (most recent first)
        """
        history = sorted(
            self._triggers_history, key=lambda t: t.timestamp, reverse=True
        )
        if limit:
            return history[:limit]
        return history

    def clear_triggers_history(self) -> None:
        """Clear alert triggers history."""
        self._triggers_history.clear()
        self._last_trigger_time.clear()

    def get_active_alerts(self) -> List[AlertTrigger]:
        """
        Get currently active alerts (within cooldown period).

        Returns:
            List of active alert triggers
        """
        active = []
        now = datetime.now()

        for trigger in self._triggers_history:
            rule = self._rules.get(trigger.rule_name)
            if not rule:
                continue

            elapsed = (now - trigger.timestamp).total_seconds()
            if elapsed < rule.cooldown_seconds:
                active.append(trigger)

        return active
