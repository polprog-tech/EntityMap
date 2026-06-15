"""Tests for the EntityMap custom panel serving.

Scenarios cover the panel JS view (auth, URL, served content) and the
sidebar panel registration, with a regression guard where the
panel could not load because the view required authentication.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.entitymap import _async_register_panel
from custom_components.entitymap.panel import EntityMapPanelView


async def _register_and_capture() -> dict:
    """Register the sidebar panel and return the kwargs sent to the frontend."""
    captured: dict = {}

    with patch(
        "homeassistant.components.frontend.async_register_built_in_panel",
        side_effect=lambda _hass, **kwargs: captured.update(kwargs),
    ):
        await _async_register_panel(MagicMock())

    return captured


class TestPanelView:
    """Scenarios for the view that serves the panel JavaScript module."""

    def test_view_does_not_require_auth(self):
        """GIVEN the panel view served to the browser module loader.

        WHEN its auth requirement is inspected.

        THEN it must not require auth, because module imports carry no token
        (regression for issue #1: "Unable to load custom panel ...").
        """
        assert EntityMapPanelView.requires_auth is False

    @pytest.mark.asyncio
    async def test_view_url_matches_registered_module_url(self):
        """GIVEN the view URL and the module_url advertised to the frontend.

        WHEN they are compared.

        THEN they match, so the frontend requests the path the view serves.
        """
        captured = await _register_and_capture()

        module_url = captured["config"]["_panel_custom"]["module_url"]
        assert module_url == EntityMapPanelView.url

    @pytest.mark.asyncio
    async def test_get_serves_javascript(self):
        """GIVEN a request for the panel module.

        WHEN the view handles it.

        THEN it returns the JS file as application/javascript with no caching.
        """
        view = EntityMapPanelView()

        response = await view.get(MagicMock())

        assert response.content_type == "application/javascript"
        assert response.headers["Cache-Control"] == "no-cache"
        assert response.body, "panel JS body should not be empty"


class TestPanelRegistration:
    """Scenarios for registering the sidebar panel."""

    @pytest.mark.asyncio
    async def test_registers_non_admin_custom_panel(self):
        """GIVEN a Home Assistant instance.

        WHEN the panel is registered.

        THEN it is a non-admin custom panel that loads without an iframe.
        """
        captured = await _register_and_capture()

        assert captured["component_name"] == "custom"
        assert captured["frontend_url_path"] == "entitymap"
        assert captured["require_admin"] is False
        assert captured["config"]["_panel_custom"]["embed_iframe"] is False
