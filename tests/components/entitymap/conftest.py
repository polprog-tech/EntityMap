"""Test fixtures for EntityMap tests."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.entitymap.const import (
    CONF_AUTO_REFRESH,
    CONF_INCLUDE_GROUPS,
    CONF_INCLUDE_TEMPLATES,
    CONF_SCAN_INTERVAL_HOURS,
    CONF_SCAN_ON_STARTUP,
    DOMAIN,
)
from custom_components.entitymap.models import DependencyGraph


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    hass.states = MagicMock()
    hass.states.async_all = MagicMock(return_value=[])
    hass.states.async_entity_ids = MagicMock(return_value=[])
    hass.states.get = MagicMock(return_value=None)
    hass.bus = MagicMock()
    hass.bus.async_fire = MagicMock()
    hass.bus.async_listen = MagicMock(return_value=MagicMock())
    hass.bus.async_listen_once = MagicMock(return_value=MagicMock())
    hass.services = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    return hass


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.data = {}
    entry.options = {
        CONF_SCAN_ON_STARTUP: True,
        CONF_AUTO_REFRESH: True,
        CONF_SCAN_INTERVAL_HOURS: 6,
        CONF_INCLUDE_TEMPLATES: True,
        CONF_INCLUDE_GROUPS: True,
    }
    entry.unique_id = DOMAIN
    return entry


@pytest.fixture
def empty_graph():
    """Create an empty dependency graph."""
    return DependencyGraph()
