"""The EntityMap integration - dependency mapping and impact analysis for Home Assistant."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_AUTO_REFRESH,
    CONF_SCAN_INTERVAL_HOURS,
    CONF_SCAN_ON_STARTUP,
    DEFAULT_AUTO_REFRESH,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DEFAULT_SCAN_ON_STARTUP,
    DOMAIN,
    PANEL_ICON,
    PANEL_TITLE,
)
from .graph import GraphBuilder

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor", "button"]

DATA_VIEW_REGISTERED = f"{DOMAIN}_view_registered"


@dataclass
class EntityMapRuntimeData:
    """Runtime data for the EntityMap integration."""

    builder: GraphBuilder
    unsub_listeners: list[Any]


type EntityMapConfigEntry = ConfigEntry[EntityMapRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: EntityMapConfigEntry) -> bool:
    """Set up EntityMap from a config entry."""
    from .panel import EntityMapPanelView
    from .services import async_register_services

    builder = GraphBuilder(hass, entry)
    unsub_listeners: list[Any] = []

    # Store runtime data
    entry.runtime_data = EntityMapRuntimeData(
        builder=builder,
        unsub_listeners=unsub_listeners,
    )

    # Register services
    await async_register_services(hass, builder)

    # Register WebSocket commands (idempotent)
    _register_websocket_commands(hass)

    # Register the panel JS serving endpoint (once per HA session)
    if DATA_VIEW_REGISTERED not in hass.data:
        try:
            hass.http.register_view(EntityMapPanelView())
            hass.data[DATA_VIEW_REGISTERED] = True
        except Exception:  # noqa: BLE001
            _LOGGER.debug("EntityMap panel view already registered")

    # Register the frontend sidebar panel (idempotent - overwrites if exists)
    try:
        await _async_register_panel(hass)
    except Exception:  # noqa: BLE001
        _LOGGER.debug("EntityMap panel already registered")

    # Set up entity platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Schedule initial scan
    options = entry.options
    if options.get(CONF_SCAN_ON_STARTUP, DEFAULT_SCAN_ON_STARTUP):

        async def _startup_scan(_event: Event) -> None:
            """Run initial scan after HA is fully started."""
            await builder.async_build()
            # Create repair issues for critical findings
            await _async_create_repair_issues(hass, builder)

        unsub_listeners.append(
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _startup_scan)
        )

    # Auto-refresh on registry changes
    if options.get(CONF_AUTO_REFRESH, DEFAULT_AUTO_REFRESH):

        @callback
        def _handle_registry_change(_event: Event) -> None:
            """Schedule a rescan when registries change."""
            hass.async_create_task(builder.async_build())

        for event_type in (
            "entity_registry_updated",
            "device_registry_updated",
        ):
            unsub_listeners.append(hass.bus.async_listen(event_type, _handle_registry_change))

    # Periodic reconciliation scan
    scan_interval = options.get(CONF_SCAN_INTERVAL_HOURS, DEFAULT_SCAN_INTERVAL_HOURS)

    async def _periodic_scan(_now: Any) -> None:
        """Periodic reconciliation scan."""
        await builder.async_build()

    unsub_listeners.append(
        async_track_time_interval(
            hass,
            _periodic_scan,
            timedelta(hours=scan_interval),
        )
    )

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    return True


async def _async_update_options(hass: HomeAssistant, entry: EntityMapConfigEntry) -> None:
    """Handle options update - reload the integration."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: EntityMapConfigEntry) -> bool:
    """Unload a config entry."""
    from homeassistant.components import frontend

    from .services import async_unregister_services

    # Remove listeners
    for unsub in entry.runtime_data.unsub_listeners:
        if callable(unsub):
            unsub()

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Unregister services
    await async_unregister_services(hass)

    # Remove panel
    frontend.async_remove_panel(hass, "entitymap")

    return unload_ok


async def _async_register_panel(hass: HomeAssistant) -> None:
    """Register the EntityMap frontend panel."""
    from homeassistant.components import frontend

    frontend.async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path="entitymap",
        config={
            "_panel_custom": {
                "name": "entitymap-panel",
                "embed_iframe": False,
                "trust_external": False,
                "module_url": "/api/panel_custom/entitymap",
            }
        },
        require_admin=False,
    )


async def _async_create_repair_issues(hass: HomeAssistant, builder: GraphBuilder) -> None:
    """Create repair issues for critical fragility findings."""
    from homeassistant.helpers import issue_registry as ir

    from .const import FragilityType
    from .fragility import detect_fragility

    findings = detect_fragility(builder.graph)

    # Count device_id references
    device_id_count = sum(
        1 for f in findings if f.fragility_type == FragilityType.DEVICE_ID_REFERENCE
    )
    if device_id_count > 0:
        ir.async_create_issue(
            hass,
            DOMAIN,
            "fragile_device_id_usage",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="fragile_device_id_usage",
            translation_placeholders={"count": str(device_id_count)},
        )

    # Missing entity references
    missing_refs = [f for f in findings if f.fragility_type == FragilityType.MISSING_ENTITY]
    for finding in missing_refs[:5]:  # Limit to 5 repair issues
        related = finding.related_node_ids[0] if finding.related_node_ids else "unknown"
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"missing_entity_{finding.finding_id}",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="missing_entity_reference",
            translation_placeholders={
                "entity_id": related,
                "source_name": finding.node_id,
            },
        )


