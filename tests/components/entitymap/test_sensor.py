"""Tests for EntityMap summary sensors.

Scenarios cover the reported values (including the cached fragility findings),
the restore bridge used before the first scan, and the scan status attributes
exposed on the last_scan sensor.
"""

from __future__ import annotations

from datetime import UTC, datetime

from custom_components.entitymap.const import (
    DependencyKind,
    FragilityType,
    NodeType,
    Severity,
)
from custom_components.entitymap.graph import GraphBuilder
from custom_components.entitymap.models import FragilityFinding, GraphEdge, GraphNode
from custom_components.entitymap.sensor import SENSOR_DESCRIPTIONS, EntityMapSensor


def _sensor(key, entry, builder):
    """Build the summary sensor for the given description key."""
    description = next(d for d in SENSOR_DESCRIPTIONS if d.key == key)

    return EntityMapSensor(entry, description, builder)


def _scanned_builder(mock_hass, mock_config_entry):
    """A builder that has completed a scan with two nodes and one edge."""
    builder = GraphBuilder(mock_hass, mock_config_entry)
    builder.graph.add_node(GraphNode("light.a", NodeType.ENTITY, "A"))
    builder.graph.add_node(GraphNode("automation.b", NodeType.AUTOMATION, "B"))
    builder.graph.add_edge(GraphEdge("automation.b", "light.a", DependencyKind.ACTION))
    builder.last_scan = datetime(2026, 6, 15, tzinfo=UTC)

    return builder


class TestSensorValues:
    """Scenarios for the value each sensor reports after a scan."""

    def test_total_nodes_and_edges_use_graph_counts(self, mock_hass, mock_config_entry):
        """GIVEN a builder with a scanned graph.

        WHEN the node and edge sensors are read.

        THEN they report the graph counts.
        """
        builder = _scanned_builder(mock_hass, mock_config_entry)

        assert _sensor("total_nodes", mock_config_entry, builder).native_value == 2
        assert _sensor("total_edges", mock_config_entry, builder).native_value == 1

    def test_fragility_sensor_uses_cached_findings(self, mock_hass, mock_config_entry):
        """GIVEN a builder whose findings were cached by the last scan.

        WHEN the fragility sensor is read.

        THEN it returns the cached count without recomputing.
        """
        builder = _scanned_builder(mock_hass, mock_config_entry)
        builder.findings = [
            FragilityFinding(
                finding_id="f1",
                fragility_type=FragilityType.MISSING_ENTITY,
                severity=Severity.HIGH,
                node_id="automation.b",
            ),
            FragilityFinding(
                finding_id="f2",
                fragility_type=FragilityType.DEVICE_ID_REFERENCE,
                severity=Severity.MEDIUM,
                node_id="automation.b",
            ),
        ]

        assert _sensor("fragility_issues", mock_config_entry, builder).native_value == 2

    def test_last_scan_returns_timestamp(self, mock_hass, mock_config_entry):
        """GIVEN a builder that has scanned.

        WHEN the last_scan sensor is read.

        THEN it returns the scan timestamp.
        """
        builder = _scanned_builder(mock_hass, mock_config_entry)

        assert _sensor("last_scan", mock_config_entry, builder).native_value == builder.last_scan


class TestRestoreBridge:
    """Scenarios for the value reported before the first scan of a session."""

    def test_restored_value_used_until_first_scan(self, mock_hass, mock_config_entry):
        """GIVEN a builder that has not scanned yet and a restored value.

        WHEN the sensor is read.

        THEN it returns the restored value instead of an empty graph count.
        """
        builder = GraphBuilder(mock_hass, mock_config_entry)
        sensor = _sensor("total_nodes", mock_config_entry, builder)
        sensor._restored_native_value = 42

        assert builder.last_scan is None
        assert sensor.native_value == 42

    def test_live_value_used_after_scan(self, mock_hass, mock_config_entry):
        """GIVEN a restored value but a scan that has since completed.

        WHEN the sensor is read.

        THEN it returns the live graph count, not the stale restored value.
        """
        builder = _scanned_builder(mock_hass, mock_config_entry)
        sensor = _sensor("total_nodes", mock_config_entry, builder)
        sensor._restored_native_value = 42

        assert sensor.native_value == 2


class TestScanStatusAttributes:
    """Scenarios for the diagnostics exposed on the last_scan sensor."""

    def test_last_scan_exposes_status_duration_and_errors(self, mock_hass, mock_config_entry):
        """GIVEN a builder with a recorded scan status.

        WHEN the last_scan attributes are read.

        THEN status, duration, and adapter error count are exposed.
        """
        builder = _scanned_builder(mock_hass, mock_config_entry)
        builder.last_scan_status = "errors"
        builder.last_scan_duration = 1.25
        builder.adapter_error_count = 2

        attrs = _sensor("last_scan", mock_config_entry, builder).extra_state_attributes

        assert attrs["status"] == "errors"
        assert attrs["duration_seconds"] == 1.25
        assert attrs["adapter_errors"] == 2
