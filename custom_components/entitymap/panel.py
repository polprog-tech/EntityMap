"""HTTP handler to serve the EntityMap frontend panel."""

from __future__ import annotations

import pathlib

from aiohttp import web

from homeassistant.components.http import HomeAssistantView

PANEL_JS_PATH = pathlib.Path(__file__).parent / "frontend" / "entitymap-panel.js"


class EntityMapPanelView(HomeAssistantView):
    """Serve the EntityMap panel JavaScript."""

    url = "/api/panel_custom/entitymap"
    name = "api:panel_custom:entitymap"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Serve the panel JS file."""
        content = PANEL_JS_PATH.read_text(encoding="utf-8")
        return web.Response(
            body=content,
            content_type="application/javascript",
            headers={"Cache-Control": "no-cache"},
        )