# ── WebSocket API ───────────────────────────────────────────────────

_WS_REGISTERED = False


def _register_websocket_commands(hass: HomeAssistant) -> None:
    """Register WebSocket commands for the frontend panel."""
    global _WS_REGISTERED  # noqa: PLW0603
    if _WS_REGISTERED:
        return
    _WS_REGISTERED = True

    from homeassistant.components import websocket_api

    from .analysis import analyze_impact
    from .fragility import detect_fragility

    @websocket_api.websocket_command({vol.Required("type"): "entitymap/graph"})
    @websocket_api.async_response
    async def ws_get_graph(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        """Return the full graph data."""
        builder = _get_builder(hass)
        if not builder:
            connection.send_error(msg["id"], "not_loaded", "EntityMap not loaded")
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
        builder = _get_builder(hass)
        if not builder:
            connection.send_error(msg["id"], "not_loaded", "EntityMap not loaded")
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
        builder = _get_builder(hass)
        if not builder:
            connection.send_error(msg["id"], "not_loaded", "EntityMap not loaded")
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
        builder = _get_builder(hass)
        if not builder:
            connection.send_error(msg["id"], "not_loaded", "EntityMap not loaded")
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
        builder = _get_builder(hass)
        if not builder:
            connection.send_error(msg["id"], "not_loaded", "EntityMap not loaded")
            return
        findings = detect_fragility(builder.graph)
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
        from .migration import get_migration_report

        builder = _get_builder(hass)
        if not builder:
            connection.send_error(msg["id"], "not_loaded", "EntityMap not loaded")
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
        """Return the area → device → entity hierarchy tree."""
        builder = _get_builder(hass)
        if not builder:
            connection.send_error(msg["id"], "not_loaded", "EntityMap not loaded")
            return
        connection.send_result(msg["id"], _build_hierarchy(builder.graph))

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
        builder: GraphBuilder = entry.runtime_data.builder
        return builder
    return None


def _build_hierarchy(graph: Any) -> dict[str, Any]:
    """Build an area → device → entity hierarchy tree from the graph.

    Returns a dict with:
      areas: list of area objects, each containing devices and direct entities
      unassigned_devices: devices without an area
      unassigned_entities: entities without an area or device
    """
    from .const import NodeType

    areas: dict[str, dict[str, Any]] = {}
    devices: dict[str, dict[str, Any]] = {}
    entities_by_area: dict[str, list[dict[str, Any]]] = {}
    unassigned_devices: list[dict[str, Any]] = []
    unassigned_entities: list[dict[str, Any]] = []

    # Collect areas
    for node in graph.nodes.values():
        if node.node_type == NodeType.AREA:
            areas[node.area_id or node.node_id.removeprefix("area.")] = {
                "node_id": node.node_id,
                "title": node.title,
                "node_type": node.node_type.value,
                "devices": [],
                "entities": [],
            }

    # Collect devices, group by area
    for node in graph.nodes.values():
        if node.node_type == NodeType.DEVICE:
            dev = {
                "node_id": node.node_id,
                "title": node.title,
                "node_type": node.node_type.value,
                "area_id": node.area_id,
                "disabled": node.disabled,
                "available": node.available,
                "metadata": node.metadata,
                "entities": [],
            }
            devices[node.device_id or node.node_id.removeprefix("device.")] = dev

    # Collect entities, link to device or area
    for node in graph.nodes.values():
        if node.node_type in (
            NodeType.ENTITY,
            NodeType.AUTOMATION,
            NodeType.SCRIPT,
            NodeType.SCENE,
            NodeType.HELPER,
            NodeType.GROUP,
        ):
            ent = {
                "node_id": node.node_id,
                "title": node.title,
                "node_type": node.node_type.value,
                "entity_id": node.entity_id,
                "device_id": node.device_id,
                "area_id": node.area_id,
                "disabled": node.disabled,
                "available": node.available,
            }
            if node.device_id and node.device_id in devices:
                devices[node.device_id]["entities"].append(ent)
            elif node.area_id and node.area_id in areas:
                entities_by_area.setdefault(node.area_id, []).append(ent)
            else:
                unassigned_entities.append(ent)

    # Build final area tree
    result_areas = []
    for area_id, area in areas.items():
        # Attach devices that belong to this area
        for dev in devices.values():
            if dev["area_id"] == area_id:
                area["devices"].append(dev)
        # Attach direct entities (not via device)
        area["entities"] = entities_by_area.get(area_id, [])
        # Counts
        area["device_count"] = len(area["devices"])
        area["entity_count"] = (
            area["device_count"]
            + len(area["entities"])
            + sum(len(d["entities"]) for d in area["devices"])
        )
        result_areas.append(area)

    # Unassigned devices (no area)
    for dev in devices.values():
        if not dev["area_id"] or dev["area_id"] not in areas:
            unassigned_devices.append(dev)

    result_areas.sort(key=lambda a: a["title"].lower())

    return {
        "areas": result_areas,
        "unassigned_devices": unassigned_devices,
        "unassigned_entities": unassigned_entities,
    }
