"""Tests for the EntityMap custom panel serving.

The panel is a multi-file ES module served from a static directory. These
scenarios guard that the module exists, that the frontend directory is
registered as a static path, and that the sidebar panel points at the served
module (regression for issue #1, where the panel could not load).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.entitymap import _async_register_panel
from custom_components.entitymap.panel import (
    FRONTEND_DIR,
    PANEL_MODULE_URL,
    PANEL_URL_BASE,
    async_register_frontend,
)


async def _register_and_capture() -> dict:
    """Register the sidebar panel and return the kwargs sent to the frontend."""
    captured: dict = {}

    with patch(
        "homeassistant.components.frontend.async_register_built_in_panel",
        side_effect=lambda _hass, **kwargs: captured.update(kwargs),
    ):
        await _async_register_panel(MagicMock())

    return captured


class TestFrontendAssets:
    """Scenarios for the served frontend module."""

    def test_panel_module_exists_in_frontend_dir(self):
        """GIVEN the static frontend directory.

        WHEN it is inspected.

        THEN it contains the panel module the sidebar points at.
        """
        assert (FRONTEND_DIR / "entitymap-panel.js").is_file()

    def test_module_url_is_under_the_static_base(self):
        """GIVEN the advertised module URL.

        WHEN it is compared to the static base.

        THEN it is served from that base as a .js module.
        """
        assert PANEL_MODULE_URL.startswith(f"{PANEL_URL_BASE}/")
        assert PANEL_MODULE_URL.endswith(".js")


class TestStaticRegistration:
    """Scenarios for registering the frontend static path."""

    @pytest.mark.asyncio
    async def test_registers_frontend_directory(self):
        """GIVEN a Home Assistant instance.

        WHEN the frontend is registered.

        THEN the frontend directory is served at the panel base path.
        """
        hass = MagicMock()
        hass.http.async_register_static_paths = AsyncMock()

        await async_register_frontend(hass)

        configs = hass.http.async_register_static_paths.call_args.args[0]
        assert len(configs) == 1
        assert configs[0].url_path == PANEL_URL_BASE
        assert configs[0].path == str(FRONTEND_DIR)


class TestPanelRegistration:
    """Scenarios for registering the sidebar panel."""

    @pytest.mark.asyncio
    async def test_registers_non_admin_custom_panel(self):
        """GIVEN a Home Assistant instance.

        WHEN the panel is registered.

        THEN it is a non-admin custom panel pointing at the served module.
        """
        captured = await _register_and_capture()

        assert captured["component_name"] == "custom"
        assert captured["frontend_url_path"] == "entitymap"
        assert captured["require_admin"] is False
        assert captured["config"]["_panel_custom"]["embed_iframe"] is False
        assert captured["config"]["_panel_custom"]["module_url"] == PANEL_MODULE_URL
