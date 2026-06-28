"""Tests for the Lumen config flow."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.lumen.config_flow import CannotConnect
from custom_components.lumen.const import (
    CONF_DONGLE_SERIAL,
    CONF_MODE,
    CONF_SERIAL,
    DOMAIN,
    MODE_CLIENT,
    MODE_SERVER,
)

USER_INPUT = {
    CONF_NAME: "Lumen",
    CONF_HOST: "1.2.3.4",
    CONF_PORT: 8000,
    CONF_MODE: MODE_CLIENT,
    CONF_DONGLE_SERIAL: "BA12345678",
    CONF_SERIAL: "1234567890",
}


async def test_user_flow_client_success(hass: HomeAssistant) -> None:
    """A valid client-mode submission creates an entry."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM

    with (
        patch("custom_components.lumen.config_flow._async_check_connection", return_value=None),
        patch("custom_components.lumen.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], dict(USER_INPUT))
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Lumen"
    assert result["data"][CONF_HOST] == "1.2.3.4"
    assert result["result"].unique_id == "BA12345678"


async def test_user_flow_cannot_connect(hass: HomeAssistant) -> None:
    """A failed reachability check shows an error and keeps the form open."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    with patch(
        "custom_components.lumen.config_flow._async_check_connection",
        side_effect=CannotConnect,
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], dict(USER_INPUT))

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_server_mode_skips_connection_check(hass: HomeAssistant) -> None:
    """Server mode does not attempt an outbound connection."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    server_input = {**USER_INPUT, CONF_MODE: MODE_SERVER}
    with (
        patch(
            "custom_components.lumen.config_flow._async_check_connection",
            side_effect=AssertionError("should not be called in server mode"),
        ),
        patch("custom_components.lumen.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], server_input)
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_duplicate_dongle_aborts(hass: HomeAssistant) -> None:
    """Configuring the same dongle serial twice aborts the second flow."""
    with (
        patch("custom_components.lumen.config_flow._async_check_connection", return_value=None),
        patch("custom_components.lumen.async_setup_entry", return_value=True),
    ):
        first = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=dict(USER_INPUT)
        )
        assert first["type"] is FlowResultType.CREATE_ENTRY

        second = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=dict(USER_INPUT)
        )

    assert second["type"] is FlowResultType.ABORT
    assert second["reason"] == "already_configured"
