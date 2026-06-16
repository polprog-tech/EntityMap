"""Migration suggestion engine for EntityMap."""

from __future__ import annotations

from .const import DependencyKind, NodeType
from .models import DependencyGraph, GraphEdge, MigrationSuggestion

_DEVICE_REF_KINDS = {
    DependencyKind.DEVICE_TRIGGER,
    DependencyKind.DEVICE_CONDITION,
    DependencyKind.DEVICE_ACTION,
}


def get_migration_report(
    graph: DependencyGraph, source_node_id: str, target_node_id: str | None = None
) -> list[MigrationSuggestion]:
    """Generate a migration report for replacing one node with another."""
    source_node = graph.nodes.get(source_node_id)

    if not source_node:
        return [MigrationSuggestion(description=f"Node '{source_node_id}' not found in the graph.")]

    inbound = graph.get_inbound(source_node_id)

    if not inbound:
        return _no_inbound_report(source_node)

    by_kind = _group_inbound_by_kind(inbound)
    suggestions: list[MigrationSuggestion] = []

    suggestions.extend(_automation_ref_suggestions(by_kind, target_node_id))

    device_suggestion = _device_reference_suggestion(inbound)

    if device_suggestion:
        suggestions.append(device_suggestion)

    suggestions.extend(_membership_suggestions(by_kind))

    mapping_suggestion = _device_entity_mapping_suggestion(graph, source_node, source_node_id)

    if mapping_suggestion:
        suggestions.append(mapping_suggestion)

    return suggestions


def _no_inbound_report(source_node) -> list[MigrationSuggestion]:
    """A node nothing depends on can be removed/replaced freely."""
    return [
        MigrationSuggestion(
            description=(
                f"'{source_node.title}' has no inbound dependencies. "
                "It can likely be removed or replaced without impact."
            ),
        )
    ]


def _group_inbound_by_kind(inbound: list[GraphEdge]) -> dict[DependencyKind, list[str]]:
    """Group inbound edge sources by their dependency kind."""
    by_kind: dict[DependencyKind, list[str]] = {}

    for edge in inbound:
        by_kind.setdefault(edge.dependency_kind, []).append(edge.source)

    return by_kind


def _automation_ref_suggestions(
    by_kind: dict[DependencyKind, list[str]], target_node_id: str | None
) -> list[MigrationSuggestion]:
    """Suggestions for trigger, condition, and action references."""
    suggestions: list[MigrationSuggestion] = []

    trigger_sources = by_kind.get(DependencyKind.TRIGGER, [])

    if trigger_sources:
        suggestions.append(
            MigrationSuggestion(
                description=f"{len(trigger_sources)} automation(s) use this entity as a trigger.",
                affected_items=tuple(trigger_sources),
                recommendation=(
                    "After replacing the entity, update the trigger entity_id "
                    "in each automation to the new entity."
                    + (f" New entity: {target_node_id}" if target_node_id else "")
                ),
            )
        )

    condition_sources = by_kind.get(DependencyKind.CONDITION, [])

    if condition_sources:
        suggestions.append(
            MigrationSuggestion(
                description=(
                    f"{len(condition_sources)} automation(s) use this entity in a condition."
                ),
                affected_items=tuple(condition_sources),
                recommendation="Update condition entity_id references to the new entity.",
            )
        )

    action_sources = by_kind.get(DependencyKind.ACTION, [])

    if action_sources:
        suggestions.append(
            MigrationSuggestion(
                description=(
                    f"{len(action_sources)} automation(s)/script(s) target this "
                    "entity in an action."
                ),
                affected_items=tuple(action_sources),
                recommendation="Update action entity_id/target references.",
            )
        )

    return suggestions


def _device_reference_suggestion(inbound: list[GraphEdge]) -> MigrationSuggestion | None:
    """Warn about device_id-based references that break on device replacement."""
    device_refs = [e.source for e in inbound if e.dependency_kind in _DEVICE_REF_KINDS]

    if not device_refs:
        return None

    return MigrationSuggestion(
        description=(
            f"{len(device_refs)} item(s) use device_id references. "
            "These WILL break when the device is replaced."
        ),
        affected_items=tuple(device_refs),
        recommendation=(
            "After adding the new device, open each affected "
            "automation/script and re-select the device in the "
            "device trigger/condition/action picker. Consider "
            "switching to entity-based references for resilience."
        ),
    )


def _membership_suggestions(by_kind: dict[DependencyKind, list[str]]) -> list[MigrationSuggestion]:
    """Suggestions for scene and group membership."""
    suggestions: list[MigrationSuggestion] = []

    scene_members = by_kind.get(DependencyKind.SCENE_MEMBER, [])

    if scene_members:
        suggestions.append(
            MigrationSuggestion(
                description=f"{len(scene_members)} scene(s) include this entity.",
                affected_items=tuple(scene_members),
                recommendation=(
                    "After replacing, update each scene to include the "
                    "new entity with the desired state."
                ),
            )
        )

    group_members = by_kind.get(DependencyKind.GROUP_MEMBER, [])

    if group_members:
        suggestions.append(
            MigrationSuggestion(
                description=f"{len(group_members)} group(s) include this entity.",
                affected_items=tuple(group_members),
                recommendation="Update group configuration to replace the old entity with the new one.",
            )
        )

    return suggestions


def _device_entity_mapping_suggestion(
    graph: DependencyGraph, source_node, source_node_id: str
) -> MigrationSuggestion | None:
    """Entity-mapping guidance shown when replacing a whole device."""
    if source_node.node_type != NodeType.DEVICE:
        return None

    entity_edges = [
        e
        for e in graph.get_inbound(source_node_id)
        if e.dependency_kind == DependencyKind.ENTITY_OF_DEVICE
    ]

    if not entity_edges:
        return None

    entity_ids = tuple(e.source for e in entity_edges)

    return MigrationSuggestion(
        description=(
            f"This device provides {len(entity_ids)} entity/entities. Record them before removal."
        ),
        affected_items=entity_ids,
        recommendation=(
            "1. Note all entity IDs listed above.\n"
            "2. Remove the old device.\n"
            "3. Add the new device.\n"
            "4. Use Settings → Devices → Entity ID to rename new "
            "entities to match old IDs.\n"
            "5. Verify all automations/scripts/scenes still work."
        ),
    )
