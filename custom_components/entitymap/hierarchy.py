"""Area -> device -> entity hierarchy tree for the frontend panel."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .const import NodeType

if TYPE_CHECKING:
    from .models import DependencyGraph

_ENTITY_NODE_TYPES = (
    NodeType.ENTITY,
    NodeType.AUTOMATION,
    NodeType.SCRIPT,
    NodeType.SCENE,
    NodeType.HELPER,
    NodeType.GROUP,
)


def build_hierarchy(graph: DependencyGraph) -> dict[str, Any]:
    """Build an area -> device -> entity tree.

    Returns areas (each with its devices and direct entities), plus the
    devices and entities that belong to no area.
    """
    areas = _collect_areas(graph)
    devices = _collect_devices(graph)
    entities_by_area, unassigned_entities = _distribute_entities(graph, areas, devices)
    devices_by_area, unassigned_devices = _group_devices_by_area(devices, areas)
    result_areas = _assemble_areas(areas, devices_by_area, entities_by_area)

    return {
        "areas": result_areas,
        "unassigned_devices": unassigned_devices,
        "unassigned_entities": unassigned_entities,
    }


def _collect_areas(graph: DependencyGraph) -> dict[str, dict[str, Any]]:
    """Index area nodes by area id."""
    areas: dict[str, dict[str, Any]] = {}

    for node in graph.nodes.values():
        if node.node_type != NodeType.AREA:
            continue

        areas[node.area_id or node.node_id.removeprefix("area.")] = {
            "node_id": node.node_id,
            "title": node.title,
            "node_type": node.node_type.value,
            "devices": [],
            "entities": [],
        }

    return areas


def _collect_devices(graph: DependencyGraph) -> dict[str, dict[str, Any]]:
    """Index device nodes by device id."""
    devices: dict[str, dict[str, Any]] = {}

    for node in graph.nodes.values():
        if node.node_type != NodeType.DEVICE:
            continue

        devices[node.device_id or node.node_id.removeprefix("device.")] = {
            "node_id": node.node_id,
            "title": node.title,
            "node_type": node.node_type.value,
            "area_id": node.area_id,
            "disabled": node.disabled,
            "available": node.available,
            "metadata": node.metadata,
            "entities": [],
        }

    return devices


def _distribute_entities(
    graph: DependencyGraph,
    areas: dict[str, dict[str, Any]],
    devices: dict[str, dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Attach each entity to its device or area; the rest are unassigned.

    Entities nested under a device are stored in place; area-level entities
    are returned keyed by area, and orphans land in the unassigned list.
    """
    entities_by_area: dict[str, list[dict[str, Any]]] = {}
    unassigned_entities: list[dict[str, Any]] = []

    for node in graph.nodes.values():
        if node.node_type not in _ENTITY_NODE_TYPES:
            continue

        ent = {
            "node_id": node.node_id,
            "title": node.title,
            "node_type": node.node_type.value,
            "entity_id": node.entity_id,
            "device_id": node.device_id,
            "area_id": node.area_id,
            "disabled": node.disabled,
            "available": node.available,
        }

        if node.device_id and node.device_id in devices:
            devices[node.device_id]["entities"].append(ent)
            continue

        if node.area_id and node.area_id in areas:
            entities_by_area.setdefault(node.area_id, []).append(ent)
            continue

        unassigned_entities.append(ent)

    return entities_by_area, unassigned_entities


def _assemble_areas(
    areas: dict[str, dict[str, Any]],
    devices_by_area: dict[str, list[dict[str, Any]]],
    entities_by_area: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Fill each area with its devices and entities, add counts, and sort."""
    result_areas = []

    for area_id, area in areas.items():
        area["devices"] = devices_by_area.get(area_id, [])
        area["entities"] = entities_by_area.get(area_id, [])
        area["device_count"] = len(area["devices"])
        area["entity_count"] = (
            area["device_count"]
            + len(area["entities"])
            + sum(len(d["entities"]) for d in area["devices"])
        )
        result_areas.append(area)

    result_areas.sort(key=lambda a: a["title"].lower())

    return result_areas


def _group_devices_by_area(
    devices: dict[str, dict[str, Any]],
    areas: dict[str, dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Bucket devices by area in a single pass; the rest are unassigned."""
    devices_by_area: dict[str, list[dict[str, Any]]] = {}
    unassigned_devices: list[dict[str, Any]] = []

    for dev in devices.values():
        area_id = dev["area_id"]

        if not area_id or area_id not in areas:
            unassigned_devices.append(dev)
            continue

        devices_by_area.setdefault(area_id, []).append(dev)

    return devices_by_area, unassigned_devices
