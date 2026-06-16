"""Tests for the area -> device -> entity hierarchy builder.

Scenarios cover device-to-area bucketing, direct area entities, and the
unassigned device/entity buckets, guarding the single-pass grouping.
"""

from __future__ import annotations

from custom_components.entitymap.const import NodeType
from custom_components.entitymap.hierarchy import build_hierarchy
from custom_components.entitymap.models import DependencyGraph, GraphNode


def _graph() -> DependencyGraph:
    """An area with a device + its entity, plus unassigned device and entity."""
    graph = DependencyGraph()
    graph.add_node(GraphNode("area.kitchen", NodeType.AREA, "Kitchen", area_id="kitchen"))
    graph.add_node(
        GraphNode("device.oven", NodeType.DEVICE, "Oven", device_id="oven", area_id="kitchen")
    )
    graph.add_node(
        GraphNode("sensor.oven_temp", NodeType.ENTITY, "Oven Temp", device_id="oven")
    )
    graph.add_node(
        GraphNode("light.strip", NodeType.ENTITY, "Strip", area_id="kitchen")
    )
    graph.add_node(GraphNode("device.orphan", NodeType.DEVICE, "Orphan", device_id="orphan"))
    graph.add_node(GraphNode("sensor.floating", NodeType.ENTITY, "Floating"))

    return graph


class TestBuildHierarchy:
    """Scenarios for the hierarchy tree structure."""

    def test_device_and_direct_entity_attach_to_area(self):
        """GIVEN an area with a device (carrying an entity) and a direct entity.

        WHEN the hierarchy is built.

        THEN the area holds the device and the direct entity, and the device
        carries its own entity.
        """
        result = build_hierarchy(_graph())

        assert len(result["areas"]) == 1
        area = result["areas"][0]
        assert area["title"] == "Kitchen"
        assert [d["node_id"] for d in area["devices"]] == ["device.oven"]
        assert [e["node_id"] for e in area["entities"]] == ["light.strip"]
        assert [e["node_id"] for e in area["devices"][0]["entities"]] == ["sensor.oven_temp"]

    def test_counts_include_devices_direct_and_nested_entities(self):
        """GIVEN the same graph.

        WHEN the hierarchy is built.

        THEN the area counts cover the device, the direct entity, and the
        device's nested entity.
        """
        area = build_hierarchy(_graph())["areas"][0]

        assert area["device_count"] == 1
        assert area["entity_count"] == 3

    def test_unassigned_buckets(self):
        """GIVEN a device and an entity with no area.

        WHEN the hierarchy is built.

        THEN they land in the unassigned buckets, not under any area.
        """
        result = build_hierarchy(_graph())

        assert [d["node_id"] for d in result["unassigned_devices"]] == ["device.orphan"]
        assert [e["node_id"] for e in result["unassigned_entities"]] == ["sensor.floating"]

    def test_empty_graph_yields_empty_tree(self):
        """GIVEN an empty graph.

        WHEN the hierarchy is built.

        THEN every bucket is empty.
        """
        result = build_hierarchy(DependencyGraph())

        assert result == {"areas": [], "unassigned_devices": [], "unassigned_entities": []}
