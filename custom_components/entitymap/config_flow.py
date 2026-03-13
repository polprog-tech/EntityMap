"""Config flow for EntityMap integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback

from .const import (
    CONF_AUTO_REFRESH,
    CONF_INCLUDE_GROUPS,
    CONF_INCLUDE_TEMPLATES,
    CONF_SCAN_INTERVAL_HOURS,
    CONF_SCAN_ON_STARTUP,
    DEFAULT_AUTO_REFRESH,
    DEFAULT_INCLUDE_GROUPS,
    DEFAULT_INCLUDE_TEMPLATES,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DEFAULT_SCAN_ON_STARTUP,
    DOMAIN,
)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SCAN_ON_STARTUP, default=DEFAULT_SCAN_ON_STARTUP): bool,
        vol.Required(CONF_AUTO_REFRESH, default=DEFAULT_AUTO_REFRESH): bool,
        vol.Required(
            CONF_INCLUDE_TEMPLATES, default=DEFAULT_INCLUDE_TEMPLATES
        ): bool,
        vol.Required(CONF_INCLUDE_GROUPS, default=DEFAULT_INCLUDE_GROUPS): bool,
    }
)


class EntityMapConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for EntityMap."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title="EntityMap",
                data={},
                options={
                    CONF_SCAN_ON_STARTUP: user_input[CONF_SCAN_ON_STARTUP],
                    CONF_AUTO_REFRESH: user_input[CONF_AUTO_REFRESH],
                    CONF_INCLUDE_TEMPLATES: user_input[CONF_INCLUDE_TEMPLATES],
                    CONF_INCLUDE_GROUPS: user_input[CONF_INCLUDE_GROUPS],
                    CONF_SCAN_INTERVAL_HOURS: DEFAULT_SCAN_INTERVAL_HOURS,
                },
            )

        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow handler."""
        return EntityMapOptionsFlow()


class EntityMapOptionsFlow(OptionsFlow):
    """Handle EntityMap options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_ON_STARTUP,
                    default=options.get(
                        CONF_SCAN_ON_STARTUP, DEFAULT_SCAN_ON_STARTUP
                    ),
                ): bool,
                vol.Required(
                    CONF_AUTO_REFRESH,
                    default=options.get(CONF_AUTO_REFRESH, DEFAULT_AUTO_REFRESH),
                ): bool,
                vol.Required(
                    CONF_SCAN_INTERVAL_HOURS,
                    default=options.get(
                        CONF_SCAN_INTERVAL_HOURS, DEFAULT_SCAN_INTERVAL_HOURS
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=168)),
                vol.Required(
                    CONF_INCLUDE_TEMPLATES,
                    default=options.get(
                        CONF_INCLUDE_TEMPLATES, DEFAULT_INCLUDE_TEMPLATES
                    ),
                ): bool,
                vol.Required(
                    CONF_INCLUDE_GROUPS,
                    default=options.get(
                        CONF_INCLUDE_GROUPS, DEFAULT_INCLUDE_GROUPS
                    ),
                ): bool,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
