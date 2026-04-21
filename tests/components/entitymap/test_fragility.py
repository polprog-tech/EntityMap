"""Tests for the EntityMap fragility detection engine.

Organized by finding type with GIVEN/WHEN/THEN scenarios covering
happy-path (clean graph), each fragility type, and edge cases.
"""

from __future__ import annotations

from custom_components.entitymap.const import (
    DependencyKind,
    FragilityType,
    NodeType,
    Severity,
)
from custom_components.entitymap.fragility import detect_fragility
from custom_components.entitymap.models import (
    DependencyGraph,
    GraphEdge,
    GraphNode,
)


class TestCleanGraph:
    """Scenarios where no fragility issues should be detected."""

    """GIVEN an empty graph."""
    def test_empty_graph_has_no_findings(self, empty_graph):

        """WHEN detecting fragility."""
        findings = detect_fragility(empty_graph)

        """THEN zero findings are returned."""
        assert len(findings) == 0

    """GIVEN a well-formed graph with valid entity references."""
    def test_clean_entity_graph_has_no_critical_findings(self):

        graph = DependencyGraph()
        graph.add_node(GraphNode("light.test", NodeType.ENTITY, "Test Light"))
        graph.add_node(GraphNode("automation.test", NodeType.AUTOMATION, "Test Auto"))
        graph.add_edge(GraphEdge("automation.test", "light.test", DependencyKind.TRIGGER))

        """WHEN detecting fragility."""
        findings = detect_fragility(graph)

        """THEN no missing-ref or device_id findings are produced."""
        device_id_findings = [
            f for f in findings if f.fragility_type == FragilityType.DEVICE_ID_REFERENCE
        ]
        missing_findings = [
            f
            for f in findings
            if f.fragility_type in (FragilityType.MISSING_ENTITY, FragilityType.MISSING_DEVICE)
        ]
        assert len(device_id_findings) == 0
        assert len(missing_findings) == 0


class TestMissingEntityReference:
    """Scenarios for the MISSING_ENTITY fragility type."""

    """GIVEN an automation with an edge to a non-existent entity."""
    def test_detects_edge_to_nonexistent_entity(self):

        graph = DependencyGraph()
        graph.add_node(GraphNode("automation.test", NodeType.AUTOMATION, "Test Auto"))
        graph.add_edge(GraphEdge("automation.test", "light.nonexistent", DependencyKind.TRIGGER))

        """WHEN detecting fragility."""
        findings = detect_fragility(graph)

        """THEN a MISSING_ENTITY finding is created."""
        missing = [f for f in findings if f.fragility_type == FragilityType.MISSING_ENTITY]
        assert len(missing) == 1
        assert missing[0].node_id == "automation.test"
        assert "light.nonexistent" in missing[0].related_node_ids

    """GIVEN an automation with a missing entity reference."""
    def test_finding_has_actionable_remediation(self):

        graph = DependencyGraph()
        graph.add_node(GraphNode("automation.x", NodeType.AUTOMATION, "X"))
        graph.add_edge(GraphEdge("automation.x", "sensor.gone", DependencyKind.CONDITION))

        """WHEN detecting fragility."""
        findings = detect_fragility(graph)
        missing = [f for f in findings if f.fragility_type == FragilityType.MISSING_ENTITY]

        """THEN the remediation text suggests corrective action."""
        assert len(missing) == 1
        assert missing[0].remediation


class TestMissingDeviceReference:
    """Scenarios for the MISSING_DEVICE fragility type."""

    """GIVEN an automation with a device_trigger edge to a missing device."""
    def test_detects_edge_to_nonexistent_device(self):

        graph = DependencyGraph()
        graph.add_node(GraphNode("automation.test", NodeType.AUTOMATION, "Test Auto"))
        graph.add_edge(GraphEdge("automation.test", "device.gone", DependencyKind.DEVICE_TRIGGER))

        """WHEN detecting fragility."""
        findings = detect_fragility(graph)

        """THEN a MISSING_DEVICE finding is created."""
        missing = [f for f in findings if f.fragility_type == FragilityType.MISSING_DEVICE]
        assert len(missing) == 1


