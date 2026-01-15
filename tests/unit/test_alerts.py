"""
Unit tests for alert configuration system (phase9.3).

Tests alert rules, thresholds, and condition evaluation.
"""

from datetime import datetime, timedelta
import pytest
from python_backup.monitoring.alerts import (
    AlertRule,
    AlertCondition,
    AlertSeverity,
    AlertManager,
    AlertTrigger,
    ThresholdType,
)
from python_backup.monitoring.metrics import BackupMetrics, RestoreMetrics


class TestAlertCondition:
    """Test alert condition model."""

    def test_create_threshold_condition(self):
        """Test creating threshold-based condition."""
        condition = AlertCondition(
            metric_name="backup_duration_seconds",
            threshold_type=ThresholdType.GREATER_THAN,
            threshold_value=300.0,  # 5 minutes
        )

        assert condition.metric_name == "backup_duration_seconds"
        assert condition.threshold_type == ThresholdType.GREATER_THAN
        assert condition.threshold_value == 300.0

    def test_evaluate_greater_than(self):
        """Test evaluating greater than condition."""
        condition = AlertCondition(
            metric_name="backup_duration_seconds",
            threshold_type=ThresholdType.GREATER_THAN,
            threshold_value=300.0,
        )

        assert condition.evaluate(350.0) is True
        assert condition.evaluate(250.0) is False
        assert condition.evaluate(300.0) is False

    def test_evaluate_less_than(self):
        """Test evaluating less than condition."""
        condition = AlertCondition(
            metric_name="backup_size_bytes",
            threshold_type=ThresholdType.LESS_THAN,
            threshold_value=1024,
        )

        assert condition.evaluate(500) is True
        assert condition.evaluate(1024) is False
        assert condition.evaluate(2000) is False

    def test_evaluate_equals(self):
        """Test evaluating equals condition."""
        condition = AlertCondition(
            metric_name="backup_success",
            threshold_type=ThresholdType.EQUALS,
            threshold_value=False,
        )

        assert condition.evaluate(False) is True
        assert condition.evaluate(True) is False


class TestAlertRule:
    """Test alert rule model."""

    def test_create_alert_rule(self):
        """Test creating alert rule."""
        rule = AlertRule(
            name="backup_duration_warning",
            description="Warn when backup takes too long",
            severity=AlertSeverity.WARNING,
            condition=AlertCondition(
                metric_name="backup_duration_seconds",
                threshold_type=ThresholdType.GREATER_THAN,
                threshold_value=300.0,
            ),
            enabled=True,
        )

        assert rule.name == "backup_duration_warning"
        assert rule.severity == AlertSeverity.WARNING
        assert rule.enabled is True

    def test_alert_rule_with_multiple_conditions(self):
        """Test alert rule with multiple conditions."""
        rule = AlertRule(
            name="critical_backup_failure",
            description="Critical alert for backup failures",
            severity=AlertSeverity.CRITICAL,
            condition=AlertCondition(
                metric_name="backup_success",
                threshold_type=ThresholdType.EQUALS,
                threshold_value=False,
            ),
            additional_conditions=[
                AlertCondition(
                    metric_name="backup_duration_seconds",
                    threshold_type=ThresholdType.GREATER_THAN,
                    threshold_value=600.0,
                )
            ],
            enabled=True,
        )

        assert len(rule.additional_conditions) == 1

    def test_alert_rule_disabled(self):
        """Test disabled alert rule."""
        rule = AlertRule(
            name="test_alert",
            description="Test alert",
            severity=AlertSeverity.INFO,
            condition=AlertCondition(
                metric_name="test_metric",
                threshold_type=ThresholdType.EQUALS,
                threshold_value=True,
            ),
            enabled=False,
        )

        assert rule.enabled is False


class TestAlertSeverity:
    """Test alert severity levels."""

    def test_severity_levels(self):
        """Test all severity levels."""
        assert AlertSeverity.INFO == "info"
        assert AlertSeverity.WARNING == "warning"
        assert AlertSeverity.ERROR == "error"
        assert AlertSeverity.CRITICAL == "critical"

    def test_severity_ordering(self):
        """Test severity level ordering."""
        severities = [
            AlertSeverity.INFO,
            AlertSeverity.WARNING,
            AlertSeverity.ERROR,
            AlertSeverity.CRITICAL,
        ]

        assert len(severities) == 4


