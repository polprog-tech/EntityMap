"""Fragility detection engine for EntityMap."""

from __future__ import annotations

import hashlib
from collections import Counter

from .const import (
    DependencyKind,
    FragilityType,
    NodeType,
    Severity,
)
from .models import DependencyGraph, FragilityFinding


def detect_fragility(graph: DependencyGraph) -> list[FragilityFinding]:
    """Detect fragility issues in the dependency graph."""
    findings: list[FragilityFinding] = []
    findings.extend(_detect_missing_references(graph))
    findings.extend(_detect_device_id_usage(graph))
    findings.extend(_detect_disabled_references(graph))
    findings.extend(_detect_unavailable_references(graph))
    findings.extend(_detect_tight_device_coupling(graph))
    findings.extend(_detect_hidden_dependencies(graph))
    return findings


def _detect_missing_references(graph: DependencyGraph) -> list[FragilityFinding]:
    """Find edges pointing to nodes that don't exist or are marked unavailable."""
    findings: list[FragilityFinding] = []
    for edge in graph.edges:
        target_node = graph.nodes.get(edge.target)
        if target_node is None:
            findings.append(
                FragilityFinding(
                    finding_id=_make_id("missing", edge.source, edge.target),
                    fragility_type=FragilityType.MISSING_ENTITY
                    if "." in edge.target and not edge.target.startswith("device.")
                    else FragilityType.MISSING_DEVICE,
                    severity=Severity.HIGH,
                    node_id=edge.source,
                    related_node_ids=(edge.target,),
                    rationale=(
                        f"'{edge.source}' references '{edge.target}' "
                        f"which does not exist in the registry."
                    ),
                    remediation=(
                        "Check if the referenced entity/device was removed or "
                        "renamed. Update the automation/script to use a valid reference."
                    ),
                )
            )
        elif (
            not target_node.available
            and target_node.node_type not in (NodeType.AREA,)
            and (not target_node.entity_id or not graph.nodes.get(target_node.entity_id))
        ):
            # Node exists but is marked unavailable by registry adapter
            # Only flag if it was not also found in entity registry (truly missing)
            pass  # Already a proper node, just currently unavailable
    return findings


def _detect_device_id_usage(graph: DependencyGraph) -> list[FragilityFinding]:
    """Detect automations/scripts using device_id-based triggers/conditions."""
    findings: list[FragilityFinding] = []
    device_ref_kinds = {
        DependencyKind.DEVICE_TRIGGER,
        DependencyKind.DEVICE_CONDITION,
        DependencyKind.DEVICE_ACTION,
    }
    for edge in graph.edges:
        if edge.dependency_kind in device_ref_kinds:
            source_node = graph.nodes.get(edge.source)
            if source_node and source_node.node_type in (
                NodeType.AUTOMATION,
                NodeType.SCRIPT,
            ):
                findings.append(
                    FragilityFinding(
                        finding_id=_make_id("devid", edge.source, edge.target),
                        fragility_type=FragilityType.DEVICE_ID_REFERENCE,
                        severity=Severity.MEDIUM,
                        node_id=edge.source,
                        related_node_ids=(edge.target,),
                        rationale=(
                            f"'{source_node.title}' uses a device_id reference to "
                            f"'{edge.target}'. Device IDs change when devices are "
                            "re-paired or replaced."
                        ),
                        remediation=(
                            "Where possible, use entity-based triggers and "
                            "conditions instead of device_id-based ones."
                        ),
                    )
                )
    return findings


def _detect_disabled_references(graph: DependencyGraph) -> list[FragilityFinding]:
    """Detect references to disabled entities."""
    findings: list[FragilityFinding] = []
    for edge in graph.edges:
        target_node = graph.nodes.get(edge.target)
        if target_node and target_node.disabled:
            findings.append(
                FragilityFinding(
                    finding_id=_make_id("disabled", edge.source, edge.target),
                    fragility_type=FragilityType.DISABLED_REFERENCE,
                    severity=Severity.LOW,
                    node_id=edge.source,
                    related_node_ids=(edge.target,),
                    rationale=(
                        f"'{edge.source}' references '{edge.target}' which is currently disabled."
                    ),
                    remediation=("Enable the referenced entity or remove the reference."),
                )
            )
    return findings


