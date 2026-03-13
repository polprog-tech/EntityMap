"""Graph builder — orchestrates source adapters and builds the dependency graph."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant

from .adapters.automation import AutomationAdapter
from .adapters.group import GroupAdapter
from .adapters.registry import RegistryAdapter
from .adapters.scene import SceneAdapter
from .adapters.script import ScriptAdapter
from .adapters.template import TemplateAdapter
from .const import (
    CONF_INCLUDE_GROUPS,
    CONF_INCLUDE_TEMPLATES,
    DEFAULT_INCLUDE_GROUPS,
    DEFAULT_INCLUDE_TEMPLATES,
    EVENT_GRAPH_UPDATED,
    EVENT_SCAN_COMPLETED,
    EVENT_SCAN_STARTED,
)
from .models import DependencyGraph

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


class GraphBuilder:
    """Builds and maintains the dependency graph."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the graph builder."""
        self.hass = hass
        self.config_entry = config_entry
        self.graph = DependencyGraph()
        self.last_scan: datetime | None = None
        self._scanning = False
        self._lock = asyncio.Lock()

    @property
    def is_scanning(self) -> bool:
        """Return True if a scan is in progress."""
        return self._scanning

    async def async_build(self) -> DependencyGraph:
        """Build the full dependency graph."""
        async with self._lock:
            if self._scanning:
                _LOGGER.warning("Scan already in progress, skipping")
                return self.graph
            self._scanning = True

        try:
            self.hass.bus.async_fire(EVENT_SCAN_STARTED)
            _LOGGER.info("Starting dependency graph build")

            new_graph = DependencyGraph()
            options = self.config_entry.options

            # Always run registry first — it establishes the base nodes
            adapters = [RegistryAdapter(self.hass)]
            adapters.append(AutomationAdapter(self.hass))
            adapters.append(ScriptAdapter(self.hass))
            adapters.append(SceneAdapter(self.hass))

            if options.get(CONF_INCLUDE_GROUPS, DEFAULT_INCLUDE_GROUPS):
                adapters.append(GroupAdapter(self.hass))

            if options.get(CONF_INCLUDE_TEMPLATES, DEFAULT_INCLUDE_TEMPLATES):
                adapters.append(TemplateAdapter(self.hass))

            for adapter in adapters:
                try:
                    await adapter.async_populate(new_graph)
                except Exception:  # noqa: BLE001
                    _LOGGER.exception(
                        "Error running adapter %s",
                        type(adapter).__name__,
                    )

            # Atomic swap
            self.graph = new_graph
            self.last_scan = datetime.now(timezone.utc)

            _LOGGER.info(
                "Dependency graph built: %d nodes, %d edges",
                new_graph.node_count,
                new_graph.edge_count,
            )

            self.hass.bus.async_fire(EVENT_SCAN_COMPLETED)
            self.hass.bus.async_fire(EVENT_GRAPH_UPDATED)

            return self.graph

        finally:
            self._scanning = False

    def get_graph_data(self) -> dict:
        """Get serializable graph data for the frontend."""
        return self.graph.as_dict()
