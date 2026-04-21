"""Tests for the EntityMap impact analysis engine.

Scenarios organized by impact context: nonexistent nodes, entities with
dependents, devices, helpers, isolated nodes, and report quality.
"""

from __future__ import annotations

from custom_components.entitymap.analysis import analyze_impact
from custom_components.entitymap.const import (
    DependencyKind,
    NodeType,
    Severity,
)
from custom_components.entitymap.models import (
    DependencyGraph,
    GraphEdge,
    GraphNode,
)


def _build_realistic_graph() -> DependencyGraph:
    """Build a realistic home automation graph for testing.

    Topology:
        device.motion → binary_sensor.motion → automation.motion_light
        device.light_hw → light.living_room ← automation.motion_light (action)
        automation.motion_light → device.motion (device_trigger, fragile)
        automation.motion_light → input_boolean.guest_mode (condition)
        automation.night_mode → script.dim_lights → light.living_room
    """
    graph = DependencyGraph()

    # Devices
    graph.add_node(GraphNode("device.motion", NodeType.DEVICE, "Motion Sensor", device_id="motion"))
    graph.add_node(
        GraphNode("device.light_hw", NodeType.DEVICE, "Light Hardware", device_id="light_hw")
    )

    # Entities
    graph.add_node(
        GraphNode(
            "binary_sensor.motion",
            NodeType.ENTITY,
            "Motion",
            entity_id="binary_sensor.motion",
            device_id="motion",
        )
    )
    graph.add_node(
        GraphNode(
            "light.living_room",
            NodeType.ENTITY,
            "Living Room Light",
            entity_id="light.living_room",
            device_id="light_hw",
        )
    )
    graph.add_node(
        GraphNode(
            "input_boolean.guest_mode",
            NodeType.HELPER,
            "Guest Mode",
            entity_id="input_boolean.guest_mode",
        )
    )

    # Automations
    graph.add_node(GraphNode("automation.motion_light", NodeType.AUTOMATION, "Motion Light"))
    graph.add_node(GraphNode("automation.night_mode", NodeType.AUTOMATION, "Night Mode"))

    # Script
    graph.add_node(GraphNode("script.dim_lights", NodeType.SCRIPT, "Dim Lights"))

    # Entity → Device edges
    graph.add_edge(
        GraphEdge("binary_sensor.motion", "device.motion", DependencyKind.ENTITY_OF_DEVICE)
    )
    graph.add_edge(
        GraphEdge("light.living_room", "device.light_hw", DependencyKind.ENTITY_OF_DEVICE)
    )

    # Automation → entity/device edges
    graph.add_edge(
        GraphEdge("automation.motion_light", "binary_sensor.motion", DependencyKind.TRIGGER)
    )
    graph.add_edge(GraphEdge("automation.motion_light", "light.living_room", DependencyKind.ACTION))
    graph.add_edge(
        GraphEdge("automation.motion_light", "device.motion", DependencyKind.DEVICE_TRIGGER)
    )
    graph.add_edge(
        GraphEdge("automation.motion_light", "input_boolean.guest_mode", DependencyKind.CONDITION)
    )

    # Night mode chain
    graph.add_edge(
        GraphEdge("automation.night_mode", "script.dim_lights", DependencyKind.SERVICE_CALL)
    )
    graph.add_edge(GraphEdge("script.dim_lights", "light.living_room", DependencyKind.ACTION))

    return graph


class TestImpactOnNonexistentNode:
    """Scenarios where the target node doesn't exist."""

    """GIVEN an empty graph."""
    def test_returns_info_severity(self, empty_graph):

        """WHEN analyzing impact for a nonexistent node."""
        report = analyze_impact(empty_graph, "nonexistent.node")

        """THEN severity is INFO and summary indicates not found."""
        assert report.severity == Severity.INFO
        assert "not found" in report.summary

    """GIVEN an empty graph."""
    def test_returns_zero_affected(self, empty_graph):

        """WHEN analyzing a missing node."""
        report = analyze_impact(empty_graph, "ghost.entity")

        """THEN no nodes are reported as affected."""
        assert len(report.affected_nodes) == 0
        assert report.risk_score == 0.0


