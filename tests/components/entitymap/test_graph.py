"""Tests for EntityMap graph builder.

Scenarios cover initial state, build lifecycle, event firing,
concurrent scan protection, and serialization.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.entitymap.graph import GraphBuilder


class TestGraphBuilderInitialState:
    """Scenarios for a freshly created GraphBuilder."""

    @pytest.fixture
    def builder(self, mock_hass, mock_config_entry):
        """Create a graph builder."""
        return GraphBuilder(mock_hass, mock_config_entry)

    def test_starts_with_empty_graph(self, builder):
        """GIVEN a new GraphBuilder."""

        """THEN the graph has zero nodes and edges."""
        assert builder.graph.node_count == 0
        assert builder.graph.edge_count == 0

    def test_no_scan_has_occurred(self, builder):
        """GIVEN a new GraphBuilder."""

        """THEN last_scan is None and is_scanning is False."""
        assert builder.last_scan is None
        assert builder.is_scanning is False


class TestGraphBuilderBuild:
    """Scenarios for the async_build lifecycle."""

    @pytest.fixture
    def builder(self, mock_hass, mock_config_entry):
        return GraphBuilder(mock_hass, mock_config_entry)

    @pytest.mark.asyncio
    async def test_build_sets_last_scan_timestamp(self, builder):
        """GIVEN an empty builder."""

        """WHEN a build completes."""
        with patch(
            "custom_components.entitymap.adapters.registry.ar"
        ) as mock_ar, patch(
            "custom_components.entitymap.adapters.registry.dr"
        ) as mock_dr, patch(
            "custom_components.entitymap.adapters.registry.er"
        ) as mock_er:
            mock_ar.async_get.return_value.async_list_areas.return_value = []
            mock_dr.async_get.return_value.devices = {}
            mock_er.async_get.return_value.entities = {}

            await builder.async_build()

        """THEN last_scan is set and is_scanning returns to False."""
        assert builder.last_scan is not None
        assert builder.is_scanning is False

    @pytest.mark.asyncio
    async def test_build_fires_lifecycle_events(self, builder, mock_hass):
        """GIVEN a builder with a mocked hass."""

        """WHEN a build completes."""
        with patch(
            "custom_components.entitymap.adapters.registry.ar"
        ) as mock_ar, patch(
            "custom_components.entitymap.adapters.registry.dr"
        ) as mock_dr, patch(
            "custom_components.entitymap.adapters.registry.er"
        ) as mock_er:
            mock_ar.async_get.return_value.async_list_areas.return_value = []
            mock_dr.async_get.return_value.devices = {}
            mock_er.async_get.return_value.entities = {}

            await builder.async_build()

        """THEN scan_started, scan_completed, and graph_updated events are fired."""
        event_names = [
            call[0][0] for call in mock_hass.bus.async_fire.call_args_list
        ]
        assert "entitymap_scan_started" in event_names
        assert "entitymap_scan_completed" in event_names
        assert "entitymap_graph_updated" in event_names


class TestGraphBuilderSerialization:
    """Scenarios for graph data export."""

    @pytest.fixture
    def builder(self, mock_hass, mock_config_entry):
        return GraphBuilder(mock_hass, mock_config_entry)

    def test_get_graph_data_returns_expected_keys(self, builder):
        """GIVEN an empty builder."""

        """WHEN get_graph_data is called."""
        data = builder.get_graph_data()

        """THEN the result contains nodes, edges, and counts."""
        assert "nodes" in data
        assert "edges" in data
        assert data["node_count"] == 0
        assert data["edge_count"] == 0

    def test_graph_data_reflects_added_nodes(self, builder):
        """GIVEN a builder with manually added nodes."""
        from custom_components.entitymap.const import NodeType
        from custom_components.entitymap.models import GraphNode

        builder.graph.add_node(GraphNode("light.x", NodeType.ENTITY, "X"))

        """WHEN get_graph_data is called."""
        data = builder.get_graph_data()

        """THEN the serialized data includes those nodes."""
        assert data["node_count"] == 1
        assert data["nodes"][0]["node_id"] == "light.x"
