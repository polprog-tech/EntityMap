"""Static serving for the EntityMap frontend panel.

The panel is a multi-file ES module (entitymap-panel.js plus constants.js and
styles.js), so the whole frontend directory is served as a static path. The
module is imported by the browser without an auth token, and static paths are
public, which is exactly what a frontend bundle needs.
"""

from __future__ import annotations

import pathlib

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

FRONTEND_DIR = pathlib.Path(__file__).parent / "frontend"
PANEL_URL_BASE = "/entitymap_frontend"
PANEL_MODULE_URL = f"{PANEL_URL_BASE}/entitymap-panel.js"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the panel's frontend directory as a public static path."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(PANEL_URL_BASE, str(FRONTEND_DIR), False)]
    )
