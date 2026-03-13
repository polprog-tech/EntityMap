"""Base adapter interface for source adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod

from homeassistant.core import HomeAssistant

from ..models import DependencyGraph


class SourceAdapter(ABC):
    """Base class for all source adapters."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the adapter."""
        self.hass = hass

    @abstractmethod
    async def async_populate(self, graph: DependencyGraph) -> None:
        """Populate the graph with nodes and edges from this source."""
