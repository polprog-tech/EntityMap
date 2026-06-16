"""Shared config-parsing helpers for the automation and script adapters."""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

_NESTED_ACTION_KEYS = ("choose", "sequence", "default", "then", "else")

_TEMPLATE_PATTERNS = [
    re.compile(r"states\(\s*['\"]([a-z_]+\.[a-z0-9_]+)['\"]\s*\)"),
    re.compile(r"states\.([a-z_]+\.[a-z0-9_]+)"),
    re.compile(r"is_state\(\s*['\"]([a-z_]+\.[a-z0-9_]+)['\"]"),
    re.compile(r"state_attr\(\s*['\"]([a-z_]+\.[a-z0-9_]+)['\"]"),
]


def as_list(value: Any) -> list[Any]:
    """Wrap a scalar in a list, pass lists through, and treat None as empty."""
    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]


def extract_entity_ids(data: dict[str, Any], key: str = "entity_id") -> list[str]:
    """Extract entity IDs from a config value (scalar, comma-separated, or list)."""
    value = data.get(key)

    if value is None:
        return []

    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if "." in v.strip()]

    if isinstance(value, list):
        return [v for v in value if isinstance(v, str) and "." in v]

    return []


def extract_template_refs(template_str: str) -> list[str]:
    """Extract entity references from a Jinja template string."""
    refs: list[str] = []

    for pattern in _TEMPLATE_PATTERNS:
        refs.extend(pattern.findall(template_str))

    return list(set(refs))


def iter_nested_actions(action: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Yield each action nested inside choose/sequence/if/repeat blocks."""
    for key in _NESTED_ACTION_KEYS:
        yield from _iter_branch_actions(action.get(key))

    repeat = action.get("repeat")

    if isinstance(repeat, dict):
        yield from as_list(repeat.get("sequence", []))


def _iter_branch_actions(nested: Any) -> Iterator[dict[str, Any]]:
    """Yield the actions inside one nested branch list."""
    if not isinstance(nested, list):
        return

    for item in nested:
        if not isinstance(item, dict):
            continue

        if "sequence" in item:
            yield from as_list(item["sequence"])
        else:
            yield item
