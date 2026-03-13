"""Script adapter — parse script configs for dependency edges."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from ..const import Confidence, DependencyKind, NodeType
from ..models import DependencyGraph, GraphEdge, GraphNode
from .automation import _as_list, _extract_entity_ids, _extract_template_refs
from .base import SourceAdapter

_LOGGER = logging.getLogger(__name__)


class ScriptAdapter(SourceAdapter):
    """Extract dependency edges from script configurations."""

    async def async_populate(self, graph: DependencyGraph) -> None:
        """Scan scripts and add edges to the graph."""
        states = self.hass.states.async_all("script")
        store = _get_script_store(self.hass)

        configs: list[tuple[str, dict[str, Any]]] = []
        if store:
            for obj_id, config in store.items():
                entity_id = f"script.{obj_id}"
                configs.append((entity_id, config))
        else:
            for state in states:
                configs.append((state.entity_id, dict(state.attributes)))

        for entity_id, config in configs:
            self._process_script(graph, entity_id, config)

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

        sequence = _as_list(config.get("sequence", config.get("actions", [])))
        for action in sequence:
            if isinstance(action, dict):
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

        # Service call targets
        if isinstance(target, dict):
            for entity_id in _extract_entity_ids(target, "entity_id"):
                self._ensure_node(graph, entity_id, NodeType.ENTITY)
                graph.add_edge(
                    GraphEdge(
                        source=script_entity_id,
                        target=entity_id,
                        dependency_kind=DependencyKind.ACTION,
                        confidence=Confidence.HIGH,
                        source_of_truth="script_config",
                    )
                )
            for device_id in _as_list(target.get("device_id", [])):
                if device_id:
                    device_node_id = f"device.{device_id}"
                    self._ensure_node(graph, device_node_id, NodeType.DEVICE)
                    graph.add_edge(
                        GraphEdge(
                            source=script_entity_id,
                            target=device_node_id,
                            dependency_kind=DependencyKind.DEVICE_ACTION,
                            confidence=Confidence.HIGH,
                            source_of_truth="script_config",
                        )
                    )

        # Legacy entity_id in action
        for entity_id in _extract_entity_ids(action, "entity_id"):
            self._ensure_node(graph, entity_id, NodeType.ENTITY)
            graph.add_edge(
                GraphEdge(
                    source=script_entity_id,
                    target=entity_id,
                    dependency_kind=DependencyKind.ACTION,
                    confidence=Confidence.HIGH,
                    source_of_truth="script_config",
                )
            )

        # Entity IDs in data
        if isinstance(data, dict):
            for entity_id in _extract_entity_ids(data, "entity_id"):
                self._ensure_node(graph, entity_id, NodeType.ENTITY)
                graph.add_edge(
                    GraphEdge(
                        source=script_entity_id,
                        target=entity_id,
                        dependency_kind=DependencyKind.ACTION,
                        confidence=Confidence.HIGH,
                        source_of_truth="script_config",
                    )
                )

        # Script calling another script
        if isinstance(service, str) and service.startswith("script."):
            self._ensure_node(graph, service, NodeType.SCRIPT)
            graph.add_edge(
                GraphEdge(
                    source=script_entity_id,
                    target=service,
                    dependency_kind=DependencyKind.SERVICE_CALL,
                    confidence=Confidence.HIGH,
                    source_of_truth="script_config",
                )
            )

        # Template references in data values
        for value in data.values() if isinstance(data, dict) else []:
            if (isinstance(value, str) and "{%" in value) or "{{" in str(value):
                for ref in _extract_template_refs(str(value)):
                    self._ensure_node(graph, ref, NodeType.ENTITY)
                    graph.add_edge(
                        GraphEdge(
                            source=script_entity_id,
                            target=ref,
                            dependency_kind=DependencyKind.TEMPLATE_REFERENCE,
                            confidence=Confidence.MEDIUM,
                            source_of_truth="script_config",
                        )
                    )

        # Nested actions
        for key in ("choose", "sequence", "default", "then", "else"):
            nested = action.get(key)
            if isinstance(nested, list):
                for item in nested:
                    if isinstance(item, dict):
                        if "sequence" in item:
                            for sub in _as_list(item["sequence"]):
                                self._process_action(graph, script_entity_id, sub)
                        else:
                            self._process_action(graph, script_entity_id, item)

        if "repeat" in action and isinstance(action["repeat"], dict):
            for sub in _as_list(action["repeat"].get("sequence", [])):
                self._process_action(graph, script_entity_id, sub)

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
    """Try to get script configs."""
    try:
        component = hass.data.get("script")
        if component is None:
            return None
        if hasattr(component, "async_items"):
            items = component.async_items()
            return {
                item.get("id", ""): item.as_dict() if hasattr(item, "as_dict") else item
                for item in items
            }
        return None
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Could not access script store")
        return None