class TestDeviceIdUsage:
    """Scenarios for the DEVICE_ID_REFERENCE fragility type."""

    """GIVEN an automation using a device_trigger to an existing device."""
    def test_detects_device_trigger_usage(self):

        graph = DependencyGraph()
        graph.add_node(GraphNode("automation.test", NodeType.AUTOMATION, "Test Auto"))
        graph.add_node(GraphNode("device.sensor1", NodeType.DEVICE, "Sensor"))
        graph.add_edge(
            GraphEdge("automation.test", "device.sensor1", DependencyKind.DEVICE_TRIGGER)
        )

        """WHEN detecting fragility."""
        findings = detect_fragility(graph)

        """THEN a DEVICE_ID_REFERENCE finding with MEDIUM severity is created."""
        devid = [f for f in findings if f.fragility_type == FragilityType.DEVICE_ID_REFERENCE]
        assert len(devid) == 1
        assert devid[0].severity == Severity.MEDIUM

    """GIVEN an automation using only entity-based triggers."""
    def test_no_device_id_finding_for_entity_triggers(self):

        graph = DependencyGraph()
        graph.add_node(GraphNode("automation.test", NodeType.AUTOMATION, "Test"))
        graph.add_node(GraphNode("sensor.temp", NodeType.ENTITY, "Temp"))
        graph.add_edge(GraphEdge("automation.test", "sensor.temp", DependencyKind.TRIGGER))

        """WHEN detecting fragility."""
        findings = detect_fragility(graph)

        """THEN no DEVICE_ID_REFERENCE findings are produced."""
        devid = [f for f in findings if f.fragility_type == FragilityType.DEVICE_ID_REFERENCE]
        assert len(devid) == 0


class TestDisabledReference:
    """Scenarios for the DISABLED_REFERENCE fragility type."""

    """GIVEN an automation referencing a disabled entity."""
    def test_detects_reference_to_disabled_entity(self):

        graph = DependencyGraph()
        graph.add_node(GraphNode("automation.test", NodeType.AUTOMATION, "Test"))
        graph.add_node(
            GraphNode(
                "light.disabled_light",
                NodeType.ENTITY,
                "Disabled Light",
                disabled=True,
            )
        )
        graph.add_edge(GraphEdge("automation.test", "light.disabled_light", DependencyKind.ACTION))

        """WHEN detecting fragility."""
        findings = detect_fragility(graph)

        """THEN a DISABLED_REFERENCE finding is created."""
        disabled = [f for f in findings if f.fragility_type == FragilityType.DISABLED_REFERENCE]
        assert len(disabled) == 1

    """GIVEN an automation referencing an enabled entity."""
    def test_no_finding_for_enabled_entity(self):

        graph = DependencyGraph()
        graph.add_node(GraphNode("automation.test", NodeType.AUTOMATION, "Test"))
        graph.add_node(GraphNode("light.ok", NodeType.ENTITY, "OK", disabled=False))
        graph.add_edge(GraphEdge("automation.test", "light.ok", DependencyKind.ACTION))

        """WHEN detecting fragility."""
        findings = detect_fragility(graph)

        """THEN no DISABLED_REFERENCE finding is produced."""
        disabled = [f for f in findings if f.fragility_type == FragilityType.DISABLED_REFERENCE]
        assert len(disabled) == 0