class TestImpactOnEntityWithDependents:
    """Scenarios for entities that automations depend on."""

    """GIVEN a motion sensor used as trigger by an automation."""
    def test_sensor_with_automation_trigger(self):

        graph = _build_realistic_graph()

        """WHEN analyzing its impact."""
        report = analyze_impact(graph, "binary_sensor.motion")

        """THEN the automation appears as affected."""
        assert len(report.affected_nodes) > 0
        assert "automation" in report.affected_by_type
        assert report.risk_score > 0

    """GIVEN a light used by both an automation and a script."""
    def test_light_with_multiple_dependents(self):

        graph = _build_realistic_graph()

        """WHEN analyzing its impact."""
        report = analyze_impact(graph, "light.living_room")

        """THEN at least both are reported as affected."""
        assert len(report.affected_nodes) >= 2

    """GIVEN a named entity in the realistic graph."""
    def test_report_summary_mentions_entity_name(self):

        graph = _build_realistic_graph()

        """WHEN analyzing its impact."""
        report = analyze_impact(graph, "light.living_room")

        """THEN the summary references the entity's title."""
        assert report.summary
        assert "Living Room Light" in report.summary


class TestImpactOnDevice:
    """Scenarios for device impact analysis."""

    """GIVEN a device with entities and automations referencing it."""
    def test_device_has_affected_nodes(self):

        graph = _build_realistic_graph()

        """WHEN analyzing its impact."""
        report = analyze_impact(graph, "device.motion")

        """THEN affected nodes are found."""
        assert len(report.affected_nodes) > 0
        assert report.risk_score > 0

    """GIVEN a device with device_id references."""
    def test_device_generates_migration_suggestions(self):

        graph = _build_realistic_graph()

        """WHEN analyzing its impact."""
        report = analyze_impact(graph, "device.motion")

        """THEN migration suggestions are generated."""
        assert len(report.migration_suggestions) > 0


class TestImpactOnHelper:
    """Scenarios for helper entity impact."""

    """GIVEN a helper used as a condition in an automation."""
    def test_helper_used_in_condition(self):

        graph = _build_realistic_graph()

        """WHEN analyzing its impact."""
        report = analyze_impact(graph, "input_boolean.guest_mode")

        """THEN the automation is in affected_by_type."""
        assert "automation" in report.affected_by_type


class TestImpactOnIsolatedNode:
    """Scenarios for nodes with no dependencies."""

    """GIVEN a standalone entity with no edges."""
    def test_isolated_node_has_zero_risk(self):

        graph = DependencyGraph()
        graph.add_node(GraphNode("sensor.standalone", NodeType.ENTITY, "Standalone"))

        """WHEN analyzing its impact."""
        report = analyze_impact(graph, "sensor.standalone")

        """THEN risk score is 0 and severity is INFO."""
        assert report.risk_score == 0
        assert report.severity == Severity.INFO

    """GIVEN a standalone entity."""
    def test_isolated_node_has_empty_affected(self):

        graph = DependencyGraph()
        graph.add_node(GraphNode("sensor.alone", NodeType.ENTITY, "Alone"))

        """WHEN analyzing its impact."""
        report = analyze_impact(graph, "sensor.alone")

        """THEN affected_nodes is empty."""
        assert len(report.affected_nodes) == 0
        assert len(report.affected_by_type) == 0


class TestImpactRiskScoring:
    """Scenarios verifying the risk score calculation."""

    """GIVEN an entity depended on by many automations vs one."""
    def test_high_dependency_count_increases_risk(self):

        graph = DependencyGraph()
        graph.add_node(GraphNode("light.x", NodeType.ENTITY, "X"))
        for i in range(5):
            auto_id = f"automation.auto_{i}"
            graph.add_node(GraphNode(auto_id, NodeType.AUTOMATION, f"Auto {i}"))
            graph.add_edge(GraphEdge(auto_id, "light.x", DependencyKind.TRIGGER))

        single_graph = DependencyGraph()
        single_graph.add_node(GraphNode("light.y", NodeType.ENTITY, "Y"))
        single_graph.add_node(GraphNode("automation.single", NodeType.AUTOMATION, "Single"))
        single_graph.add_edge(GraphEdge("automation.single", "light.y", DependencyKind.TRIGGER))

        """WHEN analyzing impact on both."""
        report_many = analyze_impact(graph, "light.x")
        report_single = analyze_impact(single_graph, "light.y")

        """THEN the risk score is higher for more dependents."""
        assert report_many.risk_score > report_single.risk_score
