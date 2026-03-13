"""Group adapter — parse group membership for dependency edges."""

from __future__ import annotations

import logging

from ..const import Confidence, DependencyKind, NodeType
from ..models import DependencyGraph, GraphEdge, GraphNode
from .base import SourceAdapter

_LOGGER = logging.getLogger(__name__)


class GroupAdapter(SourceAdapter):
    """Extract dependency edges from group configurations."""

    async def async_populate(self, graph: DependencyGraph) -> None:
        """Scan groups and add edges to the graph."""
        states = self.hass.states.async_all("group")

        for state in states:
            group_entity_id = state.entity_id
            members = state.attributes.get("entity_id", [])

            if group_entity_id not in graph.nodes:
                graph.add_node(
                    GraphNode(
                        node_id=group_entity_id,
                        node_type=NodeType.GROUP,
                        title=state.attributes.get("friendly_name", group_entity_id),
                        entity_id=group_entity_id,
                    )
                )

            if not isinstance(members, list):
                continue

            for member_id in members:
                if not isinstance(member_id, str) or "." not in member_id:
                    continue
                if member_id not in graph.nodes:
                    graph.add_node(
                        GraphNode(
                            node_id=member_id,
                            node_type=_guess_type(member_id),
                            title=member_id,
                            entity_id=member_id,
                            available=False,
                        )
                    )
                graph.add_edge(
                    GraphEdge(
                        source=group_entity_id,
                        target=member_id,
                        dependency_kind=DependencyKind.GROUP_MEMBER,
                        confidence=Confidence.HIGH,
                        source_of_truth="group_state",
                    )
                )


def _guess_type(entity_id: str) -> NodeType:
    """Guess the node type from the entity ID domain."""
    domain = entity_id.split(".")[0] if "." in entity_id else ""
    type_map: dict[str, NodeType] = {
        "automation": NodeType.AUTOMATION,
        "script": NodeType.SCRIPT,
        "scene": NodeType.SCENE,
        "group": NodeType.GROUP,
    }
    return type_map.get(domain, NodeType.ENTITY)
