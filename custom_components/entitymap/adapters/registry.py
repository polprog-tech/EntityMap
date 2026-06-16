"""Registry adapter - devices, entities, and areas from HA registries."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    area_registry as ar,
)
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers import (
    entity_registry as er,
)

from ..const import Confidence, DependencyKind, NodeType
from ..models import DependencyGraph, GraphEdge, GraphNode
from .base import SourceAdapter

_LOGGER = logging.getLogger(__name__)

# Helper domains recognized as "helper" node types
HELPER_DOMAINS: frozenset[str] = frozenset(
    {
        "input_boolean",
        "input_number",
        "input_text",
        "input_select",
        "input_datetime",
        "input_button",
        "counter",
        "timer",
    }
)


class RegistryAdapter(SourceAdapter):
    """Populate graph from entity, device, and area registries."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the adapter."""
        super().__init__(hass)

    async def async_populate(self, graph: DependencyGraph) -> None:
        """Populate graph with registry data."""
        self._populate_areas(graph, ar.async_get(self.hass))
        self._populate_devices(graph, dr.async_get(self.hass))
        self._populate_entities(graph, er.async_get(self.hass))

        _LOGGER.debug(
            "RegistryAdapter populated %d nodes and %d edges",
            graph.node_count,
            graph.edge_count,
        )

    @staticmethod
    def _populate_areas(graph: DependencyGraph, area_reg: ar.AreaRegistry) -> None:
        """Add a node for each registered area."""
        for area in area_reg.async_list_areas():
            graph.add_node(
                GraphNode(
                    node_id=f"area.{area.id}",
                    node_type=NodeType.AREA,
                    title=area.name or area.id,
                    area_id=area.id,
                )
            )

    @staticmethod
    def _populate_devices(graph: DependencyGraph, device_reg: dr.DeviceRegistry) -> None:
        """Add a node per device and an edge to its area."""
        for device in device_reg.devices.values():
            device_node_id = f"device.{device.id}"
            graph.add_node(
                GraphNode(
                    node_id=device_node_id,
                    node_type=NodeType.DEVICE,
                    title=(device.name_by_user or device.name or device.id),
                    device_id=device.id,
                    area_id=device.area_id,
                    disabled=device.disabled_by is not None,
                    metadata={
                        "manufacturer": device.manufacturer,
                        "model": device.model,
                        "via_device_id": device.via_device_id,
                    },
                )
            )

            if not device.area_id:
                continue

            graph.add_edge(
                GraphEdge(
                    source=device_node_id,
                    target=f"area.{device.area_id}",
                    dependency_kind=DependencyKind.DEVICE_IN_AREA,
                    confidence=Confidence.HIGH,
                    source_of_truth="device_registry",
                )
            )

    def _populate_entities(self, graph: DependencyGraph, entity_reg: er.EntityRegistry) -> None:
        """Add a node per entity and an edge to its device."""
        for entry in entity_reg.entities.values():
            domain = entry.entity_id.split(".")[0]
            state = self.hass.states.get(entry.entity_id)
            available = state is None or state.state != "unavailable"

            graph.add_node(
                GraphNode(
                    node_id=entry.entity_id,
                    node_type=self._classify_entity(domain, entry),
                    title=(entry.name or entry.original_name or entry.entity_id),
                    entity_id=entry.entity_id,
                    device_id=entry.device_id,
                    area_id=entry.area_id,
                    disabled=entry.disabled_by is not None,
                    available=available,
                )
            )

            if not entry.device_id:
                continue

            graph.add_edge(
                GraphEdge(
                    source=entry.entity_id,
                    target=f"device.{entry.device_id}",
                    dependency_kind=DependencyKind.ENTITY_OF_DEVICE,
                    confidence=Confidence.HIGH,
                    source_of_truth="entity_registry",
                )
            )

    @staticmethod
    def _classify_entity(domain: str, entry: er.RegistryEntry) -> NodeType:
        """Classify an entity registry entry into a NodeType."""
        if domain == "automation":
            return NodeType.AUTOMATION
        if domain == "script":
            return NodeType.SCRIPT
        if domain == "scene":
            return NodeType.SCENE
        if domain == "group":
            return NodeType.GROUP
        if domain in HELPER_DOMAINS:
            return NodeType.HELPER
        return NodeType.ENTITY
