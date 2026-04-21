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
    FragilityFinding,
    GraphEdge,
    GraphNode,
    ImpactReport,
    MigrationSuggestion,
)

# ── GraphNode ───────────────────────────────────────────────────────


class TestGraphNodeCreation:
    """Scenarios for creating graph nodes."""

    """GIVEN an entity node with minimal fields."""
    def test_entity_node_has_correct_defaults(self):

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

    """GIVEN a device node with a device_id."""
    def test_device_node_carries_device_id(self):

        node = GraphNode(
            node_id="device.abc123",
            node_type=NodeType.DEVICE,
            title="Motion Sensor",
            device_id="abc123",
        )

        """THEN the device_id is preserved."""
        assert node.device_id == "abc123"
        assert node.node_type == NodeType.DEVICE

    """GIVEN a disabled entity represented as a node."""
    def test_disabled_node_preserves_state(self):

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

    """GIVEN a fully populated node."""
    def test_as_dict_includes_all_fields(self):

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

    """GIVEN a node with no optional fields."""
    def test_as_dict_none_fields_are_none(self):

        node = GraphNode("test.x", NodeType.UNKNOWN, "X")

        """WHEN serialized."""
        d = node.as_dict()

        """THEN optional fields are None."""
        assert d["entity_id"] is None
        assert d["device_id"] is None
        assert d["area_id"] is None


class TestGraphNodeImmutability:
    """Scenarios verifying frozen dataclass behavior."""

    """GIVEN a frozen GraphNode."""
    def test_cannot_modify_title(self):

        node = GraphNode("test.node", NodeType.ENTITY, "Test")

        """WHEN attempting to modify a field."""

        """THEN an AttributeError is raised."""
        with pytest.raises(AttributeError):
            node.title = "Changed"

    """GIVEN a frozen GraphNode."""
    def test_cannot_modify_node_type(self):

        node = GraphNode("test.node", NodeType.ENTITY, "Test")

        """WHEN attempting to change node_type."""

        """THEN an AttributeError is raised."""
        with pytest.raises(AttributeError):
            node.node_type = NodeType.DEVICE


# ── GraphEdge ───────────────────────────────────────────────────────


class TestGraphEdgeCreation:
    """Scenarios for creating graph edges."""

    """GIVEN an edge with no explicit confidence."""
    def test_edge_defaults_to_high_confidence(self):

        edge = GraphEdge(
            source="automation.test",
            target="light.living_room",
            dependency_kind=DependencyKind.TRIGGER,
        )

        """THEN confidence defaults to HIGH."""
        assert edge.source == "automation.test"
        assert edge.target == "light.living_room"
        assert edge.confidence == Confidence.HIGH

    """GIVEN an edge with LOW confidence."""
    def test_edge_with_explicit_confidence(self):

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

    """GIVEN an edge with enum fields."""
    def test_as_dict_serializes_enums_as_strings(self):

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

    """GIVEN an empty graph."""
    def test_add_single_node(self, empty_graph):

        graph = empty_graph

        """WHEN a node is added."""
        graph.add_node(GraphNode("light.test", NodeType.ENTITY, "Test Light"))

        """THEN the graph contains exactly that node."""
        assert graph.node_count == 1
        assert "light.test" in graph.nodes

    """GIVEN a graph with a node."""
    def test_add_duplicate_node_overwrites(self, empty_graph):

        graph = empty_graph
        graph.add_node(GraphNode("light.test", NodeType.ENTITY, "Old"))

        """WHEN the same node_id is added with a different title."""
        graph.add_node(GraphNode("light.test", NodeType.ENTITY, "New"))

        """THEN the node is overwritten."""
        assert graph.node_count == 1
        assert graph.nodes["light.test"].title == "New"

    """GIVEN a freshly created graph."""
    def test_empty_graph_has_zero_counts(self, empty_graph):

        """THEN node and edge counts are zero."""
        assert empty_graph.node_count == 0
        assert empty_graph.edge_count == 0


class TestGraphEdgeOperations:
    """Scenarios for adding edges and querying relationships."""

    """GIVEN two nodes in a graph."""
    def test_add_edge_between_nodes(self, empty_graph):

        graph = empty_graph
        graph.add_node(GraphNode("a", NodeType.AUTOMATION, "Auto A"))
        graph.add_node(GraphNode("b", NodeType.ENTITY, "Entity B"))

        """WHEN an edge is added between them."""
        graph.add_edge(GraphEdge("a", "b", DependencyKind.TRIGGER))

        """THEN the edge count increments."""
        assert graph.edge_count == 1

    """GIVEN an edge from automation → entity."""
    def test_inbound_edges_point_to_target(self, empty_graph):

        graph = empty_graph
        graph.add_node(GraphNode("a", NodeType.AUTOMATION, "Auto"))
        graph.add_node(GraphNode("b", NodeType.ENTITY, "Entity"))
        graph.add_edge(GraphEdge("a", "b", DependencyKind.TRIGGER))

        """WHEN querying inbound edges on the entity."""
        inbound = graph.get_inbound("b")

        """THEN the automation's edge is returned."""
        assert len(inbound) == 1
        assert inbound[0].source == "a"

    """GIVEN an edge from automation → entity."""
    def test_outbound_edges_point_from_source(self, empty_graph):

        graph = empty_graph
        graph.add_node(GraphNode("a", NodeType.AUTOMATION, "Auto"))
        graph.add_node(GraphNode("b", NodeType.ENTITY, "Entity"))
        graph.add_edge(GraphEdge("a", "b", DependencyKind.TRIGGER))

        """WHEN querying outbound edges on the automation."""
        outbound = graph.get_outbound("a")

        """THEN the entity edge is returned."""
        assert len(outbound) == 1
        assert outbound[0].target == "b"

    """GIVEN an empty graph."""
    def test_inbound_on_unknown_node_returns_empty(self, empty_graph):

        """WHEN querying inbound edges for a nonexistent node."""

        """THEN an empty list is returned."""
        assert empty_graph.get_inbound("nonexistent") == []


