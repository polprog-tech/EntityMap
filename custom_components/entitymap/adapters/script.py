"""Script adapter - parse script configs for dependency edges."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from ..const import Confidence, DependencyKind, NodeType
from ..models import DependencyGraph, GraphEdge, GraphNode
from ._config_parse import (
    as_list,
    extract_entity_ids,
    extract_template_refs,
    iter_nested_actions,
)
from .base import SourceAdapter

_LOGGER = logging.getLogger(__name__)


class ScriptAdapter(SourceAdapter):
    """Extract dependency edges from script configurations."""

    async def async_populate(self, graph: DependencyGraph) -> None:
        """Scan scripts and add edges to the graph."""
        for entity_id, config in self._collect_configs():
            self._process_script(graph, entity_id, config)

    def _collect_configs(self) -> list[tuple[str, dict[str, Any]]]:
        """Get (entity_id, config) pairs from the store, or fall back to states."""
        store = _get_script_store(self.hass)

        if store:
            return [(f"script.{obj_id}", config) for obj_id, config in store.items()]

        return [
            (state.entity_id, dict(state.attributes))
            for state in self.hass.states.async_all("script")
        ]

    def _process_script(
        self,
        graph: DependencyGraph,
        script_entity_id: str,
        config: dict[str, Any],
    ) -> None:
        """Process a single script config."""
        if script_entity_id not in graph.nodes:
            graph.add_node(
                GraphNode(
                    node_id=script_entity_id,
                    node_type=NodeType.SCRIPT,
                    title=config.get("alias", script_entity_id),
                    entity_id=script_entity_id,
                )
            )

        for action in as_list(config.get("sequence", config.get("actions", []))):
            self._process_action(graph, script_entity_id, action)

    def _process_action(
        self,
        graph: DependencyGraph,
        script_entity_id: str,
        action: dict[str, Any],
    ) -> None:
        """Extract edges from an action."""
        if not isinstance(action, dict):
            return

        service = action.get("service", action.get("action", ""))
        target = action.get("target", {})
        data = action.get("data", {})

        if isinstance(target, dict):
            for entity_id in extract_entity_ids(target, "entity_id"):
                self._add_dependency(
                    graph, script_entity_id, entity_id, NodeType.ENTITY, DependencyKind.ACTION
                )

            for device_id in as_list(target.get("device_id", [])):
                if not device_id:
                    continue

                self._add_dependency(
                    graph,
                    script_entity_id,
                    f"device.{device_id}",
                    NodeType.DEVICE,
                    DependencyKind.DEVICE_ACTION,
                )

        for entity_id in extract_entity_ids(action, "entity_id"):
            self._add_dependency(
                graph, script_entity_id, entity_id, NodeType.ENTITY, DependencyKind.ACTION
            )

        if isinstance(data, dict):
            for entity_id in extract_entity_ids(data, "entity_id"):
                self._add_dependency(
                    graph, script_entity_id, entity_id, NodeType.ENTITY, DependencyKind.ACTION
                )

        if isinstance(service, str) and service.startswith("script."):
            self._add_dependency(
                graph, script_entity_id, service, NodeType.SCRIPT, DependencyKind.SERVICE_CALL
            )

        if isinstance(data, dict):
            for value in data.values():
                self._link_template_value(graph, script_entity_id, value)

        for nested_action in iter_nested_actions(action):
            self._process_action(graph, script_entity_id, nested_action)

    def _link_template_value(
        self, graph: DependencyGraph, script_entity_id: str, value: Any
    ) -> None:
        """Add template-reference edges for entities referenced in a templated value."""
        has_template = (isinstance(value, str) and "{%" in value) or "{{" in str(value)

        if not has_template:
            return

        for ref in extract_template_refs(str(value)):
            self._add_dependency(
                graph,
                script_entity_id,
                ref,
                NodeType.ENTITY,
                DependencyKind.TEMPLATE_REFERENCE,
                confidence=Confidence.MEDIUM,
            )

    def _add_dependency(
        self,
        graph: DependencyGraph,
        source: str,
        target: str,
        node_type: NodeType,
        kind: DependencyKind,
        confidence: Confidence = Confidence.HIGH,
    ) -> None:
        """Ensure the target node exists, then add the dependency edge."""
        self._ensure_node(graph, target, node_type)

        graph.add_edge(
            GraphEdge(
                source=source,
                target=target,
                dependency_kind=kind,
                confidence=confidence,
                source_of_truth="script_config",
            )
        )

    @staticmethod
    def _ensure_node(graph: DependencyGraph, node_id: str, node_type: NodeType) -> None:
        """Ensure a node exists in the graph."""
        if node_id not in graph.nodes:
            graph.add_node(
                GraphNode(
                    node_id=node_id,
                    node_type=node_type,
                    title=node_id,
                    entity_id=node_id if "." in node_id else None,
                    available=False,
                )
            )


def _get_script_store(hass: HomeAssistant) -> dict[str, dict[str, Any]] | None:
    """Try to get script configs from the script component store."""
    try:
        component = hass.data.get("script")

        if component is None:
            return None

        if hasattr(component, "async_items"):
            return {
                item.get("id", ""): item.as_dict() if hasattr(item, "as_dict") else item
                for item in component.async_items()
            }

        return None
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Could not access script store")
        return None
