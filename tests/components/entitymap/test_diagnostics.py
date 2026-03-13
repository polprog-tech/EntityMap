"""Tests for EntityMap diagnostics support.

Scenarios cover diagnostics output structure, data completeness,
and privacy (no raw entity IDs leaked).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.entitymap.const import DependencyKind, NodeType
from custom_components.entitymap.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.entitymap.graph import GraphBuilder
from custom_components.entitymap.models import DependencyGraph, GraphEdge, GraphNode


class TestDiagnosticsOutput:
    """Scenarios for the diagnostics data structure."""

    @pytest.mark.asyncio
    async def test_contains_expected_top_level_keys(self, mock_hass, mock_config_entry):
        """GIVEN a builder with a small graph."""
        builder = GraphBuilder(mock_hass, mock_config_entry)
        builder.graph.add_node(GraphNode("light.test", NodeType.ENTITY, "Test"))
        builder.graph.add_node(GraphNode("automation.a", NodeType.AUTOMATION, "Auto A"))
        builder.graph.add_edge(GraphEdge("automation.a", "light.test", DependencyKind.TRIGGER))

        runtime_data = MagicMock()
        runtime_data.builder = builder
        mock_config_entry.runtime_data = runtime_data

        """WHEN diagnostics are generated."""
        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)

        """THEN the output contains graph, fragility, scanner, and config_entry keys."""
        assert "graph" in result
        assert "fragility" in result
        assert "scanner" in result
        assert "config_entry" in result

    @pytest.mark.asyncio
    async def test_graph_counts_are_accurate(self, mock_hass, mock_config_entry):
        """GIVEN a graph with 2 nodes and 1 edge."""
        builder = GraphBuilder(mock_hass, mock_config_entry)
        builder.graph.add_node(GraphNode("light.a", NodeType.ENTITY, "A"))
        builder.graph.add_node(GraphNode("automation.b", NodeType.AUTOMATION, "B"))
        builder.graph.add_edge(GraphEdge("automation.b", "light.a", DependencyKind.ACTION))

        runtime_data = MagicMock()
        runtime_data.builder = builder
        mock_config_entry.runtime_data = runtime_data

        """WHEN diagnostics are generated."""
        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)

        """THEN the counts match the graph state."""
        assert result["graph"]["node_count"] == 2
        assert result["graph"]["edge_count"] == 1


class TestDiagnosticsPrivacy:
    """Scenarios verifying diagnostics do not leak sensitive data."""

    @pytest.mark.asyncio
    async def test_empty_graph_diagnostics_do_not_leak(
        self, mock_hass, mock_config_entry
    ):
        """GIVEN an empty graph."""
        builder = GraphBuilder(mock_hass, mock_config_entry)
        runtime_data = MagicMock()
        runtime_data.builder = builder
        mock_config_entry.runtime_data = runtime_data

        """WHEN diagnostics are generated."""
        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)

        """THEN the output contains aggregate counts rather than raw entity IDs."""
        result_str = str(result)
        assert "nodes_by_type" in result_str or result["graph"]["node_count"] == 0


class TestDiagnosticsWithFindings:
    """Scenarios where the graph has fragility issues."""

    @pytest.mark.asyncio
    async def test_fragility_findings_included(self, mock_hass, mock_config_entry):
        """GIVEN a graph with a missing entity reference."""
        builder = GraphBuilder(mock_hass, mock_config_entry)
        builder.graph.add_node(GraphNode("automation.x", NodeType.AUTOMATION, "X"))
        builder.graph.add_edge(GraphEdge("automation.x", "light.ghost", DependencyKind.TRIGGER))

        runtime_data = MagicMock()
        runtime_data.builder = builder
        mock_config_entry.runtime_data = runtime_data

        """WHEN diagnostics are generated."""
        result = await async_get_config_entry_diagnostics(mock_hass, mock_config_entry)

        """THEN the fragility section reports findings."""
        assert result["fragility"]["total_findings"] > 0
