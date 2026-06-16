"""Template adapter - scan template entities for the entities they reference."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterator
from typing import Any

from homeassistant.helpers import entity_registry as er

from ..const import Confidence, DependencyKind, NodeType
from ..models import DependencyGraph, GraphEdge, GraphNode
from .base import SourceAdapter

_LOGGER = logging.getLogger(__name__)

TEMPLATE_ENTITY_PATTERNS = [
    re.compile(r"states\(\s*['\"]([a-z_]+\.[a-z0-9_]+)['\"]\s*\)"),
    re.compile(r"states\.([a-z_]+\.[a-z0-9_]+)"),
    re.compile(r"is_state(?:_attr)?\(\s*['\"]([a-z_]+\.[a-z0-9_]+)['\"]"),
    re.compile(r"state_attr\(\s*['\"]([a-z_]+\.[a-z0-9_]+)['\"]"),
    re.compile(r"has_value\(\s*['\"]([a-z_]+\.[a-z0-9_]+)['\"]"),
    re.compile(r"expand\(\s*['\"]([a-z_]+\.[a-z0-9_]+)['\"]"),
]


class TemplateAdapter(SourceAdapter):
    """Scan template entities for the entities their templates reference."""

    async def async_populate(self, graph: DependencyGraph) -> None:
        """Add an edge from each template entity to the entities it references."""
        entity_reg = er.async_get(self.hass)

        for entry in entity_reg.entities.values():
            if entry.platform != "template":
                continue

            refs = self._extract_refs(entry.entity_id, entry.config_entry_id)
            self._link_references(graph, entry.entity_id, refs)

    def _link_references(self, graph: DependencyGraph, source_id: str, refs: set[str]) -> None:
        """Link a template entity to each of the entities its templates reference."""
        for ref in refs:
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
                    source=source_id,
                    target=ref,
                    dependency_kind=DependencyKind.TEMPLATE_REFERENCE,
                    confidence=Confidence.MEDIUM,
                    source_of_truth="template_config",
                    notes="Inferred from template configuration",
                )
            )

    def _extract_refs(self, entity_id: str, config_entry_id: str | None) -> set[str]:
        """Extract entity references from this template entity's own config.

        UI-created template helpers keep their templates in the backing config
        entry's options/data, so we read only the strings belonging to this
        entity's entry. YAML `template:` entities have no such entry and are
        skipped here (their source is not exposed at runtime).
        """
        refs: set[str] = set()
        if not config_entry_id:
            return refs

        entry = self.hass.config_entries.async_get_entry(config_entry_id)
        if entry is None or entry.domain != "template":
            return refs

        for text in self._iter_strings((entry.options, entry.data)):
            for pattern in TEMPLATE_ENTITY_PATTERNS:
                refs.update(pattern.findall(text))

        refs.discard(entity_id)
        return refs

    @staticmethod
    def _iter_strings(roots: tuple[Any, ...]) -> Iterator[str]:
        """Yield every string nested in the given config values."""
        stack: list[Any] = list(roots)
        while stack:
            value = stack.pop()
            if isinstance(value, str):
                yield value
            elif isinstance(value, dict):
                stack.extend(value.values())
            elif isinstance(value, (list, tuple)):
                stack.extend(value)
