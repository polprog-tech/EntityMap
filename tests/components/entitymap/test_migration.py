"""Tests for the EntityMap migration suggestion engine.

Scenarios organized by migration context: nonexistent nodes,
no-dependency entities, trigger/condition/action migrations,
device replacement, scene/group members, and target-specified migrations.
"""

from __future__ import annotations

from custom_components.entitymap.const import DependencyKind, NodeType
from custom_components.entitymap.migration import get_migration_report
from custom_components.entitymap.models import (
    DependencyGraph,
    GraphEdge,
    GraphNode,
)


class TestMigrationForNonexistentNode:
    """Scenarios where the source node doesn't exist."""

    def test_returns_not_found_message(self, empty_graph):
        """GIVEN an empty graph."""

        """WHEN requesting migration for a nonexistent node."""
        result = get_migration_report(empty_graph, "nonexistent.node")

        """THEN the result contains a 'not found' message."""
        assert len(result) == 1
        assert "not found" in result[0].description


class TestMigrationForIsolatedNode:
    """Scenarios where the node has no inbound dependencies."""

    def test_indicates_safe_removal(self):
        """GIVEN an entity with no inbound edges."""
        graph = DependencyGraph()
        graph.add_node(GraphNode("light.test", NodeType.ENTITY, "Test"))

        """WHEN requesting migration."""
        result = get_migration_report(graph, "light.test")

        """THEN the suggestion says it can be removed without impact."""
        assert len(result) == 1
        assert "no inbound" in result[0].description.lower()


class TestMigrationForTriggerDependency:
    """Scenarios for entities used as automation triggers."""

    def test_generates_trigger_migration_suggestion(self):
        """GIVEN an entity used as a trigger by one automation."""
        graph = DependencyGraph()
        graph.add_node(GraphNode("light.test", NodeType.ENTITY, "Test"))
        graph.add_node(GraphNode("automation.a", NodeType.AUTOMATION, "Auto A"))
        graph.add_edge(GraphEdge("automation.a", "light.test", DependencyKind.TRIGGER))

        """WHEN requesting migration."""
        result = get_migration_report(graph, "light.test")

        """THEN a trigger-specific suggestion is produced."""
        trigger_suggestions = [s for s in result if "trigger" in s.description.lower()]
        assert len(trigger_suggestions) == 1

    def test_includes_target_entity_when_specified(self):
        """GIVEN a migration from old to new entity."""
        graph = DependencyGraph()
        graph.add_node(GraphNode("light.old", NodeType.ENTITY, "Old Light"))
        graph.add_node(GraphNode("automation.a", NodeType.AUTOMATION, "Auto"))
        graph.add_edge(GraphEdge("automation.a", "light.old", DependencyKind.TRIGGER))

        """WHEN a target_node_id is provided."""
        result = get_migration_report(graph, "light.old", "light.new")

        """THEN the recommendation references the new entity."""
        trigger_suggestions = [s for s in result if "trigger" in s.description.lower()]
        assert len(trigger_suggestions) == 1
        assert "light.new" in trigger_suggestions[0].recommendation


