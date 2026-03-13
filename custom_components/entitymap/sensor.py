"""Sensor platform for EntityMap summary sensors."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, EVENT_GRAPH_UPDATED

if TYPE_CHECKING:
    from .graph import GraphBuilder

SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="total_nodes",
        translation_key="total_nodes",
        icon="mdi:graph",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="nodes",
    ),
    SensorEntityDescription(
        key="total_edges",
        translation_key="total_edges",
        icon="mdi:vector-polyline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="dependencies",
    ),
    SensorEntityDescription(
        key="fragility_issues",
        translation_key="fragility_issues",
        icon="mdi:alert-outline",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="issues",
    ),
    SensorEntityDescription(
        key="last_scan",
        translation_key="last_scan",
        icon="mdi:clock-check-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EntityMap sensor entities."""
    builder: GraphBuilder = entry.runtime_data.builder
    entities = [
        EntityMapSensor(entry, description, builder)
        for description in SENSOR_DESCRIPTIONS
    ]
    async_add_entities(entities)


class EntityMapSensor(SensorEntity):
    """A summary sensor for EntityMap."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        entry: ConfigEntry,
        description: SensorEntityDescription,
        builder: GraphBuilder,
    ) -> None:
        """Initialize the sensor."""
        self.entity_description = description
        self._builder = builder
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._canonical_object_id = description.key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="EntityMap",
            manufacturer="EntityMap",
            model="Dependency Analyzer",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def suggested_object_id(self) -> str:
        """Force English entity IDs regardless of HA locale."""
        return self._canonical_object_id

    async def async_added_to_hass(self) -> None:
        """Register event listener."""
        self.async_on_remove(
            self.hass.bus.async_listen(
                EVENT_GRAPH_UPDATED, self._handle_graph_update
            )
        )

    @callback
    def _handle_graph_update(self, _event: Any) -> None:
        """Handle graph update event."""
        self.async_write_ha_state()

    @property
    def native_value(self) -> int | datetime | None:
        """Return the sensor value."""
        key = self.entity_description.key
        graph = self._builder.graph

        if key == "total_nodes":
            return graph.node_count
        if key == "total_edges":
            return graph.edge_count
        if key == "fragility_issues":
            from .fragility import detect_fragility

            return len(detect_fragility(graph))
        if key == "last_scan":
            return self._builder.last_scan
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        key = self.entity_description.key
        if key == "total_nodes":
            from collections import Counter

            from .const import NodeType

            graph = self._builder.graph
            type_counts: Counter[str] = Counter()
            for node in graph.nodes.values():
                type_counts[node.node_type.value] += 1
            return {"by_type": dict(type_counts)}
        return {}
