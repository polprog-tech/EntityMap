"""Constants for the EntityMap integration."""

from __future__ import annotations

from enum import StrEnum
from typing import Final

DOMAIN: Final = "entitymap"

# ── Configuration keys ──────────────────────────────────────────────
CONF_SCAN_ON_STARTUP: Final = "scan_on_startup"
CONF_AUTO_REFRESH: Final = "auto_refresh"
CONF_SCAN_INTERVAL_HOURS: Final = "scan_interval_hours"
CONF_INCLUDE_TEMPLATES: Final = "include_templates"
CONF_INCLUDE_GROUPS: Final = "include_groups"

# ── Defaults ────────────────────────────────────────────────────────
DEFAULT_SCAN_ON_STARTUP: Final = True
DEFAULT_AUTO_REFRESH: Final = True
DEFAULT_SCAN_INTERVAL_HOURS: Final = 6
DEFAULT_INCLUDE_TEMPLATES: Final = True
DEFAULT_INCLUDE_GROUPS: Final = True

# ── Panel ───────────────────────────────────────────────────────────
PANEL_URL: Final = "/entitymap"
PANEL_TITLE: Final = "EntityMap"
PANEL_ICON: Final = "mdi:graph-outline"

# ── Services ────────────────────────────────────────────────────────
SERVICE_SCAN: Final = "scan"
SERVICE_ANALYZE_IMPACT: Final = "analyze_impact"
SERVICE_GET_DEPENDENCIES: Final = "get_dependencies"

# ── Events ──────────────────────────────────────────────────────────
EVENT_GRAPH_UPDATED: Final = f"{DOMAIN}_graph_updated"
EVENT_SCAN_STARTED: Final = f"{DOMAIN}_scan_started"
EVENT_SCAN_COMPLETED: Final = f"{DOMAIN}_scan_completed"

# ── Attributes ──────────────────────────────────────────────────────
ATTR_NODE_ID: Final = "node_id"
ATTR_NODE_TYPE: Final = "node_type"
ATTR_TARGET_NODE: Final = "target_node"
ATTR_INCLUDE_INFERRED: Final = "include_inferred"


class NodeType(StrEnum):
    """Types of nodes in the dependency graph."""

    DEVICE = "device"
    ENTITY = "entity"
    AUTOMATION = "automation"
    SCRIPT = "script"
    SCENE = "scene"
    HELPER = "helper"
    GROUP = "group"
    AREA = "area"
    UNKNOWN = "unknown"


class DependencyKind(StrEnum):
    """Types of dependency edges."""

    ENTITY_OF_DEVICE = "entity_of_device"
    TRIGGER = "trigger"
    CONDITION = "condition"
    ACTION = "action"
    TARGET = "target"
    TEMPLATE_REFERENCE = "template_reference"
    STATE_REFERENCE = "state_reference"
    SCENE_MEMBER = "scene_member"
    GROUP_MEMBER = "group_member"
    SERVICE_CALL = "service_call"
    DEVICE_TRIGGER = "device_trigger"
    DEVICE_CONDITION = "device_condition"
    DEVICE_ACTION = "device_action"
    DEVICE_IN_AREA = "device_in_area"
    HELPER_REFERENCE = "helper_reference"
    INFERRED = "inferred"


class Confidence(StrEnum):
    """Confidence level for a dependency edge."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Severity(StrEnum):
    """Severity level for fragility findings."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FragilityType(StrEnum):
    """Types of fragility findings."""

    MISSING_ENTITY = "missing_entity"
    MISSING_DEVICE = "missing_device"
    DEVICE_ID_REFERENCE = "device_id_reference"
    DISABLED_REFERENCE = "disabled_reference"
    UNAVAILABLE_REFERENCE = "unavailable_reference"
    STALE_REFERENCE = "stale_reference"
    DUPLICATE_COUPLING = "duplicate_coupling"
    TIGHT_DEVICE_COUPLING = "tight_device_coupling"
    HIDDEN_DEPENDENCY = "hidden_dependency"