class TestMigrationForDeviceReplacement:
    """Scenarios for device replacement migrations."""

    def test_device_with_device_id_refs_warns(self):
        """GIVEN a device with device_id references from automations."""
        graph = DependencyGraph()
        graph.add_node(GraphNode("device.sensor1", NodeType.DEVICE, "Sensor 1"))
        graph.add_node(
            GraphNode("binary_sensor.motion", NodeType.ENTITY, "Motion", device_id="sensor1")
        )
        graph.add_node(GraphNode("automation.test", NodeType.AUTOMATION, "Test"))
        graph.add_edge(
            GraphEdge("binary_sensor.motion", "device.sensor1", DependencyKind.ENTITY_OF_DEVICE)
        )
        graph.add_edge(
            GraphEdge("automation.test", "device.sensor1", DependencyKind.DEVICE_TRIGGER)
        )

        """WHEN requesting migration."""
        result = get_migration_report(graph, "device.sensor1")

        """THEN device_id warnings are produced."""
        assert len(result) >= 2
        device_ref_suggestions = [s for s in result if "device_id" in s.description.lower()]
        assert len(device_ref_suggestions) >= 1

    def test_device_with_entities_lists_entity_mapping(self):
        """GIVEN a device that provides entities."""
        graph = DependencyGraph()
        graph.add_node(GraphNode("device.hub", NodeType.DEVICE, "Hub"))
        graph.add_node(GraphNode("sensor.temp", NodeType.ENTITY, "Temp", device_id="hub"))
        graph.add_node(GraphNode("sensor.humid", NodeType.ENTITY, "Humidity", device_id="hub"))
        graph.add_edge(GraphEdge("sensor.temp", "device.hub", DependencyKind.ENTITY_OF_DEVICE))
        graph.add_edge(GraphEdge("sensor.humid", "device.hub", DependencyKind.ENTITY_OF_DEVICE))

        """WHEN requesting migration."""
        result = get_migration_report(graph, "device.hub")

        """THEN entity mapping guidance is included."""
        entity_suggestions = [s for s in result if "entity" in s.description.lower()]
        assert len(entity_suggestions) >= 1


class TestMigrationForSceneMembers:
    """Scenarios for entities that are scene members."""

    def test_scene_member_migration(self):
        """GIVEN an entity that's a member of a scene."""
        graph = DependencyGraph()
        graph.add_node(GraphNode("light.test", NodeType.ENTITY, "Test"))
        graph.add_node(GraphNode("scene.evening", NodeType.SCENE, "Evening"))
        graph.add_edge(GraphEdge("scene.evening", "light.test", DependencyKind.SCENE_MEMBER))

        """WHEN requesting migration."""
        result = get_migration_report(graph, "light.test")

        """THEN a scene-specific suggestion is produced."""
        scene_suggestions = [s for s in result if "scene" in s.description.lower()]
        assert len(scene_suggestions) == 1


class TestMigrationForGroupMembers:
    """Scenarios for entities that are group members."""

    def test_group_member_migration(self):
        """GIVEN an entity that's a member of a group."""
        graph = DependencyGraph()
        graph.add_node(GraphNode("light.test", NodeType.ENTITY, "Test"))
        graph.add_node(GraphNode("group.all_lights", NodeType.GROUP, "All Lights"))
        graph.add_edge(GraphEdge("group.all_lights", "light.test", DependencyKind.GROUP_MEMBER))

        """WHEN requesting migration."""
        result = get_migration_report(graph, "light.test")

        """THEN a group-specific suggestion is produced."""
        group_suggestions = [s for s in result if "group" in s.description.lower()]
        assert len(group_suggestions) == 1


class TestMigrationForMultipleDependencies:
    """Scenarios where an entity has many dependency types."""

    def test_entity_with_trigger_and_scene_produces_both(self):
        """GIVEN an entity used as a trigger AND a scene member."""
        graph = DependencyGraph()
        graph.add_node(GraphNode("light.multi", NodeType.ENTITY, "Multi"))
        graph.add_node(GraphNode("automation.a", NodeType.AUTOMATION, "Auto"))
        graph.add_node(GraphNode("scene.cozy", NodeType.SCENE, "Cozy"))
        graph.add_edge(GraphEdge("automation.a", "light.multi", DependencyKind.TRIGGER))
        graph.add_edge(GraphEdge("scene.cozy", "light.multi", DependencyKind.SCENE_MEMBER))

        """WHEN requesting migration."""
        result = get_migration_report(graph, "light.multi")

        """THEN suggestions for both contexts are produced."""
        trigger_sugs = [s for s in result if "trigger" in s.description.lower()]
        scene_sugs = [s for s in result if "scene" in s.description.lower()]
        assert len(trigger_sugs) >= 1
        assert len(scene_sugs) >= 1