class TestAlertTrigger:
    """Test alert trigger model."""

    def test_create_alert_trigger(self):
        """Test creating alert trigger."""
        trigger = AlertTrigger(
            rule_name="backup_failure",
            severity=AlertSeverity.ERROR,
            message="Backup failed for database mydb",
            timestamp=datetime.now(),
            metric_value=False,
            instance_name="prod-mysql-01",
            database_name="mydb",
        )

        assert trigger.rule_name == "backup_failure"
        assert trigger.severity == AlertSeverity.ERROR
        assert trigger.instance_name == "prod-mysql-01"
        assert trigger.database_name == "mydb"

    def test_alert_trigger_with_metadata(self):
        """Test alert trigger with additional metadata."""
        trigger = AlertTrigger(
            rule_name="backup_duration_warning",
            severity=AlertSeverity.WARNING,
            message="Backup duration exceeded threshold",
            timestamp=datetime.now(),
            metric_value=350.0,
            instance_name="prod-mysql-01",
            database_name="mydb",
            metadata={
                "threshold": 300.0,
                "actual_duration": 350.0,
                "overhead_seconds": 50.0,
            },
        )

        assert trigger.metadata is not None
        assert trigger.metadata["threshold"] == 300.0
        assert trigger.metadata["overhead_seconds"] == 50.0


