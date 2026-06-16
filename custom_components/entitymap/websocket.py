"""WebSocket API backing the EntityMap frontend panel."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .analysis import analyze_impact
from .const import DOMAIN
from .hierarchy import build_hierarchy
from .migration import get_migration_report

if TYPE_CHECKING:
    from .graph import GraphBuilder

_WS_REGISTERED = False


def async_register_websocket_commands(hass: HomeAssistant) -> None:
    """Register the panel's WebSocket commands once per HA session."""
    global _WS_REGISTERED  # noqa: PLW0603

    if _WS_REGISTERED:
        return

    _WS_REGISTERED = True

    @websocket_api.websocket_command({vol.Required("type"): "entitymap/graph"})
    @websocket_api.async_response
    async def ws_get_graph(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        """Return the full graph data."""
        builder = _require_builder(hass, connection, msg)

        if builder is None:
            return

        connection.send_result(msg["id"], builder.get_graph_data())

    @websocket_api.websocket_command(
        {
            vol.Required("type"): "entitymap/impact",
            vol.Required("node_id"): str,
        }
    )
    @websocket_api.async_response
    async def ws_get_impact(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        """Return impact analysis for a node."""
        builder = _require_builder(hass, connection, msg)

        if builder is None:
            return

        report = analyze_impact(builder.graph, msg["node_id"])
        connection.send_result(msg["id"], report.as_dict())

    @websocket_api.websocket_command(
        {
            vol.Required("type"): "entitymap/neighborhood",
            vol.Required("node_id"): str,
            vol.Optional("depth", default=2): int,
        }
    )
    @websocket_api.async_response
    async def ws_get_neighborhood(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        """Return the neighborhood around a node."""
        builder = _require_builder(hass, connection, msg)

        if builder is None:
            return

        graph = builder.graph
        node_ids, edges = graph.get_neighborhood(msg["node_id"], msg.get("depth", 2))
        nodes = [graph.nodes[nid].as_dict() for nid in node_ids if nid in graph.nodes]
        connection.send_result(
            msg["id"],
            {"nodes": nodes, "edges": [e.as_dict() for e in edges]},
        )

    @websocket_api.websocket_command({vol.Required("type"): "entitymap/scan"})
    @websocket_api.async_response
    async def ws_scan(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        """Trigger a dependency scan."""
        builder = _require_builder(hass, connection, msg)

        if builder is None:
            return

        graph = await builder.async_build()
        connection.send_result(
            msg["id"],
            {"node_count": graph.node_count, "edge_count": graph.edge_count},
        )

    @websocket_api.websocket_command({vol.Required("type"): "entitymap/findings"})
    @websocket_api.async_response
    async def ws_get_findings(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        """Return fragility findings."""
        builder = _require_builder(hass, connection, msg)

        if builder is None:
            return

        findings = builder.findings
        connection.send_result(
            msg["id"],
            {"findings": [f.as_dict() for f in findings], "count": len(findings)},
        )

    @websocket_api.websocket_command(
        {
            vol.Required("type"): "entitymap/migration",
            vol.Required("node_id"): str,
            vol.Optional("target_node_id"): str,
        }
    )
    @websocket_api.async_response
    async def ws_get_migration(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        """Return migration suggestions for a node."""
        builder = _require_builder(hass, connection, msg)

        if builder is None:
            return

        suggestions = get_migration_report(builder.graph, msg["node_id"], msg.get("target_node_id"))
        connection.send_result(
            msg["id"],
            {"suggestions": [s.as_dict() for s in suggestions]},
        )

    @websocket_api.websocket_command({vol.Required("type"): "entitymap/hierarchy"})
    @websocket_api.async_response
    async def ws_get_hierarchy(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        """Return the area -> device -> entity hierarchy tree."""
        builder = _require_builder(hass, connection, msg)

        if builder is None:
            return

        connection.send_result(msg["id"], build_hierarchy(builder.graph))

    websocket_api.async_register_command(hass, ws_get_graph)
    websocket_api.async_register_command(hass, ws_get_impact)
    websocket_api.async_register_command(hass, ws_get_neighborhood)
    websocket_api.async_register_command(hass, ws_scan)
    websocket_api.async_register_command(hass, ws_get_findings)
    websocket_api.async_register_command(hass, ws_get_migration)
    websocket_api.async_register_command(hass, ws_get_hierarchy)


def _get_builder(hass: HomeAssistant) -> GraphBuilder | None:
    """Get the GraphBuilder from the first config entry."""
    entries = hass.config_entries.async_entries(DOMAIN)

    if not entries:
        return None

    entry = entries[0]

    if hasattr(entry, "runtime_data") and entry.runtime_data:
        return entry.runtime_data.builder

    return None


def _require_builder(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> GraphBuilder | None:
    """Return the builder, or send a not_loaded error and return None."""
    builder = _get_builder(hass)

    if builder is None:
        connection.send_error(msg["id"], "not_loaded", "EntityMap not loaded")
        return None

    return builder
