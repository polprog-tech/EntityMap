"""Characterization tests for the automation source adapter.

These pin the full set of dependency edges extracted from an automation config
(triggers, conditions, actions, nested choose/repeat, templates) so the parser
can be refactored without changing behavior.
"""

from __future__ import annotations

import pytest

from custom_components.entitymap.adapters.automation import AutomationAdapter
from custom_components.entitymap.models import DependencyGraph


class _Store:
    """Minimal stand-in for the automation collection store."""

    def __init__(self, items):
        self._items = items

    def async_items(self):
        return self._items


_CONFIG = {
    "id": "test",
    "alias": "Test Auto",
    "trigger": [
        {"platform": "device", "device_id": "dev1"},
        {"platform": "state", "entity_id": "sensor.a"},
        {"platform": "template", "value_template": "{{ states('sensor.tmpl') }}"},
    ],
    "condition": [
        {"condition": "state", "entity_id": "binary_sensor.c"},
        {"condition": "device", "device_id": "dev2"},
        {"condition": "template", "value_template": "{{ is_state('sensor.cond', 'on') }}"},
    ],
    "action": [
        {"service": "light.turn_on", "target": {"entity_id": "light.l", "device_id": "dev3"}},
        {"service": "script.my_script"},
        {"service": "scene.turn_on", "data": {"entity_id": "scene.s"}},
        {"choose": [{"sequence": [{"service": "switch.turn_on", "target": {"entity_id": "switch.w"}}]}]},
        {"repeat": {"sequence": [{"service": "fan.turn_on", "target": {"entity_id": "fan.f"}}]}},
        {"service": "light.toggle", "entity_id": "light.legacy"},
        {"service": "input_boolean.turn_on", "data": {"entity_id": "input_boolean.d"}},
    ],
}

_EXPECTED_EDGES = {
    ("automation.test", "device.dev1", "device_trigger"),
    ("automation.test", "sensor.a", "trigger"),
    ("automation.test", "sensor.tmpl", "template_reference"),
    ("automation.test", "binary_sensor.c", "condition"),
    ("automation.test", "device.dev2", "device_condition"),
    ("automation.test", "sensor.cond", "template_reference"),
    ("automation.test", "light.l", "action"),
    ("automation.test", "device.dev3", "device_action"),
    ("automation.test", "script.my_script", "service_call"),
    ("automation.test", "scene.s", "service_call"),
    ("automation.test", "scene.s", "action"),
    ("automation.test", "switch.w", "action"),
    ("automation.test", "fan.f", "action"),
    ("automation.test", "light.legacy", "action"),
    ("automation.test", "input_boolean.d", "action"),
}


@pytest.mark.asyncio
async def test_extracts_all_dependency_edges(mock_hass):
    """GIVEN an automation exercising every supported config shape.

    WHEN the adapter populates the graph.

    THEN the full set of dependency edges is produced and the node is named.
    """
    mock_hass.data = {"automation": _Store([_CONFIG])}
    graph = DependencyGraph()

    await AutomationAdapter(mock_hass).async_populate(graph)

    edges = {(e.source, e.target, e.dependency_kind.value) for e in graph.edges}
    assert edges == _EXPECTED_EDGES
    assert graph.nodes["automation.test"].title == "Test Auto"
