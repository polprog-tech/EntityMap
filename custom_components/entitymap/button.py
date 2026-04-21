"""Button platform for EntityMap rescan button."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

if TYPE_CHECKING:
    from .graph import GraphBuilder


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up EntityMap button entities."""
    builder: GraphBuilder = entry.runtime_data.builder
    async_add_entities(
        [
            EntityMapRescanButton(entry, builder),
        ]
    )


class EntityMapRescanButton(ButtonEntity):
    """Button to trigger a full dependency rescan."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_icon = "mdi:refresh"
    _attr_translation_key = "rescan"

    def __init__(self, entry: ConfigEntry, builder: GraphBuilder) -> None:
        """Initialize the button."""
        self.entity_description = ButtonEntityDescription(
            key="rescan",
            translation_key="rescan",
        )
        self._builder = builder
        self._attr_unique_id = f"{entry.entry_id}_rescan"
        self._canonical_object_id = "rescan"
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

    async def async_press(self) -> None:
        """Handle button press - trigger a full rescan."""
        await self._builder.async_build()
