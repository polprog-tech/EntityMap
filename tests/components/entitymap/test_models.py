"""Tests for the EntityMap domain models.

Organized by feature/scenario using GIVEN/WHEN/THEN structure.
Each test is designed to be readable at a glance and covers
happy-path, edge-case, and failure-path scenarios.
"""

from __future__ import annotations

import pytest

from custom_components.entitymap.const import (
    Confidence,
    DependencyKind,
    FragilityType,
    NodeType,
    Severity,
)
from custom_components.entitymap.models import (
    DependencyGraph,
    FragilityFinding,
    GraphEdge,
    GraphNode,
    ImpactReport,
    MigrationSuggestion,
)


# ── GraphNode ───────────────────────────────────────────────────────


class TestGraphNodeCreation:
    """Scenarios for creating graph nodes."""

    def test_entity_node_has_correct_defaults(self):
        """GIVEN an entity node with minimal fields."""
        node = GraphNode(
            node_id="light.living_room",
            node_type=NodeType.ENTITY,
            title="Living Room Light",
            entity_id="light.living_room",
        )

        """THEN it has sensible defaults (available, not disabled)."""
        assert node.node_id == "light.living_room"
        assert node.node_type == NodeType.ENTITY
        assert node.title == "Living Room Light"
        assert node.available is True
        assert node.disabled is False
        assert node.metadata == {}

    def test_device_node_carries_device_id(self):
        """GIVEN a device node with a device_id."""
        node = GraphNode(
            node_id="device.abc123",
            node_type=NodeType.DEVICE,
            title="Motion Sensor",
            device_id="abc123",
        )

        """THEN the device_id is preserved."""
        assert node.device_id == "abc123"
        assert node.node_type == NodeType.DEVICE

    def test_disabled_node_preserves_state(self):
        """GIVEN a disabled entity represented as a node."""
        node = GraphNode(
            node_id="switch.old",
            node_type=NodeType.ENTITY,
            title="Old Switch",
            disabled=True,
        )

        """THEN the disabled flag is set."""
        assert node.disabled is True
        assert node.available is True


class TestGraphNodeSerialization:
    """Scenarios for node serialization to dict."""

    def test_as_dict_includes_all_fields(self):
        """GIVEN a fully populated node."""
        node = GraphNode(
            node_id="device.abc123",
            node_type=NodeType.DEVICE,
            title="Motion Sensor",
            device_id="abc123",
            area_id="living_room",
        )

        """WHEN serialized to dict."""
        d = node.as_dict()

        """THEN all fields are present with enum values as strings."""
        assert d["node_id"] == "device.abc123"
        assert d["node_type"] == "device"
        assert d["title"] == "Motion Sensor"
        assert d["device_id"] == "abc123"
        assert d["area_id"] == "living_room"

    def test_as_dict_none_fields_are_none(self):
        """GIVEN a node with no optional fields."""
        node = GraphNode("test.x", NodeType.UNKNOWN, "X")

        """WHEN serialized."""
        d = node.as_dict()

        """THEN optional fields are None."""
        assert d["entity_id"] is None
        assert d["device_id"] is None
        assert d["area_id"] is None


class TestGraphNodeImmutability:
    """Scenarios verifying frozen dataclass behavior."""

    def test_cannot_modify_title(self):
        """GIVEN a frozen GraphNode."""
        node = GraphNode("test.node", NodeType.ENTITY, "Test")

        """WHEN attempting to modify a field."""

        """THEN an AttributeError is raised."""
        with pytest.raises(AttributeError):
            node.title = "Changed"

    def test_cannot_modify_node_type(self):
        """GIVEN a frozen GraphNode."""
        node = GraphNode("test.node", NodeType.ENTITY, "Test")

        """WHEN attempting to change node_type."""

        """THEN an AttributeError is raised."""
        with pytest.raises(AttributeError):
            node.node_type = NodeType.DEVICE


# ── GraphEdge ───────────────────────────────────────────────────────


class TestGraphEdgeCreation:
    """Scenarios for creating graph edges."""

    def test_edge_defaults_to_high_confidence(self):
        """GIVEN an edge with no explicit confidence."""
        edge = GraphEdge(
            source="automation.test",
            target="light.living_room",
            dependency_kind=DependencyKind.TRIGGER,
        )

        """THEN confidence defaults to HIGH."""
        assert edge.source == "automation.test"
        assert edge.target == "light.living_room"
        assert edge.confidence == Confidence.HIGH

    def test_edge_with_explicit_confidence(self):
        """GIVEN an edge with LOW confidence."""
        edge = GraphEdge(
            source="automation.a",
            target="sensor.b",
            dependency_kind=DependencyKind.TEMPLATE_REFERENCE,
            confidence=Confidence.LOW,
            source_of_truth="template_regex",
        )

        """THEN that confidence level is preserved."""
        assert edge.confidence == Confidence.LOW
        assert edge.source_of_truth == "template_regex"


