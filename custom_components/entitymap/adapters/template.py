"""Template adapter - scan template entities for entity references."""

from __future__ import annotations

import logging
import re

from homeassistant.helpers import entity_registry as er

from ..const import Confidence, DependencyKind, NodeType
from ..models import DependencyGraph, GraphEdge, GraphNode
from .base import SourceAdapter

_LOGGER = logging.getLogger(__name__)

TEMPLATE_ENTITY_PATTERNS = [
    re.compile(r"states\(\s*['\"]([a-z_]+\.[a-z0-9_]+)['\"]\s*\)"),
    re.compile(r"states\.([a-z_]+\.[a-z0-9_]+)"),
    re.compile(r"is_state\(\s*['\"]([a-z_]+\.[a-z0-9_]+)['\"]"),
    re.compile(r"state_attr\(\s*['\"]([a-z_]+\.[a-z0-9_]+)['\"]"),
    re.compile(r"expand\(\s*['\"]([a-z_]+\.[a-z0-9_]+)['\"]"),
]


class TemplateAdapter(SourceAdapter):
    """Scan template entities for entity references."""

    async def async_populate(self, graph: DependencyGraph) -> None:
        """Scan template entities and extract references."""
        entity_reg = er.async_get(self.hass)

        for entry in entity_reg.entities.values():
            if entry.platform != "template":
                continue

            entity_id = entry.entity_id
            # Try to get template config from HA storage
            template_refs = await self._extract_refs_for_entity(entity_id)
            if not template_refs:
                continue

            for ref in template_refs:
                if ref not in graph.nodes:
                    graph.add_node(
                        GraphNode(
                            node_id=ref,
                            node_type=NodeType.ENTITY,
                            title=ref,
                            entity_id=ref,
                            available=False,
                        )
                    )
                graph.add_edge(
                    GraphEdge(
                        source=entity_id,
                        target=ref,
                        dependency_kind=DependencyKind.TEMPLATE_REFERENCE,
                        confidence=Confidence.MEDIUM,
                        source_of_truth="template_config",
                        notes="Inferred from template configuration",
                    )
                )

    async def _extract_refs_for_entity(self, entity_id: str) -> list[str]:
        """Extract entity references from a template entity's config."""
        refs: set[str] = set()

        # Try accessing the template component's storage
        try:
            template_data = self.hass.data.get("template")
            if template_data and hasattr(template_data, "async_items"):
                for item in template_data.async_items():
                    config = item.as_dict() if hasattr(item, "as_dict") else item
                    config_str = str(config)
                    for pattern in TEMPLATE_ENTITY_PATTERNS:
                        refs.update(pattern.findall(config_str))
        except Exception:  # noqa: BLE001
            _LOGGER.debug("Could not access template store for %s", entity_id)

        # Remove self-references
        refs.discard(entity_id)
        return list(refs)