def _detect_unavailable_references(
    graph: DependencyGraph,
) -> list[FragilityFinding]:
    """Detect references to currently unavailable entities."""
    findings: list[FragilityFinding] = []
    for edge in graph.edges:
        target_node = graph.nodes.get(edge.target)
        if (
            target_node
            and not target_node.available
            and not target_node.disabled
            and target_node.node_type == NodeType.ENTITY
        ):
            findings.append(
                FragilityFinding(
                    finding_id=_make_id("unavail", edge.source, edge.target),
                    fragility_type=FragilityType.UNAVAILABLE_REFERENCE,
                    severity=Severity.LOW,
                    node_id=edge.source,
                    related_node_ids=(edge.target,),
                    rationale=(
                        f"'{edge.source}' references '{edge.target}' "
                        "which is currently unavailable."
                    ),
                    remediation=("Check if the entity's integration is working properly."),
                )
            )
    return findings


def _detect_tight_device_coupling(
    graph: DependencyGraph,
) -> list[FragilityFinding]:
    """Detect automations tightly coupled to a single device via many edges."""
    findings: list[FragilityFinding] = []
    # Count device references per automation
    auto_device_refs: dict[str, Counter[str]] = {}
    device_ref_kinds = {
        DependencyKind.DEVICE_TRIGGER,
        DependencyKind.DEVICE_CONDITION,
        DependencyKind.DEVICE_ACTION,
    }
    for edge in graph.edges:
        if edge.dependency_kind in device_ref_kinds:
            source_node = graph.nodes.get(edge.source)
            if source_node and source_node.node_type == NodeType.AUTOMATION:
                auto_device_refs.setdefault(edge.source, Counter())[edge.target] += 1

    for auto_id, device_counts in auto_device_refs.items():
        for device_id, count in device_counts.items():
            if count >= 3:
                findings.append(
                    FragilityFinding(
                        finding_id=_make_id("tight", auto_id, device_id),
                        fragility_type=FragilityType.TIGHT_DEVICE_COUPLING,
                        severity=Severity.HIGH,
                        node_id=auto_id,
                        related_node_ids=(device_id,),
                        rationale=(
                            f"'{auto_id}' has {count} device_id references to "
                            f"'{device_id}', making it very fragile to device "
                            "replacement."
                        ),
                        remediation=(
                            "Refactor this automation to use entity-based "
                            "references where possible."
                        ),
                    )
                )
    return findings


def _detect_hidden_dependencies(
    graph: DependencyGraph,
) -> list[FragilityFinding]:
    """Detect dependencies hidden through scripts or helpers."""
    findings: list[FragilityFinding] = []
    # Find automations that call scripts which reference other entities
    for edge in graph.edges:
        if edge.dependency_kind == DependencyKind.SERVICE_CALL:
            source_node = graph.nodes.get(edge.source)
            target_node = graph.nodes.get(edge.target)
            if (
                source_node
                and target_node
                and source_node.node_type == NodeType.AUTOMATION
                and target_node.node_type == NodeType.SCRIPT
            ):
                # Check if the script has further dependencies
                script_deps = graph.get_outbound(edge.target)
                if len(script_deps) > 2:
                    findings.append(
                        FragilityFinding(
                            finding_id=_make_id("hidden", edge.source, edge.target),
                            fragility_type=FragilityType.HIDDEN_DEPENDENCY,
                            severity=Severity.INFO,
                            node_id=edge.source,
                            related_node_ids=(edge.target,),
                            rationale=(
                                f"'{source_node.title}' calls script "
                                f"'{target_node.title}' which has "
                                f"{len(script_deps)} further dependencies. "
                                "Changes to those dependencies may affect this "
                                "automation indirectly."
                            ),
                            remediation=(
                                "Review the called script to understand the full dependency chain."
                            ),
                        )
                    )
    return findings


def _make_id(*parts: str) -> str:
    """Create a stable, deterministic finding ID."""
    raw = ":".join(parts)
    return hashlib.md5(raw.encode(), usedforsecurity=False).hexdigest()[:12]
