"""Graph builder - orchestrates source adapters and builds the dependency graph."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant

from .adapters.automation import AutomationAdapter
from .adapters.base import SourceAdapter
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
    SCAN_STATUS_ERRORS,
    SCAN_STATUS_NEVER,
    SCAN_STATUS_OK,
)
from .models import DependencyGraph

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .models import FragilityFinding

_LOGGER = logging.getLogger(__name__)


class GraphBuilder:
    """Builds and maintains the dependency graph."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the graph builder."""
        self.hass = hass
        self.config_entry = config_entry
        self.graph = DependencyGraph()
        self.findings: list[FragilityFinding] = []
        self.last_scan: datetime | None = None
        self.last_scan_duration: float | None = None
        self.last_scan_status: str = SCAN_STATUS_NEVER
        self.adapter_error_count: int = 0
        self._scanning = False
        self._lock = asyncio.Lock()

    @property
    def is_scanning(self) -> bool:
        """Return True if a scan is in progress."""
        return self._scanning

    def _build_adapters(self, options: Mapping[str, Any]) -> list[SourceAdapter]:
        """Assemble the source adapters to run, registry first to seed base nodes."""
        adapters: list[SourceAdapter] = [
            RegistryAdapter(self.hass),
            AutomationAdapter(self.hass),
            ScriptAdapter(self.hass),
            SceneAdapter(self.hass),
        ]

        if options.get(CONF_INCLUDE_GROUPS, DEFAULT_INCLUDE_GROUPS):
            adapters.append(GroupAdapter(self.hass))

        if options.get(CONF_INCLUDE_TEMPLATES, DEFAULT_INCLUDE_TEMPLATES):
            adapters.append(TemplateAdapter(self.hass))

        return adapters

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
            started = time.monotonic()

            new_graph = DependencyGraph()
            adapters = self._build_adapters(self.config_entry.options)

            error_count = 0
            for adapter in adapters:
                try:
                    await adapter.async_populate(new_graph)
                except Exception:
                    error_count += 1
                    _LOGGER.exception(
                        "Error running adapter %s",
                        type(adapter).__name__,
                    )

            # Compute findings once per scan so sensors and the panel can reuse them
            from .fragility import detect_fragility

            # Atomic swap
            self.graph = new_graph
            self.findings = detect_fragility(new_graph)
            self.last_scan = datetime.now(UTC)
            self.last_scan_duration = time.monotonic() - started
            self.adapter_error_count = error_count
            self.last_scan_status = SCAN_STATUS_OK if error_count == 0 else SCAN_STATUS_ERRORS

            _LOGGER.info(
                "Dependency graph built: %d nodes, %d edges (%d adapter errors)",
                new_graph.node_count,
                new_graph.edge_count,
                error_count,
            )

            self.hass.bus.async_fire(EVENT_SCAN_COMPLETED)
            self.hass.bus.async_fire(EVENT_GRAPH_UPDATED)

            return self.graph

        finally:
            self._scanning = False

    def get_graph_data(self) -> dict:
        """Get serializable graph data for the frontend."""
        return self.graph.as_dict()

    def export_data(self) -> dict:
        """Full graph plus findings and scan metadata, for the export service."""
        data = self.graph.as_dict()
        data["findings"] = [f.as_dict() for f in self.findings]
        data["last_scan"] = self.last_scan.isoformat() if self.last_scan else None
        data["scan_status"] = self.last_scan_status

        return data
