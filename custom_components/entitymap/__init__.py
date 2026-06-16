"""The EntityMap integration - dependency mapping and impact analysis for Home Assistant."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.start import async_at_started

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
    REGISTRY_REFRESH_COOLDOWN_SECONDS,
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
    from .panel import async_register_frontend
    from .services import async_register_services
    from .websocket import async_register_websocket_commands

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
    async_register_websocket_commands(hass)

    # Serve the panel's frontend assets (once per HA session)
    if DATA_VIEW_REGISTERED not in hass.data:
        try:
            await async_register_frontend(hass)
            hass.data[DATA_VIEW_REGISTERED] = True
        except Exception:  # noqa: BLE001
            _LOGGER.debug("EntityMap frontend already registered")

    # Register the frontend sidebar panel (idempotent - overwrites if exists)
    try:
        await _async_register_panel(hass)
    except Exception:  # noqa: BLE001
        _LOGGER.debug("EntityMap panel already registered")

    # Set up entity platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _setup_startup_scan(hass, entry, builder, unsub_listeners)
    _setup_auto_refresh(hass, entry, builder, unsub_listeners)
    _setup_periodic_scan(hass, entry, builder, unsub_listeners)

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    return True


def _setup_startup_scan(
    hass: HomeAssistant,
    entry: EntityMapConfigEntry,
    builder: GraphBuilder,
    unsub_listeners: list[Any],
) -> None:
    """Run the first scan immediately if HA is already running, otherwise on start."""
    if not entry.options.get(CONF_SCAN_ON_STARTUP, DEFAULT_SCAN_ON_STARTUP):
        return

    async def _startup_scan(_hass: HomeAssistant) -> None:
        """Run the initial scan once HA is ready."""
        await builder.async_build()
        await _async_create_repair_issues(hass, builder)

    unsub_listeners.append(async_at_started(hass, _startup_scan))


def _setup_auto_refresh(
    hass: HomeAssistant,
    entry: EntityMapConfigEntry,
    builder: GraphBuilder,
    unsub_listeners: list[Any],
) -> None:
    """Debounce registry-change rescans so a burst collapses into one."""
    if not entry.options.get(CONF_AUTO_REFRESH, DEFAULT_AUTO_REFRESH):
        return

    refresh_debouncer = Debouncer(
        hass,
        _LOGGER,
        cooldown=REGISTRY_REFRESH_COOLDOWN_SECONDS,
        immediate=False,
        function=builder.async_build,
    )
    entry.async_on_unload(refresh_debouncer.async_shutdown)

    @callback
    def _handle_registry_change(_event: Event) -> None:
        """Schedule a debounced rescan when registries change."""
        hass.async_create_task(refresh_debouncer.async_call())

    for event_type in (
        "entity_registry_updated",
        "device_registry_updated",
    ):
        unsub_listeners.append(hass.bus.async_listen(event_type, _handle_registry_change))


def _setup_periodic_scan(
    hass: HomeAssistant,
    entry: EntityMapConfigEntry,
    builder: GraphBuilder,
    unsub_listeners: list[Any],
) -> None:
    """Schedule the periodic reconciliation scan."""
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL_HOURS, DEFAULT_SCAN_INTERVAL_HOURS)

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

    from .panel import PANEL_MODULE_URL

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
                "module_url": PANEL_MODULE_URL,
            }
        },
        require_admin=False,
    )


async def _async_create_repair_issues(hass: HomeAssistant, builder: GraphBuilder) -> None:
    """Create repair issues for critical fragility findings."""
    from homeassistant.helpers import issue_registry as ir

    from .const import FragilityType

    findings = builder.findings

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
