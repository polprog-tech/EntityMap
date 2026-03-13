"""Domain models for the EntityMap integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .const import (
    Confidence,
    DependencyKind,
    FragilityType,
    NodeType,
    Severity,
)


@dataclass(frozen=True, slots=True)
class GraphNode:
    """A node in the dependency graph."""

    node_id: str
    node_type: NodeType
    title: str
    entity_id: str | None = None
    device_id: str | None = None
    area_id: str | None = None
    disabled: bool = False
    available: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "title": self.title,
            "entity_id": self.entity_id,
            "device_id": self.device_id,
            "area_id": self.area_id,
            "disabled": self.disabled,
            "available": self.available,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """An edge in the dependency graph."""

    source: str
    target: str
    dependency_kind: DependencyKind
    confidence: Confidence = Confidence.HIGH
    source_of_truth: str = ""
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "dependency_kind": self.dependency_kind.value,
            "confidence": self.confidence.value,
            "source_of_truth": self.source_of_truth,
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class FragilityFinding:
    """A fragility finding for a node or edge."""

    finding_id: str
    fragility_type: FragilityType
    severity: Severity
    node_id: str
    related_node_ids: tuple[str, ...] = ()
    rationale: str = ""
    remediation: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "finding_id": self.finding_id,
            "fragility_type": self.fragility_type.value,
            "severity": self.severity.value,
            "node_id": self.node_id,
            "related_node_ids": list(self.related_node_ids),
            "rationale": self.rationale,
            "remediation": self.remediation,
        }


@dataclass(frozen=True, slots=True)
class MigrationSuggestion:
    """A migration suggestion for safer device/entity replacement."""

    description: str
    affected_items: tuple[str, ...] = ()
    recommendation: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "description": self.description,
            "affected_items": list(self.affected_items),
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True, slots=True)
class ImpactReport:
    """Impact analysis report for a target node."""

    target_node_id: str
    affected_nodes: tuple[str, ...] = ()
    affected_by_type: dict[str, int] = field(default_factory=dict)
    risk_score: float = 0.0
    severity: Severity = Severity.INFO
    summary: str = ""
    migration_suggestions: tuple[MigrationSuggestion, ...] = ()
    fragility_findings: tuple[FragilityFinding, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "target_node_id": self.target_node_id,
            "affected_nodes": list(self.affected_nodes),
            "affected_by_type": self.affected_by_type,
            "risk_score": self.risk_score,
            "severity": self.severity.value,
            "summary": self.summary,
            "migration_suggestions": [s.as_dict() for s in self.migration_suggestions],
            "fragility_findings": [f.as_dict() for f in self.fragility_findings],
        }


@dataclass(slots=True)
class DependencyGraph:
    """The complete dependency graph."""

    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)
    _inbound: dict[str, list[GraphEdge]] = field(default_factory=dict)
    _outbound: dict[str, list[GraphEdge]] = field(default_factory=dict)

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.node_id] = node
        if node.node_id not in self._inbound:
            self._inbound[node.node_id] = []
        if node.node_id not in self._outbound:
            self._outbound[node.node_id] = []

    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)
        self._inbound.setdefault(edge.target, []).append(edge)
        self._outbound.setdefault(edge.source, []).append(edge)

    def get_inbound(self, node_id: str) -> list[GraphEdge]:
        """Get edges pointing to this node (what depends on it)."""
        return self._inbound.get(node_id, [])

    def get_outbound(self, node_id: str) -> list[GraphEdge]:
        """Get edges from this node (what it depends on)."""
        return self._outbound.get(node_id, [])

    def get_dependents(self, node_id: str) -> set[str]:
        """Get all node IDs that depend on the given node (inbound sources)."""
        return {edge.source for edge in self.get_inbound(node_id)}

    def get_dependencies(self, node_id: str) -> set[str]:
        """Get all node IDs that the given node depends on (outbound targets)."""
        return {edge.target for edge in self.get_outbound(node_id)}

    def get_transitive_dependents(self, node_id: str) -> set[str]:
        """Get all nodes that transitively depend on the given node."""
        visited: set[str] = set()
        stack = [node_id]
        while stack:
            current = stack.pop()
            for dep in self.get_dependents(current):
                if dep not in visited:
                    visited.add(dep)
                    stack.append(dep)
        return visited

    def get_neighborhood(
        self, node_id: str, depth: int = 1
    ) -> tuple[set[str], list[GraphEdge]]:
        """Get nodes and edges within N hops of the given node."""
        visited: set[str] = {node_id}
        edge_set: set[tuple[str, str, str]] = set()
        result_edges: list[GraphEdge] = []
        frontier = {node_id}

        for _ in range(depth):
            next_frontier: set[str] = set()
            for nid in frontier:
                for edge in self.get_inbound(nid) + self.get_outbound(nid):
                    key = (edge.source, edge.target, edge.dependency_kind)
                    if key not in edge_set:
                        edge_set.add(key)
                        result_edges.append(edge)
                    other = edge.source if edge.target == nid else edge.target
                    if other not in visited:
                        visited.add(other)
                        next_frontier.add(other)
            frontier = next_frontier

        return visited, result_edges

    def clear(self) -> None:
        """Clear the entire graph."""
        self.nodes.clear()
        self.edges.clear()
        self._inbound.clear()
        self._outbound.clear()

    @property
    def node_count(self) -> int:
        """Return the number of nodes."""
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        """Return the number of edges."""
        return len(self.edges)

    def as_dict(self) -> dict[str, Any]:
        """Serialize the full graph."""
        return {
            "nodes": [n.as_dict() for n in self.nodes.values()],
            "edges": [e.as_dict() for e in self.edges],
            "node_count": self.node_count,
            "edge_count": self.edge_count,
        }
