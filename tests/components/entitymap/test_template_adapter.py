"""Tests for the template source adapter.

Scenarios cover extracting references from a UI template helper's config
entry, the various supported template functions, the self-reference guard,
and the documented gap for YAML template entities.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from custom_components.entitymap.adapters.template import TemplateAdapter
from custom_components.entitymap.const import DependencyKind
from custom_components.entitymap.models import DependencyGraph


def _template_entity(entity_id, config_entry_id):
    """A registry entry for a template-platform entity."""
    return SimpleNamespace(
        entity_id=entity_id,
        platform="template",
        config_entry_id=config_entry_id,
    )


async def _populate(mock_hass, entities, entry):
    """Run the adapter against a mocked registry and config entry."""
    graph = DependencyGraph()
    registry = MagicMock()
    registry.entities = entities
    mock_hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    with patch("custom_components.entitymap.adapters.template.er") as mock_er:
        mock_er.async_get.return_value = registry
        await TemplateAdapter(mock_hass).async_populate(graph)

    return graph


class TestTemplateAdapter:
    """Scenarios for resolving template entity references."""

    @pytest.mark.asyncio
    async def test_extracts_refs_from_helper_config_entry(self, mock_hass):
        """GIVEN a UI template helper whose state template references entities.

        WHEN the adapter runs.

        THEN it links the template entity to each referenced entity.
        """
        entities = {"sensor.my_template": _template_entity("sensor.my_template", "ce1")}
        entry = SimpleNamespace(
            domain="template",
            options={
                "state": "{{ states('sensor.source') | float }}",
                "availability": "{{ has_value('binary_sensor.gate') }}",
            },
            data={},
        )

        graph = await _populate(mock_hass, entities, entry)

        targets = {e.target for e in graph.edges if e.source == "sensor.my_template"}
        assert targets == {"sensor.source", "binary_sensor.gate"}
        assert all(
            e.dependency_kind == DependencyKind.TEMPLATE_REFERENCE for e in graph.edges
        )

    @pytest.mark.asyncio
    async def test_supports_multiple_template_functions(self, mock_hass):
        """GIVEN a template using states(), is_state(), state_attr() and expand().

        WHEN the adapter runs.

        THEN every referenced entity is captured.
        """
        entities = {"sensor.combo": _template_entity("sensor.combo", "ce1")}
        entry = SimpleNamespace(
            domain="template",
            options={
                "state": (
                    "{% if is_state('light.kitchen', 'on') %}"
                    "{{ state_attr('climate.house', 'temperature') }}"
                    "{{ expand('group.lights') | list }}{% endif %}"
                ),
            },
            data={},
        )

        graph = await _populate(mock_hass, entities, entry)

        targets = {e.target for e in graph.edges}
        assert targets == {"light.kitchen", "climate.house", "group.lights"}

    @pytest.mark.asyncio
    async def test_self_reference_is_ignored(self, mock_hass):
        """GIVEN a template that references itself.

        WHEN the adapter runs.

        THEN no self-edge is created.
        """
        entities = {"sensor.loop": _template_entity("sensor.loop", "ce1")}
        entry = SimpleNamespace(
            domain="template",
            options={"state": "{{ states('sensor.loop') }}"},
            data={},
        )

        graph = await _populate(mock_hass, entities, entry)

        assert graph.edge_count == 0

    @pytest.mark.asyncio
    async def test_yaml_template_without_config_entry_is_skipped(self, mock_hass):
        """GIVEN a YAML template entity that has no config entry.

        WHEN the adapter runs.

        THEN it is skipped (its source is not exposed at runtime).
        """
        entities = {"sensor.yaml_tpl": _template_entity("sensor.yaml_tpl", None)}

        graph = await _populate(mock_hass, entities, entry=None)

        assert graph.edge_count == 0
