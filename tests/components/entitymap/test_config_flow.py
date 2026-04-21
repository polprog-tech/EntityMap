"""Tests for EntityMap config flow and options flow.

Scenarios cover the full UI flow: form display, entry creation,
options modification, and edge cases.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.entitymap.config_flow import (
    EntityMapConfigFlow,
    EntityMapOptionsFlow,
)
from custom_components.entitymap.const import (
    CONF_AUTO_REFRESH,
    CONF_INCLUDE_GROUPS,
    CONF_INCLUDE_TEMPLATES,
    CONF_SCAN_INTERVAL_HOURS,
    CONF_SCAN_ON_STARTUP,
)

# ── Config Flow ─────────────────────────────────────────────────────


class TestConfigFlowUserStep:
    """Scenarios for the initial user setup step."""

    @pytest.fixture
    def flow(self):
        """Create a config flow instance with mocked HA context."""
        flow = EntityMapConfigFlow()
        flow.hass = MagicMock()
        flow.context = {"source": "user"}
        return flow

    """GIVEN a user starting configuration."""
    @pytest.mark.asyncio
    async def test_shows_form_when_no_input(self, flow):

        """WHEN no input has been provided."""
        with patch.object(flow, "async_set_unique_id", return_value=None):
            with patch.object(flow, "_abort_if_unique_id_configured"):
                result = await flow.async_step_user(user_input=None)

        """THEN a form is displayed for the user step."""
        assert result["type"] == "form"
        assert result["step_id"] == "user"

    """GIVEN valid user input with all options."""
    @pytest.mark.asyncio
    async def test_creates_entry_with_valid_input(self, flow):

        user_input = {
            CONF_SCAN_ON_STARTUP: True,
            CONF_AUTO_REFRESH: True,
            CONF_INCLUDE_TEMPLATES: True,
            CONF_INCLUDE_GROUPS: True,
        }

        """WHEN submitted."""
        with patch.object(flow, "async_set_unique_id", return_value=None):
            with patch.object(flow, "_abort_if_unique_id_configured"):
                with patch.object(flow, "async_create_entry") as mock_create:
                    await flow.async_step_user(user_input=user_input)

        """THEN a config entry is created with correct title and options."""
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args
        assert call_kwargs[1]["title"] == "EntityMap"
        options = call_kwargs[1]["options"]
        assert options[CONF_SCAN_ON_STARTUP] is True
        assert options[CONF_AUTO_REFRESH] is True

    """GIVEN user input with only required fields set to False."""
    @pytest.mark.asyncio
    async def test_creates_entry_with_minimal_input(self, flow):

        user_input = {
            CONF_SCAN_ON_STARTUP: False,
            CONF_AUTO_REFRESH: False,
            CONF_INCLUDE_TEMPLATES: False,
            CONF_INCLUDE_GROUPS: False,
        }

        """WHEN submitted."""
        with patch.object(flow, "async_set_unique_id", return_value=None):
            with patch.object(flow, "_abort_if_unique_id_configured"):
                with patch.object(flow, "async_create_entry") as mock_create:
                    await flow.async_step_user(user_input=user_input)

        """THEN a config entry is created preserving those values."""
        options = mock_create.call_args[1]["options"]
        assert options[CONF_SCAN_ON_STARTUP] is False
        assert options[CONF_INCLUDE_TEMPLATES] is False


# ── Options Flow ────────────────────────────────────────────────────


class TestOptionsFlowInit:
    """Scenarios for the options flow initialization."""

    @pytest.fixture
    def options_flow(self, mock_config_entry):
        """Create an options flow instance with config entry patched in."""
        flow = EntityMapOptionsFlow()
        flow.hass = MagicMock()
        # Patch config_entry since OptionsFlow has a property setter that
        # requires the HA frame helper to be set up.
        with patch.object(
            type(flow),
            "config_entry",
            new_callable=lambda: property(lambda self: mock_config_entry),
        ):
            yield flow

    """GIVEN an existing config entry."""
    @pytest.mark.asyncio
    async def test_shows_form_with_current_values(self, options_flow):

        """WHEN the options flow starts."""
        result = await options_flow.async_step_init(user_input=None)

        """THEN a form is displayed for the init step."""
        assert result["type"] == "form"
        assert result["step_id"] == "init"

    """GIVEN the user modifies options."""
    @pytest.mark.asyncio
    async def test_saves_updated_options(self, options_flow):

        user_input = {
            CONF_SCAN_ON_STARTUP: False,
            CONF_AUTO_REFRESH: True,
            CONF_SCAN_INTERVAL_HOURS: 12,
            CONF_INCLUDE_TEMPLATES: False,
            CONF_INCLUDE_GROUPS: True,
        }

        """WHEN submitted."""
        with patch.object(options_flow, "async_create_entry") as mock_create:
            await options_flow.async_step_init(user_input=user_input)

        """THEN the new options are saved via async_create_entry."""
        mock_create.assert_called_once_with(data=user_input)

    """GIVEN full options input."""
    @pytest.mark.asyncio
    async def test_preserves_all_fields_on_save(self, options_flow):

        user_input = {
            CONF_SCAN_ON_STARTUP: True,
            CONF_AUTO_REFRESH: False,
            CONF_SCAN_INTERVAL_HOURS: 24,
            CONF_INCLUDE_TEMPLATES: True,
            CONF_INCLUDE_GROUPS: False,
        }

        """WHEN saved."""
        with patch.object(options_flow, "async_create_entry") as mock_create:
            await options_flow.async_step_init(user_input=user_input)

        """THEN all fields including scan_interval are preserved."""
        saved_data = mock_create.call_args[1]["data"]
        assert saved_data[CONF_SCAN_INTERVAL_HOURS] == 24
        assert saved_data[CONF_INCLUDE_GROUPS] is False