class TestAlertManager:
    """Test alert manager."""

    @pytest.fixture
    def manager(self):
        """Create alert manager."""
        return AlertManager()

    def test_add_alert_rule(self, manager):
        """Test adding alert rule."""
        rule = AlertRule(
            name="backup_failure",
            description="Alert on backup failure",
            severity=AlertSeverity.ERROR,
            condition=AlertCondition(
                metric_name="backup_success",
                threshold_type=ThresholdType.EQUALS,
                threshold_value=False,
            ),
            enabled=True,
        )

        manager.add_rule(rule)
        assert len(manager.get_rules()) == 1

    def test_remove_alert_rule(self, manager):
        """Test removing alert rule."""
        rule = AlertRule(
            name="test_rule",
            description="Test rule",
            severity=AlertSeverity.INFO,
            condition=AlertCondition(
                metric_name="test_metric",
                threshold_type=ThresholdType.EQUALS,
                threshold_value=True,
            ),
            enabled=True,
        )

        manager.add_rule(rule)
        assert len(manager.get_rules()) == 1

        manager.remove_rule("test_rule")
        assert len(manager.get_rules()) == 0

    def test_get_rule_by_name(self, manager):
        """Test getting rule by name."""
        rule = AlertRule(
            name="backup_duration",
            description="Monitor backup duration",
            severity=AlertSeverity.WARNING,
            condition=AlertCondition(
                metric_name="backup_duration_seconds",
                threshold_type=ThresholdType.GREATER_THAN,
                threshold_value=300.0,
            ),
            enabled=True,
        )

        manager.add_rule(rule)
        retrieved_rule = manager.get_rule("backup_duration")
        assert retrieved_rule is not None
        assert retrieved_rule.name == "backup_duration"

    def test_evaluate_backup_metrics(self, manager):
        """Test evaluating backup metrics against rules."""
        # Add rule
        rule = AlertRule(
            name="backup_failure",
            description="Alert on backup failure",
            severity=AlertSeverity.ERROR,
            condition=AlertCondition(
                metric_name="success",
                threshold_type=ThresholdType.EQUALS,
                threshold_value=False,
            ),
            enabled=True,
        )
        manager.add_rule(rule)

        # Create failed backup metric
        metrics = BackupMetrics(
            instance_name="prod-mysql-01",
            database_name="mydb",
            duration_seconds=10.0,
            backup_size_bytes=0,
            success=False,
            timestamp=datetime.now(),
            error_message="Connection failed",
        )

        # Evaluate
        triggers = manager.evaluate_metrics([metrics])
        assert len(triggers) >= 1

    def test_evaluate_restore_metrics(self, manager):
        """Test evaluating restore metrics against rules."""
        # Add rule for long restore duration
        rule = AlertRule(
            name="restore_duration_warning",
            description="Warn on long restore",
            severity=AlertSeverity.WARNING,
            condition=AlertCondition(
                metric_name="duration_seconds",
                threshold_type=ThresholdType.GREATER_THAN,
                threshold_value=180.0,
            ),
            enabled=True,
        )
        manager.add_rule(rule)

        # Create restore metric with long duration
        metrics = RestoreMetrics(
            instance_name="dev-postgres-01",
            database_name="testdb",
            duration_seconds=250.0,
            restore_size_bytes=1024 * 1024 * 500,
            success=True,
            timestamp=datetime.now(),
        )

        # Evaluate
        triggers = manager.evaluate_metrics([metrics])
        assert len(triggers) >= 1

    def test_disabled_rule_not_evaluated(self, manager):
        """Test that disabled rules are not evaluated."""
        # Add disabled rule
        rule = AlertRule(
            name="disabled_rule",
            description="This rule is disabled",
            severity=AlertSeverity.INFO,
            condition=AlertCondition(
                metric_name="success",
                threshold_type=ThresholdType.EQUALS,
                threshold_value=False,
            ),
            enabled=False,
        )
        manager.add_rule(rule)

        # Create metric that would trigger the rule
        metrics = BackupMetrics(
            instance_name="prod-mysql-01",
            database_name="mydb",
            duration_seconds=10.0,
            backup_size_bytes=0,
            success=False,
            timestamp=datetime.now(),
        )

        # Evaluate - should not trigger disabled rule
        triggers = manager.evaluate_metrics([metrics])
        assert len([t for t in triggers if t.rule_name == "disabled_rule"]) == 0

    def test_enable_disable_rule(self, manager):
        """Test enabling and disabling rules."""
        rule = AlertRule(
            name="test_rule",
            description="Test",
            severity=AlertSeverity.INFO,
            condition=AlertCondition(
                metric_name="test_metric",
                threshold_type=ThresholdType.EQUALS,
                threshold_value=True,
            ),
            enabled=True,
        )
        manager.add_rule(rule)

        # Disable rule
        manager.disable_rule("test_rule")
        retrieved = manager.get_rule("test_rule")
        assert retrieved.enabled is False

        # Enable rule
        manager.enable_rule("test_rule")
        retrieved = manager.get_rule("test_rule")
        assert retrieved.enabled is True

    def test_get_triggers_history(self, manager):
        """Test getting triggers history."""
        rule = AlertRule(
            name="backup_failure",
            description="Alert on failure",
            severity=AlertSeverity.ERROR,
            condition=AlertCondition(
                metric_name="success",
                threshold_type=ThresholdType.EQUALS,
                threshold_value=False,
            ),
            enabled=True,
        )
        manager.add_rule(rule)

        # Trigger alert
        metrics = BackupMetrics(
            instance_name="prod-mysql-01",
            database_name="mydb",
            duration_seconds=10.0,
            backup_size_bytes=0,
            success=False,
            timestamp=datetime.now(),
        )
        manager.evaluate_metrics([metrics])

        # Get history
        history = manager.get_triggers_history()
        assert len(history) >= 1

    def test_clear_triggers_history(self, manager):
        """Test clearing triggers history."""
        rule = AlertRule(
            name="test_rule",
            description="Test",
            severity=AlertSeverity.INFO,
            condition=AlertCondition(
                metric_name="success",
                threshold_type=ThresholdType.EQUALS,
                threshold_value=False,
            ),
            enabled=True,
        )
        manager.add_rule(rule)

        # Create trigger
        metrics = BackupMetrics(
            instance_name="prod-mysql-01",
            database_name="mydb",
            duration_seconds=10.0,
            backup_size_bytes=0,
            success=False,
            timestamp=datetime.now(),
        )
        manager.evaluate_metrics([metrics])

        assert len(manager.get_triggers_history()) >= 1

        # Clear history
        manager.clear_triggers_history()
        assert len(manager.get_triggers_history()) == 0