class TestGraphEdgeSerialization:
    """Scenarios for edge serialization."""

    def test_as_dict_serializes_enums_as_strings(self):
        """GIVEN an edge with enum fields."""
        edge = GraphEdge(
            source="automation.test",
            target="light.living_room",
            dependency_kind=DependencyKind.ACTION,
            confidence=Confidence.MEDIUM,
        )

        """WHEN serialized."""
        d = edge.as_dict()

        """THEN enum values become strings."""
        assert d["dependency_kind"] == "action"
        assert d["confidence"] == "medium"
        assert d["source"] == "automation.test"


# ── DependencyGraph ─────────────────────────────────────────────────


class TestGraphNodeOperations:
    """Scenarios for adding and querying nodes."""

    def test_add_single_node(self, empty_graph):
        """GIVEN an empty graph."""
        graph = empty_graph

        """WHEN a node is added."""
        graph.add_node(GraphNode("light.test", NodeType.ENTITY, "Test Light"))

        """THEN the graph contains exactly that node."""
        assert graph.node_count == 1
        assert "light.test" in graph.nodes

    def test_add_duplicate_node_overwrites(self, empty_graph):
        """GIVEN a graph with a node."""
        graph = empty_graph
        graph.add_node(GraphNode("light.test", NodeType.ENTITY, "Old"))

        """WHEN the same node_id is added with a different title."""
        graph.add_node(GraphNode("light.test", NodeType.ENTITY, "New"))

        """THEN the node is overwritten."""
        assert graph.node_count == 1
        assert graph.nodes["light.test"].title == "New"

    def test_empty_graph_has_zero_counts(self, empty_graph):
        """GIVEN a freshly created graph."""

        """THEN node and edge counts are zero."""
        assert empty_graph.node_count == 0
        assert empty_graph.edge_count == 0


class TestGraphEdgeOperations:
    """Scenarios for adding edges and querying relationships."""

    def test_add_edge_between_nodes(self, empty_graph):
        """GIVEN two nodes in a graph."""
        graph = empty_graph
        graph.add_node(GraphNode("a", NodeType.AUTOMATION, "Auto A"))
        graph.add_node(GraphNode("b", NodeType.ENTITY, "Entity B"))

        """WHEN an edge is added between them."""
        graph.add_edge(GraphEdge("a", "b", DependencyKind.TRIGGER))

        """THEN the edge count increments."""
        assert graph.edge_count == 1

    def test_inbound_edges_point_to_target(self, empty_graph):
        """GIVEN an edge from automation → entity."""
        graph = empty_graph
        graph.add_node(GraphNode("a", NodeType.AUTOMATION, "Auto"))
        graph.add_node(GraphNode("b", NodeType.ENTITY, "Entity"))
        graph.add_edge(GraphEdge("a", "b", DependencyKind.TRIGGER))

        """WHEN querying inbound edges on the entity."""
        inbound = graph.get_inbound("b")

        """THEN the automation's edge is returned."""
        assert len(inbound) == 1
        assert inbound[0].source == "a"

    def test_outbound_edges_point_from_source(self, empty_graph):
        """GIVEN an edge from automation → entity."""
        graph = empty_graph
        graph.add_node(GraphNode("a", NodeType.AUTOMATION, "Auto"))
        graph.add_node(GraphNode("b", NodeType.ENTITY, "Entity"))
        graph.add_edge(GraphEdge("a", "b", DependencyKind.TRIGGER))

        """WHEN querying outbound edges on the automation."""
        outbound = graph.get_outbound("a")

        """THEN the entity edge is returned."""
        assert len(outbound) == 1
        assert outbound[0].target == "b"

    def test_inbound_on_unknown_node_returns_empty(self, empty_graph):
        """GIVEN an empty graph."""

        """WHEN querying inbound edges for a nonexistent node."""

        """THEN an empty list is returned."""
        assert empty_graph.get_inbound("nonexistent") == []


