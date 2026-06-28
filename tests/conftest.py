"""Fixtures for the Lumen test suite."""

from collections.abc import Generator
from unittest.mock import patch

import pytest
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lumen.const import (
    CONF_DONGLE_SERIAL,
    CONF_MODE,
    CONF_SERIAL,
    DOMAIN,
    MODE_CLIENT,
)

from .fake_transport import FakeTransport

ENTRY_DATA = {
    CONF_NAME: "Lumen",
    CONF_HOST: "1.2.3.4",
    CONF_PORT: 8000,
    CONF_MODE: MODE_CLIENT,
    CONF_DONGLE_SERIAL: "BA12345678",
    CONF_SERIAL: "1234567890",
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> Generator[None]:
    """Enable loading custom integrations in every test."""
    yield


@pytest.fixture
async def setup_lumen(hass: HomeAssistant) -> MockConfigEntry:
    """Set up the integration with a fake transport and return the config entry."""
    entry = MockConfigEntry(domain=DOMAIN, data=ENTRY_DATA, unique_id="BA12345678", title="Lumen")
    entry.add_to_hass(hass)
    with patch("custom_components.lumen.ClientTransport", FakeTransport):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry
