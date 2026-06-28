"""Config flow for the Lumen integration."""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_DONGLE_SERIAL,
    CONF_MODE,
    CONF_SERIAL,
    CONNECT_TIMEOUT,
    DEFAULT_MODE,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DOMAIN,
    MODE_CLIENT,
    MODE_SERVER,
    SERIAL_LENGTH,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_MODE, default=DEFAULT_MODE): vol.In([MODE_CLIENT, MODE_SERVER]),
        vol.Required(CONF_DONGLE_SERIAL): str,
        vol.Required(CONF_SERIAL): str,
    }
)


class CannotConnect(HomeAssistantError):
    """Error raised when the dongle cannot be reached."""


async def _async_check_connection(host: str, port: int) -> None:
    """Open a brief TCP connection to confirm the dongle is reachable."""
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=CONNECT_TIMEOUT)
    except (OSError, TimeoutError) as err:
        raise CannotConnect from err
    writer.close()
    try:
        await writer.wait_closed()
    except OSError:
        # The socket was reachable; failures while closing are not interesting.
        pass


class LumenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the configuration flow for Lumen."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step where the user enters connection details."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if len(user_input[CONF_DONGLE_SERIAL]) != SERIAL_LENGTH or len(user_input[CONF_SERIAL]) != SERIAL_LENGTH:
                errors["base"] = "invalid_serial"
            else:
                await self.async_set_unique_id(user_input[CONF_DONGLE_SERIAL])
                self._abort_if_unique_id_configured()

                if user_input[CONF_MODE] == MODE_CLIENT:
                    try:
                        await _async_check_connection(user_input[CONF_HOST], user_input[CONF_PORT])
                    except CannotConnect:
                        errors["base"] = "cannot_connect"

            if not errors:
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