class TestGraphDependencyQueries:
    """Scenarios for dependent/dependency lookups."""

    def test_get_dependents_returns_all_sources(self, empty_graph):
        """GIVEN an entity with two automations pointing to it."""
        graph = empty_graph
        graph.add_node(GraphNode("a", NodeType.AUTOMATION, "Auto A"))
        graph.add_node(GraphNode("b", NodeType.AUTOMATION, "Auto B"))
        graph.add_node(GraphNode("c", NodeType.ENTITY, "Entity C"))
        graph.add_edge(GraphEdge("a", "c", DependencyKind.TRIGGER))
        graph.add_edge(GraphEdge("b", "c", DependencyKind.ACTION))

        """WHEN querying dependents."""
        deps = graph.get_dependents("c")

        """THEN both automation IDs are returned."""
        assert deps == {"a", "b"}

    def test_get_dependencies_returns_all_targets(self, empty_graph):
        """GIVEN an automation depending on two entities."""
        graph = empty_graph
        graph.add_node(GraphNode("a", NodeType.AUTOMATION, "Auto"))
        graph.add_node(GraphNode("b", NodeType.ENTITY, "Trigger"))
        graph.add_node(GraphNode("c", NodeType.ENTITY, "Action"))
        graph.add_edge(GraphEdge("a", "b", DependencyKind.TRIGGER))
        graph.add_edge(GraphEdge("a", "c", DependencyKind.ACTION))

        """WHEN querying dependencies."""
        deps = graph.get_dependencies("a")

        """THEN both entity IDs are returned."""
        assert deps == {"b", "c"}

    def test_dependents_of_isolated_node_is_empty(self, empty_graph):
        """GIVEN an isolated node with no inbound edges."""
        graph = empty_graph
        graph.add_node(GraphNode("x", NodeType.ENTITY, "Isolated"))

        """WHEN querying dependents."""

        """THEN an empty set is returned."""
        assert graph.get_dependents("x") == set()


class TestGraphTransitiveTraversal:
    """Scenarios for multi-hop transitive dependency traversal."""

    def test_transitive_dependents_follows_chain(self, empty_graph):
        """GIVEN a chain C ← B ← A."""
        graph = empty_graph
        graph.add_node(GraphNode("a", NodeType.AUTOMATION, "A"))
        graph.add_node(GraphNode("b", NodeType.SCRIPT, "B"))
        graph.add_node(GraphNode("c", NodeType.ENTITY, "C"))
        graph.add_edge(GraphEdge("a", "b", DependencyKind.SERVICE_CALL))
        graph.add_edge(GraphEdge("b", "c", DependencyKind.ACTION))

        """WHEN querying transitive dependents of C."""
        trans = graph.get_transitive_dependents("c")

        """THEN both A and B are returned."""
        assert "b" in trans
        assert "a" in trans

    def test_transitive_dependents_handles_cycles(self, empty_graph):
        """GIVEN a cycle A → B → A."""
        graph = empty_graph
        graph.add_node(GraphNode("a", NodeType.AUTOMATION, "A"))
        graph.add_node(GraphNode("b", NodeType.AUTOMATION, "B"))
        graph.add_edge(GraphEdge("a", "b", DependencyKind.SERVICE_CALL))
        graph.add_edge(GraphEdge("b", "a", DependencyKind.SERVICE_CALL))

        """WHEN querying transitive dependents of B."""
        trans = graph.get_transitive_dependents("b")

        """THEN traversal terminates without infinite loop and returns A."""
        assert "a" in trans


class TestGraphNeighborhood:
    """Scenarios for neighborhood extraction."""

    def test_neighborhood_depth_1_excludes_distant_nodes(self, empty_graph):
        """GIVEN a linear chain A→B, A→C→D."""
        graph = empty_graph
        graph.add_node(GraphNode("a", NodeType.AUTOMATION, "A"))
        graph.add_node(GraphNode("b", NodeType.ENTITY, "B"))
        graph.add_node(GraphNode("c", NodeType.ENTITY, "C"))
        graph.add_node(GraphNode("d", NodeType.ENTITY, "D"))
        graph.add_edge(GraphEdge("a", "b", DependencyKind.TRIGGER))
        graph.add_edge(GraphEdge("a", "c", DependencyKind.ACTION))
        graph.add_edge(GraphEdge("c", "d", DependencyKind.TEMPLATE_REFERENCE))

        """WHEN querying neighborhood of A at depth=1."""
        nodes, edges = graph.get_neighborhood("a", depth=1)

        """THEN A, B, C are included but D is not."""
        assert "a" in nodes
        assert "b" in nodes
        assert "c" in nodes
        assert "d" not in nodes

    def test_neighborhood_depth_2_reaches_distant_nodes(self, empty_graph):
        """GIVEN a chain A→C→D."""
        graph = empty_graph
        graph.add_node(GraphNode("a", NodeType.AUTOMATION, "A"))
        graph.add_node(GraphNode("c", NodeType.ENTITY, "C"))
        graph.add_node(GraphNode("d", NodeType.ENTITY, "D"))
        graph.add_edge(GraphEdge("a", "c", DependencyKind.ACTION))
        graph.add_edge(GraphEdge("c", "d", DependencyKind.TEMPLATE_REFERENCE))

        """WHEN querying neighborhood of A at depth=2."""
        nodes, edges = graph.get_neighborhood("a", depth=2)

        """THEN D is included."""
        assert "d" in nodes

    def test_neighborhood_of_isolated_node_returns_only_self(self, empty_graph):
        """GIVEN a node with no edges."""
        graph = empty_graph
        graph.add_node(GraphNode("x", NodeType.ENTITY, "Isolated"))

        """WHEN querying its neighborhood."""
        nodes, edges = graph.get_neighborhood("x", depth=3)

        """THEN only the node itself is returned."""
        assert nodes == {"x"}
        assert edges == []


