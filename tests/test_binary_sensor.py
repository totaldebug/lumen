"""Tests for the Lumen binary_sensor platform — inverter connectivity."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_connectivity_on_after_setup(hass: HomeAssistant, setup_lumen: MockConfigEntry) -> None:
    """Connectivity reports 'on' once the first poll has succeeded."""
    state = hass.states.get("binary_sensor.lumen_connectivity")
    assert state is not None
    assert state.state == "on"
    assert state.attributes["device_class"] == "connectivity"
