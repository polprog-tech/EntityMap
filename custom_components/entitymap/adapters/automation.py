"""Automation adapter - parse automation configs for dependency edges."""

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


class AutomationAdapter(SourceAdapter):
    """Extract dependency edges from automation configurations."""

    async def async_populate(self, graph: DependencyGraph) -> None:
        """Scan automations and add edges to the graph."""
        for entity_id, config in self._collect_configs():
            self._process_automation(graph, entity_id, config)

    def _collect_configs(self) -> list[tuple[str, dict[str, Any]]]:
        """Get (entity_id, config) pairs from the store, or fall back to states."""
        store = _get_automation_store(self.hass)

        if store:
            return [(f"automation.{item.get('id', '')}", item) for item in store]

        return [
            (state.entity_id, dict(state.attributes))
            for state in self.hass.states.async_all("automation")
        ]

    def _process_automation(
        self,
        graph: DependencyGraph,
        auto_entity_id: str,
        config: dict[str, Any],
    ) -> None:
        """Process a single automation config."""
        if auto_entity_id not in graph.nodes:
            graph.add_node(
                GraphNode(
                    node_id=auto_entity_id,
                    node_type=NodeType.AUTOMATION,
                    title=config.get("alias", auto_entity_id),
                    entity_id=auto_entity_id,
                )
            )

        for trigger in as_list(config.get("trigger", config.get("triggers", []))):
            self._process_trigger(graph, auto_entity_id, trigger)

        for condition in as_list(config.get("condition", config.get("conditions", []))):
            self._process_condition(graph, auto_entity_id, condition)

        for action in as_list(config.get("action", config.get("actions", []))):
            self._process_action(graph, auto_entity_id, action)

    def _process_trigger(
        self,
        graph: DependencyGraph,
        auto_entity_id: str,
        trigger: dict[str, Any],
    ) -> None:
        """Extract edges from a trigger definition."""
        if not isinstance(trigger, dict):
            return

        device_id = trigger.get("device_id")

        if device_id:
            self._add_dependency(
                graph,
                auto_entity_id,
                f"device.{device_id}",
                NodeType.DEVICE,
                DependencyKind.DEVICE_TRIGGER,
            )

        for entity_id in extract_entity_ids(trigger, "entity_id"):
            self._add_dependency(
                graph, auto_entity_id, entity_id, NodeType.ENTITY, DependencyKind.TRIGGER
            )

        if trigger.get("platform", trigger.get("trigger", "")) == "template":
            for ref in extract_template_refs(str(trigger.get("value_template", ""))):
                self._add_dependency(
                    graph,
                    auto_entity_id,
                    ref,
                    NodeType.ENTITY,
                    DependencyKind.TEMPLATE_REFERENCE,
                    confidence=Confidence.MEDIUM,
                    notes="Extracted from value_template",
                )

    def _process_condition(
        self,
        graph: DependencyGraph,
        auto_entity_id: str,
        condition: dict[str, Any],
    ) -> None:
        """Extract edges from a condition definition."""
        if not isinstance(condition, dict):
            return

        for entity_id in extract_entity_ids(condition, "entity_id"):
            self._add_dependency(
                graph, auto_entity_id, entity_id, NodeType.ENTITY, DependencyKind.CONDITION
            )

        device_id = condition.get("device_id")

        if device_id:
            self._add_dependency(
                graph,
                auto_entity_id,
                f"device.{device_id}",
                NodeType.DEVICE,
                DependencyKind.DEVICE_CONDITION,
            )

        for ref in extract_template_refs(str(condition.get("value_template", ""))):
            self._add_dependency(
                graph,
                auto_entity_id,
                ref,
                NodeType.ENTITY,
                DependencyKind.TEMPLATE_REFERENCE,
                confidence=Confidence.MEDIUM,
            )

    def _process_action(
        self,
        graph: DependencyGraph,
        auto_entity_id: str,
        action: dict[str, Any],
    ) -> None:
        """Extract edges from an action definition."""
        if not isinstance(action, dict):
            return

        service = action.get("service", action.get("action", ""))
        target = action.get("target", {})
        data = action.get("data", {})

        if isinstance(target, dict):
            for entity_id in extract_entity_ids(target, "entity_id"):
                self._add_dependency(
                    graph, auto_entity_id, entity_id, NodeType.ENTITY, DependencyKind.ACTION
                )

            for device_id in as_list(target.get("device_id", [])):
                if not device_id:
                    continue

                self._add_dependency(
                    graph,
                    auto_entity_id,
                    f"device.{device_id}",
                    NodeType.DEVICE,
                    DependencyKind.DEVICE_ACTION,
                )

        for entity_id in extract_entity_ids(action, "entity_id"):
            self._add_dependency(
                graph, auto_entity_id, entity_id, NodeType.ENTITY, DependencyKind.ACTION
            )

        if isinstance(data, dict):
            for entity_id in extract_entity_ids(data, "entity_id"):
                self._add_dependency(
                    graph, auto_entity_id, entity_id, NodeType.ENTITY, DependencyKind.ACTION
                )

        if isinstance(service, str) and service.startswith("script."):
            self._add_dependency(
                graph, auto_entity_id, service, NodeType.SCRIPT, DependencyKind.SERVICE_CALL
            )

        if isinstance(service, str) and "scene" in service:
            scene_id = data.get("entity_id") if isinstance(data, dict) else None

            if isinstance(scene_id, str) and scene_id:
                self._add_dependency(
                    graph, auto_entity_id, scene_id, NodeType.SCENE, DependencyKind.SERVICE_CALL
                )

        for nested_action in iter_nested_actions(action):
            self._process_action(graph, auto_entity_id, nested_action)

    def _add_dependency(
        self,
        graph: DependencyGraph,
        source: str,
        target: str,
        node_type: NodeType,
        kind: DependencyKind,
        confidence: Confidence = Confidence.HIGH,
        notes: str = "",
    ) -> None:
        """Ensure the target node exists, then add the dependency edge."""
        self._ensure_placeholder(graph, target, node_type)

        graph.add_edge(
            GraphEdge(
                source=source,
                target=target,
                dependency_kind=kind,
                confidence=confidence,
                source_of_truth="automation_config",
                notes=notes,
            )
        )

    @staticmethod
    def _ensure_placeholder(graph: DependencyGraph, node_id: str, node_type: NodeType) -> None:
        """Ensure a node exists in the graph (placeholder if not from registry)."""
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


def _get_automation_store(hass: HomeAssistant) -> list[dict[str, Any]] | None:
    """Try to get automation configs from the automation component store."""
    try:
        component = hass.data.get("automation")

        if component is None:
            return None

        if hasattr(component, "async_items"):
            return [
                item.as_dict() if hasattr(item, "as_dict") else item
                for item in component.async_items()
            ]

        return None
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Could not access automation store, will use state fallback")
        return None
