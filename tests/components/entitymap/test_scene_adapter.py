"""Characterization tests for the scene source adapter.

Pins the scene-member edges extracted from both the entities-dict and the
entity_id-list config shapes, including the non-entity skip rule.
"""

from __future__ import annotations

import pytest

from custom_components.entitymap.adapters.scene import SceneAdapter
from custom_components.entitymap.models import DependencyGraph


class _Store:
    """Minimal stand-in for the scene collection store."""

    def __init__(self, items):
        self._items = items

    def async_items(self):
        return self._items


_CONFIG = {
    "id": "movie",
    "name": "Movie",
    "entities": {"light.l": {"state": "on"}, "invalid": {}},
    "entity_id": ["switch.w", "bad", "media_player.m"],
}

_EXPECTED_EDGES = {
    ("scene.movie", "light.l", "scene_member"),
    ("scene.movie", "switch.w", "scene_member"),
    ("scene.movie", "media_player.m", "scene_member"),
}


@pytest.mark.asyncio
async def test_extracts_scene_members(mock_hass):
    """GIVEN a scene defined with both an entities dict and an entity_id list.

    WHEN the adapter populates the graph.

    THEN every valid member becomes a scene_member edge and non-entities are skipped.
    """
    mock_hass.data = {"scene": _Store([_CONFIG])}
    graph = DependencyGraph()

    await SceneAdapter(mock_hass).async_populate(graph)

    edges = {(e.source, e.target, e.dependency_kind.value) for e in graph.edges}
    assert edges == _EXPECTED_EDGES
    assert graph.nodes["scene.movie"].title == "Movie"