class TestTightDeviceCoupling:
    """Scenarios for the TIGHT_DEVICE_COUPLING fragility type."""

    """GIVEN an automation with 3+ device_id references to one device."""
    def test_three_device_refs_triggers_finding(self):

        graph = DependencyGraph()
        graph.add_node(GraphNode("automation.test", NodeType.AUTOMATION, "Test"))
        graph.add_node(GraphNode("device.sensor1", NodeType.DEVICE, "Sensor"))
        for kind in [
            DependencyKind.DEVICE_TRIGGER,
            DependencyKind.DEVICE_CONDITION,
            DependencyKind.DEVICE_ACTION,
        ]:
            graph.add_edge(GraphEdge("automation.test", "device.sensor1", kind))

        """WHEN detecting fragility."""
        findings = detect_fragility(graph)

        """THEN a TIGHT_DEVICE_COUPLING finding with HIGH severity is created."""
        tight = [f for f in findings if f.fragility_type == FragilityType.TIGHT_DEVICE_COUPLING]
        assert len(tight) == 1
        assert tight[0].severity == Severity.HIGH

    """GIVEN an automation with only 2 device_id references."""
    def test_two_device_refs_is_not_tight(self):

        graph = DependencyGraph()
        graph.add_node(GraphNode("automation.test", NodeType.AUTOMATION, "Test"))
        graph.add_node(GraphNode("device.sensor1", NodeType.DEVICE, "Sensor"))
        graph.add_edge(
            GraphEdge("automation.test", "device.sensor1", DependencyKind.DEVICE_TRIGGER)
        )
        graph.add_edge(
            GraphEdge("automation.test", "device.sensor1", DependencyKind.DEVICE_CONDITION)
        )

        """WHEN detecting fragility."""
        findings = detect_fragility(graph)

        """THEN no TIGHT_DEVICE_COUPLING finding is produced."""
        tight = [f for f in findings if f.fragility_type == FragilityType.TIGHT_DEVICE_COUPLING]
        assert len(tight) == 0


class TestHiddenDependency:
    """Scenarios for the HIDDEN_DEPENDENCY fragility type."""

    """GIVEN an automation calling a script that has 3+ dependencies."""
    def test_automation_calling_complex_script(self):

        graph = DependencyGraph()
        graph.add_node(GraphNode("automation.test", NodeType.AUTOMATION, "Test Auto"))
        graph.add_node(GraphNode("script.complex", NodeType.SCRIPT, "Complex Script"))
        graph.add_node(GraphNode("light.a", NodeType.ENTITY, "A"))
        graph.add_node(GraphNode("light.b", NodeType.ENTITY, "B"))
        graph.add_node(GraphNode("light.c", NodeType.ENTITY, "C"))
        graph.add_edge(GraphEdge("automation.test", "script.complex", DependencyKind.SERVICE_CALL))
        graph.add_edge(GraphEdge("script.complex", "light.a", DependencyKind.ACTION))
        graph.add_edge(GraphEdge("script.complex", "light.b", DependencyKind.ACTION))
        graph.add_edge(GraphEdge("script.complex", "light.c", DependencyKind.ACTION))

        """WHEN detecting fragility."""
        findings = detect_fragility(graph)

        """THEN a HIDDEN_DEPENDENCY finding with INFO severity is created."""
        hidden = [f for f in findings if f.fragility_type == FragilityType.HIDDEN_DEPENDENCY]
        assert len(hidden) == 1
        assert hidden[0].severity == Severity.INFO

    """GIVEN an automation calling a script with only 1 dependency."""
    def test_automation_calling_simple_script_is_not_hidden(self):

        graph = DependencyGraph()
        graph.add_node(GraphNode("automation.test", NodeType.AUTOMATION, "Test"))
        graph.add_node(GraphNode("script.simple", NodeType.SCRIPT, "Simple"))
        graph.add_node(GraphNode("light.a", NodeType.ENTITY, "A"))
        graph.add_edge(GraphEdge("automation.test", "script.simple", DependencyKind.SERVICE_CALL))
        graph.add_edge(GraphEdge("script.simple", "light.a", DependencyKind.ACTION))

        """WHEN detecting fragility."""
        findings = detect_fragility(graph)

        """THEN no HIDDEN_DEPENDENCY finding is produced."""
        hidden = [f for f in findings if f.fragility_type == FragilityType.HIDDEN_DEPENDENCY]
        assert len(hidden) == 0


class TestFindingIdStability:
    """Scenarios verifying deterministic finding IDs."""

    """GIVEN two identical graphs with the same missing reference."""
    def test_same_inputs_produce_same_finding_id(self):

        def _make_graph():
            g = DependencyGraph()
            g.add_node(GraphNode("automation.x", NodeType.AUTOMATION, "X"))
            g.add_edge(GraphEdge("automation.x", "light.gone", DependencyKind.TRIGGER))
            return g

        """WHEN detecting fragility on both."""
        findings1 = detect_fragility(_make_graph())
        findings2 = detect_fragility(_make_graph())

        """THEN the finding IDs are identical (deterministic)."""
        assert len(findings1) > 0
        assert findings1[0].finding_id == findings2[0].finding_id
