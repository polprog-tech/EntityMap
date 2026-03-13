"""Automation adapter — parse automation configs for dependency edges."""

from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.core import HomeAssistant

from ..const import Confidence, DependencyKind, NodeType
from ..models import DependencyGraph, GraphEdge, GraphNode
from .base import SourceAdapter

_LOGGER = logging.getLogger(__name__)

ENTITY_ID_PATTERN = re.compile(
    r"\b([a-z_]+\.[a-z0-9_]+)\b"
)


class AutomationAdapter(SourceAdapter):
    """Extract dependency edges from automation configurations."""

    async def async_populate(self, graph: DependencyGraph) -> None:
        """Scan automations and add edges to the graph."""
        states = self.hass.states.async_all("automation")
        component_data = self.hass.data.get("automation")

        configs: list[tuple[str, dict[str, Any]]] = []
        if component_data and hasattr(component_data, "async_get_automations"):
            # Prefer component API if available
            pass

        # Use the collection store if accessible
        store = _get_automation_store(self.hass)
        if store:
            for item in store:
                auto_id = item.get("id", "")
                entity_id = f"automation.{auto_id}"
                configs.append((entity_id, item))
        else:
            # Fallback: scan states and attributes
            for state in states:
                entity_id = state.entity_id
                attrs = dict(state.attributes)
                configs.append((entity_id, attrs))

        for entity_id, config in configs:
            self._process_automation(graph, entity_id, config)

    def _process_automation(
        self,
        graph: DependencyGraph,
        auto_entity_id: str,
        config: dict[str, Any],
    ) -> None:
        """Process a single automation config."""
        # Ensure automation node exists
        if auto_entity_id not in graph.nodes:
            graph.add_node(
                GraphNode(
                    node_id=auto_entity_id,
                    node_type=NodeType.AUTOMATION,
                    title=config.get("alias", auto_entity_id),
                    entity_id=auto_entity_id,
                )
            )

        # Triggers
        for trigger in _as_list(config.get("trigger", config.get("triggers", []))):
            self._process_trigger(graph, auto_entity_id, trigger)

        # Conditions
        for condition in _as_list(
            config.get("condition", config.get("conditions", []))
        ):
            self._process_condition(graph, auto_entity_id, condition)

        # Actions
        for action in _as_list(config.get("action", config.get("actions", []))):
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

        platform = trigger.get("platform", trigger.get("trigger", ""))

        # Device triggers
        device_id = trigger.get("device_id")
        if device_id:
            device_node_id = f"device.{device_id}"
            self._ensure_placeholder(graph, device_node_id, NodeType.DEVICE)
            graph.add_edge(
                GraphEdge(
                    source=auto_entity_id,
                    target=device_node_id,
                    dependency_kind=DependencyKind.DEVICE_TRIGGER,
                    confidence=Confidence.HIGH,
                    source_of_truth="automation_config",
                )
            )

        # Entity-based triggers
        for entity_id in _extract_entity_ids(trigger, "entity_id"):
            self._ensure_placeholder(graph, entity_id, NodeType.ENTITY)
            graph.add_edge(
                GraphEdge(
                    source=auto_entity_id,
                    target=entity_id,
                    dependency_kind=DependencyKind.TRIGGER,
                    confidence=Confidence.HIGH,
                    source_of_truth="automation_config",
                )
            )

        # Template triggers — extract entity references from templates
        if platform == "template":
            value_template = trigger.get("value_template", "")
            for ref in _extract_template_refs(str(value_template)):
                self._ensure_placeholder(graph, ref, NodeType.ENTITY)
                graph.add_edge(
                    GraphEdge(
                        source=auto_entity_id,
                        target=ref,
                        dependency_kind=DependencyKind.TEMPLATE_REFERENCE,
                        confidence=Confidence.MEDIUM,
                        source_of_truth="automation_config",
                        notes="Extracted from value_template",
                    )
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

        for entity_id in _extract_entity_ids(condition, "entity_id"):
            self._ensure_placeholder(graph, entity_id, NodeType.ENTITY)
            graph.add_edge(
                GraphEdge(
                    source=auto_entity_id,
                    target=entity_id,
                    dependency_kind=DependencyKind.CONDITION,
                    confidence=Confidence.HIGH,
                    source_of_truth="automation_config",
                )
            )

        device_id = condition.get("device_id")
        if device_id:
            device_node_id = f"device.{device_id}"
            self._ensure_placeholder(graph, device_node_id, NodeType.DEVICE)
            graph.add_edge(
                GraphEdge(
                    source=auto_entity_id,
                    target=device_node_id,
                    dependency_kind=DependencyKind.DEVICE_CONDITION,
                    confidence=Confidence.HIGH,
                    source_of_truth="automation_config",
                )
            )

        # Value template in conditions
        value_template = condition.get("value_template", "")
        if value_template:
            for ref in _extract_template_refs(str(value_template)):
                self._ensure_placeholder(graph, ref, NodeType.ENTITY)
                graph.add_edge(
                    GraphEdge(
                        source=auto_entity_id,
                        target=ref,
                        dependency_kind=DependencyKind.TEMPLATE_REFERENCE,
                        confidence=Confidence.MEDIUM,
                        source_of_truth="automation_config",
                    )
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

        # Service call targets
        service = action.get("service", action.get("action", ""))
        target = action.get("target", {})
        data = action.get("data", {})

        if isinstance(target, dict):
            for entity_id in _extract_entity_ids(target, "entity_id"):
                self._ensure_placeholder(graph, entity_id, NodeType.ENTITY)
                graph.add_edge(
                    GraphEdge(
                        source=auto_entity_id,
                        target=entity_id,
                        dependency_kind=DependencyKind.ACTION,
                        confidence=Confidence.HIGH,
                        source_of_truth="automation_config",
                    )
                )
            for device_id in _as_list(target.get("device_id", [])):
                if device_id:
                    device_node_id = f"device.{device_id}"
                    self._ensure_placeholder(graph, device_node_id, NodeType.DEVICE)
                    graph.add_edge(
                        GraphEdge(
                            source=auto_entity_id,
                            target=device_node_id,
                            dependency_kind=DependencyKind.DEVICE_ACTION,
                            confidence=Confidence.HIGH,
                            source_of_truth="automation_config",
                        )
                    )

        # entity_id directly in action (legacy format)
        for entity_id in _extract_entity_ids(action, "entity_id"):
            self._ensure_placeholder(graph, entity_id, NodeType.ENTITY)
            graph.add_edge(
                GraphEdge(
                    source=auto_entity_id,
                    target=entity_id,
                    dependency_kind=DependencyKind.ACTION,
                    confidence=Confidence.HIGH,
                    source_of_truth="automation_config",
                )
            )

        # entity_id in data
        if isinstance(data, dict):
            for entity_id in _extract_entity_ids(data, "entity_id"):
                self._ensure_placeholder(graph, entity_id, NodeType.ENTITY)
                graph.add_edge(
                    GraphEdge(
                        source=auto_entity_id,
                        target=entity_id,
                        dependency_kind=DependencyKind.ACTION,
                        confidence=Confidence.HIGH,
                        source_of_truth="automation_config",
                    )
                )

        # Script calls
        if isinstance(service, str) and service.startswith("script."):
            script_entity = service
            self._ensure_placeholder(graph, script_entity, NodeType.SCRIPT)
            graph.add_edge(
                GraphEdge(
                    source=auto_entity_id,
                    target=script_entity,
                    dependency_kind=DependencyKind.SERVICE_CALL,
                    confidence=Confidence.HIGH,
                    source_of_truth="automation_config",
                )
            )

        # Scene activation
        if isinstance(service, str) and "scene" in service:
            scene_id = data.get("entity_id") if isinstance(data, dict) else None
            if scene_id and isinstance(scene_id, str):
                self._ensure_placeholder(graph, scene_id, NodeType.SCENE)
                graph.add_edge(
                    GraphEdge(
                        source=auto_entity_id,
                        target=scene_id,
                        dependency_kind=DependencyKind.SERVICE_CALL,
                        confidence=Confidence.HIGH,
                        source_of_truth="automation_config",
                    )
                )

        # Nested actions (choose, if, repeat)
        for key in ("choose", "sequence", "default", "then", "else"):
            nested = action.get(key)
            if isinstance(nested, list):
                for item in nested:
                    if isinstance(item, dict):
                        if "sequence" in item:
                            for sub in _as_list(item["sequence"]):
                                self._process_action(graph, auto_entity_id, sub)
                        else:
                            self._process_action(graph, auto_entity_id, item)

        if "repeat" in action and isinstance(action["repeat"], dict):
            for sub in _as_list(action["repeat"].get("sequence", [])):
                self._process_action(graph, auto_entity_id, sub)

    @staticmethod
    def _ensure_placeholder(
        graph: DependencyGraph, node_id: str, node_type: NodeType
    ) -> None:
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
        # The automation component stores configs in its collection
        if hasattr(component, "async_items"):
            return [
                item.as_dict() if hasattr(item, "as_dict") else item
                for item in component.async_items()
            ]
        return None
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Could not access automation store, will use state fallback")
        return None


def _as_list(value: Any) -> list[Any]:
    """Ensure a value is a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _extract_entity_ids(data: dict[str, Any], key: str = "entity_id") -> list[str]:
    """Extract entity IDs from a config dict."""
    value = data.get(key)
    if value is None:
        return []
    if isinstance(value, str):
        # Could be comma-separated or single
        return [v.strip() for v in value.split(",") if "." in v.strip()]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str) and "." in v]
    return []


def _extract_template_refs(template_str: str) -> list[str]:
    """Extract entity references from a Jinja2 template string."""
    refs: list[str] = []
    # states('entity_id') or states.entity_id or is_state('entity_id', ...)
    patterns = [
        re.compile(r"states\(\s*['\"]([a-z_]+\.[a-z0-9_]+)['\"]\s*\)"),
        re.compile(r"states\.([a-z_]+\.[a-z0-9_]+)"),
        re.compile(r"is_state\(\s*['\"]([a-z_]+\.[a-z0-9_]+)['\"]"),
        re.compile(r"state_attr\(\s*['\"]([a-z_]+\.[a-z0-9_]+)['\"]"),
    ]
    for pattern in patterns:
        refs.extend(pattern.findall(template_str))
    return list(set(refs))
