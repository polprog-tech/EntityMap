"""Impact analysis engine for EntityMap."""

from __future__ import annotations

from collections import Counter

from .const import NodeType, Severity
from .models import (
    DependencyGraph,
    FragilityFinding,
    ImpactReport,
    MigrationSuggestion,
)


def analyze_impact(graph: DependencyGraph, node_id: str) -> ImpactReport:
    """Analyze the impact of removing/disabling a node."""
    if node_id not in graph.nodes:
        return ImpactReport(
            target_node_id=node_id,
            summary=f"Node '{node_id}' not found in the dependency graph.",
            severity=Severity.INFO,
        )

    node = graph.nodes[node_id]

    # Get all direct dependents
    direct_dependents = graph.get_dependents(node_id)

    # Get transitive dependents
    all_affected = graph.get_transitive_dependents(node_id)

    # Count by type
    type_counter: Counter[str] = Counter()
    for dep_id in all_affected:
        if dep_id in graph.nodes:
            type_counter[graph.nodes[dep_id].node_type.value] += 1

    # Calculate risk score (0-100)
    risk_score = _calculate_risk_score(graph, node_id, direct_dependents, all_affected)

    # Determine severity
    severity = _risk_to_severity(risk_score)

    # Build summary
    parts: list[str] = []
    for ntype, count in sorted(type_counter.items(), key=lambda x: -x[1]):
        label = ntype + "s" if count > 1 else ntype
        parts.append(f"{count} {label}")
    affected_summary = ", ".join(parts) if parts else "no objects"
    summary = f"Removing or replacing '{node.title}' may affect {affected_summary}."

    # Fragility findings for this node
    findings = _get_node_findings(graph, node_id)

    # Migration suggestions
    suggestions = _get_migration_suggestions(graph, node_id, node)

    return ImpactReport(
        target_node_id=node_id,
        affected_nodes=tuple(sorted(all_affected)),
        affected_by_type=dict(type_counter),
        risk_score=risk_score,
        severity=severity,
        summary=summary,
        migration_suggestions=tuple(suggestions),
        fragility_findings=tuple(findings),
    )


def _calculate_risk_score(
    graph: DependencyGraph,
    node_id: str,
    direct_deps: set[str],
    transitive_deps: set[str],
) -> float:
    """Calculate a risk score from 0-100."""
    score = 0.0

    # Direct dependents contribute more
    score += min(len(direct_deps) * 10, 40)

    # Transitive dependents
    score += min(len(transitive_deps) * 3, 30)

    # High-value dependents (automations, scripts) add more risk
    for dep_id in direct_deps:
        dep_node = graph.nodes.get(dep_id)
        if dep_node and dep_node.node_type in (
            NodeType.AUTOMATION,
            NodeType.SCRIPT,
        ):
            score += 5

    # Device ID references (fragile)
    inbound = graph.get_inbound(node_id)
    device_trigger_count = sum(1 for e in inbound if "device" in e.dependency_kind.value)
    score += min(device_trigger_count * 5, 20)

    return min(score, 100.0)


def _risk_to_severity(risk_score: float) -> Severity:
    """Convert risk score to severity level."""
    if risk_score >= 70:
        return Severity.CRITICAL
    if risk_score >= 50:
        return Severity.HIGH
    if risk_score >= 25:
        return Severity.MEDIUM
    if risk_score > 0:
        return Severity.LOW
    return Severity.INFO


def _get_node_findings(graph: DependencyGraph, node_id: str) -> list[FragilityFinding]:
    """Get fragility findings related to a specific node."""
    # Import here to avoid circular dependency
    from .fragility import detect_fragility

    all_findings = detect_fragility(graph)
    return [f for f in all_findings if f.node_id == node_id or node_id in f.related_node_ids]


def _get_migration_suggestions(
    graph: DependencyGraph,
    node_id: str,
    node: object,
) -> list[MigrationSuggestion]:
    """Generate migration suggestions for a node."""
    from .models import GraphNode

    suggestions: list[MigrationSuggestion] = []
    if not isinstance(node, GraphNode):
        return suggestions

    inbound = graph.get_inbound(node_id)

    # Check for device_id-based references
    device_refs = [e for e in inbound if "device" in e.dependency_kind.value]
    if device_refs:
        affected = tuple(e.source for e in device_refs)
        suggestions.append(
            MigrationSuggestion(
                description=(
                    f"This node has {len(device_refs)} device_id-based reference(s). "
                    "These will break if the device is re-paired."
                ),
                affected_items=affected,
                recommendation=(
                    "Where possible, switch automations to use entity-based "
                    "triggers and conditions instead of device_id references."
                ),
            )
        )

    # Suggest reviewing affected automations
    auto_deps = [
        e.source
        for e in inbound
        if graph.nodes.get(e.source) and graph.nodes[e.source].node_type == NodeType.AUTOMATION
    ]
    if auto_deps:
        suggestions.append(
            MigrationSuggestion(
                description=(
                    f"{len(auto_deps)} automation(s) reference this node. "
                    "Review each before making changes."
                ),
                affected_items=tuple(auto_deps),
                recommendation=(
                    "Open each automation and update entity_id references "
                    "to point to the replacement entity."
                ),
            )
        )

    if node.node_type == NodeType.DEVICE:
        # Suggest entity-level migration
        device_entities = [
            e.source
            for e in graph.get_inbound(node_id)
            if graph.nodes.get(e.source) and graph.nodes[e.source].node_type == NodeType.ENTITY
        ]
        if device_entities:
            suggestions.append(
                MigrationSuggestion(
                    description=(
                        f"This device provides {len(device_entities)} entities. "
                        "After replacing the device, map old entities to new ones."
                    ),
                    affected_items=tuple(device_entities),
                    recommendation=(
                        "Note down all entity IDs before removing the device. "
                        "After adding the replacement, use HA's entity ID "
                        "customization to restore the original entity IDs."
                    ),
                )
            )

    return suggestions
