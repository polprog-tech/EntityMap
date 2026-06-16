"""Characterization tests for the script source adapter.

Pins the dependency edges extracted from a script config (action targets,
device targets, legacy entity_id, data entity_id, script calls, template
references, nested choose/repeat) so the parser can be refactored safely.
"""

from __future__ import annotations

import pytest

from custom_components.entitymap.adapters.script import ScriptAdapter
from custom_components.entitymap.models import DependencyGraph


class _Store:
    """Minimal stand-in for the script collection store."""

    def __init__(self, items):
        self._items = items

    def async_items(self):
        return self._items


_CONFIG = {
    "id": "my",
    "alias": "My Script",
    "sequence": [
        {"service": "light.turn_on", "target": {"entity_id": "light.l", "device_id": "dev1"}},
        {"service": "switch.toggle", "entity_id": "switch.legacy"},
        {"service": "fan.turn_on", "data": {"entity_id": "fan.d"}},
        {"service": "script.other"},
        {"service": "notify.x", "data": {"message": "{{ states('sensor.tmpl') }}"}},
        {"choose": [{"sequence": [{"service": "lock.lock", "target": {"entity_id": "lock.k"}}]}]},
        {"repeat": {"sequence": [{"service": "cover.open", "target": {"entity_id": "cover.c"}}]}},
    ],
}

_EXPECTED_EDGES = {
    ("script.my", "light.l", "action"),
    ("script.my", "device.dev1", "device_action"),
    ("script.my", "switch.legacy", "action"),
    ("script.my", "fan.d", "action"),
    ("script.my", "script.other", "service_call"),
    ("script.my", "sensor.tmpl", "template_reference"),
    ("script.my", "lock.k", "action"),
    ("script.my", "cover.c", "action"),
}


@pytest.mark.asyncio
async def test_extracts_all_dependency_edges(mock_hass):
    """GIVEN a script exercising every supported action shape.

    WHEN the adapter populates the graph.

    THEN the full set of dependency edges is produced and the node is named.
    """
    mock_hass.data = {"script": _Store([_CONFIG])}
    graph = DependencyGraph()

    await ScriptAdapter(mock_hass).async_populate(graph)

    edges = {(e.source, e.target, e.dependency_kind.value) for e in graph.edges}
    assert edges == _EXPECTED_EDGES
    assert graph.nodes["script.my"].title == "My Script"
