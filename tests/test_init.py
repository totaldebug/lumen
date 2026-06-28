"""End-to-end setup tests for the Lumen integration."""

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lumen.const import (
    CONF_DONGLE_SERIAL,
    CONF_MODE,
    CONF_SERIAL,
    DOMAIN,
    MODE_CLIENT,
)

from .fake_transport import FakeTransport

DATA = {
    CONF_NAME: "Lumen",
    CONF_HOST: "1.2.3.4",
    CONF_PORT: 8000,
    CONF_MODE: MODE_CLIENT,
    CONF_DONGLE_SERIAL: "BA12345678",
    CONF_SERIAL: "1234567890",
}


def _entry(hass: HomeAssistant) -> MockConfigEntry:
    """Add and return a Lumen config entry."""
    entry = MockConfigEntry(domain=DOMAIN, data=DATA, unique_id="BA12345678", title="Lumen")
    entry.add_to_hass(hass)
    return entry


async def test_setup_creates_sensors_with_values(hass: HomeAssistant) -> None:
    """Setting up the entry creates sensors populated from the decoded registers."""
    entry = _entry(hass)
    with patch("custom_components.lumen.ClientTransport", FakeTransport):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert hass.states.get("sensor.lumen_battery_voltage").state == "0.4"
    assert hass.states.get("sensor.lumen_solar_voltage_array_1").state == "0.1"


async def test_inverter_is_connected_via_dongle(hass: HomeAssistant) -> None:
    """The inverter device hangs off the dongle device via via_device."""
    entry = _entry(hass)
    with patch("custom_components.lumen.ClientTransport", FakeTransport):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    device_registry = dr.async_get(hass)
    dongle = device_registry.async_get_device(identifiers={(DOMAIN, "BA12345678")})
    inverter = device_registry.async_get_device(identifiers={(DOMAIN, "1234567890")})
    assert dongle is not None
    assert inverter is not None
    assert inverter.via_device_id == dongle.id


async def test_unload(hass: HomeAssistant) -> None:
    """The entry unloads cleanly."""
    entry = _entry(hass)
    with patch("custom_components.lumen.ClientTransport", FakeTransport):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