class TestGraphDependencyQueries:
    """Scenarios for dependent/dependency lookups."""

    """GIVEN an entity with two automations pointing to it."""
    def test_get_dependents_returns_all_sources(self, empty_graph):

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

    """GIVEN an automation depending on two entities."""
    def test_get_dependencies_returns_all_targets(self, empty_graph):

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

    """GIVEN an isolated node with no inbound edges."""
    def test_dependents_of_isolated_node_is_empty(self, empty_graph):

        graph = empty_graph
        graph.add_node(GraphNode("x", NodeType.ENTITY, "Isolated"))

        """WHEN querying dependents."""

        """THEN an empty set is returned."""
        assert graph.get_dependents("x") == set()


class TestGraphTransitiveTraversal:
    """Scenarios for multi-hop transitive dependency traversal."""

    """GIVEN a chain C ← B ← A."""
    def test_transitive_dependents_follows_chain(self, empty_graph):

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

    """GIVEN a cycle A → B → A."""
    def test_transitive_dependents_handles_cycles(self, empty_graph):

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

    """GIVEN a linear chain A→B, A→C→D."""
    def test_neighborhood_depth_1_excludes_distant_nodes(self, empty_graph):

        graph = empty_graph
        graph.add_node(GraphNode("a", NodeType.AUTOMATION, "A"))
        graph.add_node(GraphNode("b", NodeType.ENTITY, "B"))
        graph.add_node(GraphNode("c", NodeType.ENTITY, "C"))
        graph.add_node(GraphNode("d", NodeType.ENTITY, "D"))
        graph.add_edge(GraphEdge("a", "b", DependencyKind.TRIGGER))
        graph.add_edge(GraphEdge("a", "c", DependencyKind.ACTION))
        graph.add_edge(GraphEdge("c", "d", DependencyKind.TEMPLATE_REFERENCE))

        """WHEN querying neighborhood of A at depth=1."""
        nodes, _edges = graph.get_neighborhood("a", depth=1)

        """THEN A, B, C are included but D is not."""
        assert "a" in nodes
        assert "b" in nodes
        assert "c" in nodes
        assert "d" not in nodes

    """GIVEN a chain A→C→D."""
    def test_neighborhood_depth_2_reaches_distant_nodes(self, empty_graph):

        graph = empty_graph
        graph.add_node(GraphNode("a", NodeType.AUTOMATION, "A"))
        graph.add_node(GraphNode("c", NodeType.ENTITY, "C"))
        graph.add_node(GraphNode("d", NodeType.ENTITY, "D"))
        graph.add_edge(GraphEdge("a", "c", DependencyKind.ACTION))
        graph.add_edge(GraphEdge("c", "d", DependencyKind.TEMPLATE_REFERENCE))

        """WHEN querying neighborhood of A at depth=2."""
        nodes, _edges = graph.get_neighborhood("a", depth=2)

        """THEN D is included."""
        assert "d" in nodes

    """GIVEN a node with no edges."""
    def test_neighborhood_of_isolated_node_returns_only_self(self, empty_graph):

        graph = empty_graph
        graph.add_node(GraphNode("x", NodeType.ENTITY, "Isolated"))

        """WHEN querying its neighborhood."""
        nodes, edges = graph.get_neighborhood("x", depth=3)

        """THEN only the node itself is returned."""
        assert nodes == {"x"}
        assert edges == []


class TestGraphLifecycle:
    """Scenarios for graph clearing and serialization."""

    """GIVEN a graph with nodes and edges."""
    def test_clear_empties_all_collections(self, empty_graph):

        graph = empty_graph
        graph.add_node(GraphNode("a", NodeType.ENTITY, "A"))
        graph.add_node(GraphNode("b", NodeType.ENTITY, "B"))
        graph.add_edge(GraphEdge("a", "b", DependencyKind.TRIGGER))

        """WHEN cleared."""
        graph.clear()

        """THEN all counts are zero."""
        assert graph.node_count == 0
        assert graph.edge_count == 0

    """GIVEN a graph with one node."""
    def test_as_dict_serializes_full_graph(self, empty_graph):

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

    """GIVEN a fragility finding with enum types."""
    def test_as_dict_serializes_all_enum_fields(self):

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

    """GIVEN a finding with no related nodes."""
    def test_empty_related_nodes_serializes_to_empty_list(self):

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

    """GIVEN an impact report with affected types."""
    def test_as_dict_includes_risk_and_affected_types(self):

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

    """GIVEN an impact report with no affected nodes."""
    def test_empty_report_serializes_cleanly(self):

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

    """GIVEN a migration suggestion with all fields."""
    def test_as_dict_includes_all_fields(self):

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

    """GIVEN a suggestion with only a description."""
    def test_minimal_suggestion_has_empty_defaults(self):

        suggestion = MigrationSuggestion(description="Simple note")

        """WHEN serialized."""
        d = suggestion.as_dict()

        """THEN affected_items and recommendation have sensible defaults."""
        assert d["affected_items"] == []
        assert d["recommendation"] == ""
