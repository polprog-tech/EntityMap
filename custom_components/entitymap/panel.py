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
    # The frontend imports this module via a plain <script type="module">, which
    # carries no auth token. Requiring auth makes the import fail with an invalid
    # authentication error (and trips the HTTP ban component), so the panel never
    # loads. The file is public frontend code with no secrets, so serve it openly.
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        """Serve the panel JS file."""
        content = PANEL_JS_PATH.read_text(encoding="utf-8")
        return web.Response(
            body=content,
            content_type="application/javascript",
            headers={"Cache-Control": "no-cache"},
        )
