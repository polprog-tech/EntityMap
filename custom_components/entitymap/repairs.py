"""Repair flows for EntityMap."""

from __future__ import annotations

from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.core import HomeAssistant


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict | None,
) -> RepairsFlow:
    """Create a repair flow for an EntityMap issue."""
    # Most EntityMap issues are informational — user should fix manually
    return ConfirmRepairFlow()
