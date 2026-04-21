"""Scene adapter - parse scene configs for dependency edges."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from ..const import Confidence, DependencyKind, NodeType
from ..models import DependencyGraph, GraphEdge, GraphNode
from .base import SourceAdapter

_LOGGER = logging.getLogger(__name__)


class SceneAdapter(SourceAdapter):
    """Extract dependency edges from scene configurations."""

    async def async_populate(self, graph: DependencyGraph) -> None:
        """Scan scenes and add edges to the graph."""
        states = self.hass.states.async_all("scene")
        store = _get_scene_store(self.hass)

        configs: list[tuple[str, dict[str, Any]]] = []
        if store:
            for item in store:
                scene_id = item.get("id", "")
                entity_id = f"scene.{scene_id}"
                configs.append((entity_id, item))
        else:
            for state in states:
                configs.append((state.entity_id, dict(state.attributes)))

        for entity_id, config in configs:
            self._process_scene(graph, entity_id, config)

    def _process_scene(
        self,
        graph: DependencyGraph,
        scene_entity_id: str,
        config: dict[str, Any],
    ) -> None:
        """Process a single scene config."""
        if scene_entity_id not in graph.nodes:
            graph.add_node(
                GraphNode(
                    node_id=scene_entity_id,
                    node_type=NodeType.SCENE,
                    title=config.get("name", scene_entity_id),
                    entity_id=scene_entity_id,
                )
            )

        # Scene entities (the states to be set)
        entities = config.get("entities", {})
        if isinstance(entities, dict):
            for member_entity_id in entities:
                if not isinstance(member_entity_id, str) or "." not in member_entity_id:
                    continue
                if member_entity_id not in graph.nodes:
                    graph.add_node(
                        GraphNode(
                            node_id=member_entity_id,
                            node_type=NodeType.ENTITY,
                            title=member_entity_id,
                            entity_id=member_entity_id,
                            available=False,
                        )
                    )
                graph.add_edge(
                    GraphEdge(
                        source=scene_entity_id,
                        target=member_entity_id,
                        dependency_kind=DependencyKind.SCENE_MEMBER,
                        confidence=Confidence.HIGH,
                        source_of_truth="scene_config",
                    )
                )

        # Also check entity_id list format
        entity_ids = config.get("entity_id", [])
        if isinstance(entity_ids, list):
            for member_id in entity_ids:
                if isinstance(member_id, str) and "." in member_id:
                    if member_id not in graph.nodes:
                        graph.add_node(
                            GraphNode(
                                node_id=member_id,
                                node_type=NodeType.ENTITY,
                                title=member_id,
                                entity_id=member_id,
                                available=False,
                            )
                        )
                    graph.add_edge(
                        GraphEdge(
                            source=scene_entity_id,
                            target=member_id,
                            dependency_kind=DependencyKind.SCENE_MEMBER,
                            confidence=Confidence.HIGH,
                            source_of_truth="scene_config",
                        )
                    )


def _get_scene_store(hass: HomeAssistant) -> list[dict[str, Any]] | None:
    """Try to get scene configs from HA store."""
    try:
        component = hass.data.get("scene")
        if component is None:
            return None
        if hasattr(component, "async_items"):
            return [
                item.as_dict() if hasattr(item, "as_dict") else item
                for item in component.async_items()
            ]
        return None
    except Exception:  # noqa: BLE001
        _LOGGER.debug("Could not access scene store")
        return None