class TestGraphLifecycle:
    """Scenarios for graph clearing and serialization."""

    def test_clear_empties_all_collections(self, empty_graph):
        """GIVEN a graph with nodes and edges."""
        graph = empty_graph
        graph.add_node(GraphNode("a", NodeType.ENTITY, "A"))
        graph.add_node(GraphNode("b", NodeType.ENTITY, "B"))
        graph.add_edge(GraphEdge("a", "b", DependencyKind.TRIGGER))

        """WHEN cleared."""
        graph.clear()

        """THEN all counts are zero."""
        assert graph.node_count == 0
        assert graph.edge_count == 0

    def test_as_dict_serializes_full_graph(self, empty_graph):
        """GIVEN a graph with one node."""
        graph = empty_graph
        graph.add_node(GraphNode("a", NodeType.ENTITY, "A"))

        """WHEN serialized."""
        d = graph.as_dict()

        """THEN the dict contains nodes, edges, and counts."""
        assert d["node_count"] == 1
        assert d["edge_count"] == 0
        assert len(d["nodes"]) == 1
        assert d["nodes"][0]["node_id"] == "a"


# ── FragilityFinding ────────────────────────────────────────────────


class TestFragilityFindingSerialization:
    """Scenarios for fragility finding serialization."""

    def test_as_dict_serializes_all_enum_fields(self):
        """GIVEN a fragility finding with enum types."""
        finding = FragilityFinding(
            finding_id="test123",
            fragility_type=FragilityType.MISSING_ENTITY,
            severity=Severity.HIGH,
            node_id="automation.test",
            related_node_ids=("light.missing",),
            rationale="Entity does not exist",
            remediation="Fix the reference",
        )

        """WHEN serialized."""
        d = finding.as_dict()

        """THEN enum values are strings."""
        assert d["finding_id"] == "test123"
        assert d["fragility_type"] == "missing_entity"
        assert d["severity"] == "high"
        assert d["related_node_ids"] == ["light.missing"]

    def test_empty_related_nodes_serializes_to_empty_list(self):
        """GIVEN a finding with no related nodes."""
        finding = FragilityFinding(
            finding_id="abc",
            fragility_type=FragilityType.DEVICE_ID_REFERENCE,
            severity=Severity.LOW,
            node_id="automation.x",
        )

        """WHEN serialized."""
        d = finding.as_dict()

        """THEN related_node_ids is an empty list."""
        assert d["related_node_ids"] == []


# ── ImpactReport ───────────────────────────────────────────────────


class TestImpactReportSerialization:
    """Scenarios for impact report serialization."""

    def test_as_dict_includes_risk_and_affected_types(self):
        """GIVEN an impact report with affected types."""
        report = ImpactReport(
            target_node_id="light.test",
            affected_nodes=("automation.a",),
            affected_by_type={"automation": 1},
            risk_score=25.0,
            severity=Severity.MEDIUM,
            summary="Test summary",
        )

        """WHEN serialized."""
        d = report.as_dict()

        """THEN risk_score and affected_by_type are present."""
        assert d["risk_score"] == 25.0
        assert d["affected_by_type"]["automation"] == 1
        assert d["severity"] == "medium"

    def test_empty_report_serializes_cleanly(self):
        """GIVEN an impact report with no affected nodes."""
        report = ImpactReport(target_node_id="x.y")

        """WHEN serialized."""
        d = report.as_dict()

        """THEN affected_nodes is empty and score is zero."""
        assert d["affected_nodes"] == []
        assert d["risk_score"] == 0.0
        assert d["severity"] == "info"


# ── MigrationSuggestion ────────────────────────────────────────────


class TestMigrationSuggestionSerialization:
    """Scenarios for migration suggestion serialization."""

    def test_as_dict_includes_all_fields(self):
        """GIVEN a migration suggestion with all fields."""
        suggestion = MigrationSuggestion(
            description="Test suggestion",
            affected_items=("automation.a",),
            recommendation="Do this",
        )

        """WHEN serialized."""
        d = suggestion.as_dict()

        """THEN description, affected_items, recommendation are present."""
        assert d["description"] == "Test suggestion"
        assert len(d["affected_items"]) == 1
        assert d["recommendation"] == "Do this"

    def test_minimal_suggestion_has_empty_defaults(self):
        """GIVEN a suggestion with only a description."""
        suggestion = MigrationSuggestion(description="Simple note")

        """WHEN serialized."""
        d = suggestion.as_dict()

        """THEN affected_items and recommendation have sensible defaults."""
        assert d["affected_items"] == []
        assert d["recommendation"] == ""
