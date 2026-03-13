"""Diagnostics support for EntityMap."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .fragility import detect_fragility


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    builder = entry.runtime_data.builder
    graph = builder.graph
    findings = detect_fragility(graph)

    # Redact entity IDs to avoid leaking user configuration details
    # We keep the domain prefix but redact the object_id part
    def redact_id(node_id: str) -> str:
        if "." in node_id:
            domain, _obj_id = node_id.split(".", 1)
            return f"{domain}.***"
        return "***"

    node_summary: dict[str, int] = {}
    for node in graph.nodes.values():
        node_summary[node.node_type.value] = node_summary.get(node.node_type.value, 0) + 1

    edge_summary: dict[str, int] = {}
    for edge in graph.edges:
        edge_summary[edge.dependency_kind.value] = (
            edge_summary.get(edge.dependency_kind.value, 0) + 1
        )

    finding_summary: dict[str, int] = {}
    for finding in findings:
        finding_summary[finding.fragility_type.value] = (
            finding_summary.get(finding.fragility_type.value, 0) + 1
        )

    return {
        "config_entry": {
            "entry_id": entry.entry_id,
            "options": dict(entry.options),
        },
        "graph": {
            "node_count": graph.node_count,
            "edge_count": graph.edge_count,
            "nodes_by_type": node_summary,
            "edges_by_kind": edge_summary,
        },
        "fragility": {
            "total_findings": len(findings),
            "findings_by_type": finding_summary,
        },
        "scanner": {
            "last_scan": (builder.last_scan.isoformat() if builder.last_scan else None),
            "is_scanning": builder.is_scanning,
        },
    }
