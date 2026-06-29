"""Tests for the Lumen sensor platform — derived and diagnostic sensors.

FakeTransport answers each read with values equal to the register address, so
e.g. pv1/pv2/pv3 power (regs 7/8/9) read as 7/8/9 W.
"""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_combined_solar_output(hass: HomeAssistant, setup_lumen: MockConfigEntry) -> None:
    """Solar Output sums the three PV arrays (7 + 8 + 9 W)."""
    assert float(hass.states.get("sensor.lumen_solar_output").state) == 24.0


async def test_battery_and_grid_flow(hass: HomeAssistant, setup_lumen: MockConfigEntry) -> None:
    """Flow sensors are signed differences: charge - discharge, to_grid - from_grid."""
    assert float(hass.states.get("sensor.lumen_battery_flow").state) == -1.0  # 10 - 11
    assert float(hass.states.get("sensor.lumen_grid_flow").state) == -1.0  # 26 - 27


async def test_status_text(hass: HomeAssistant, setup_lumen: MockConfigEntry) -> None:
    """Status (Text) maps the raw status code (reg 0 = 0) to its label."""
    assert hass.states.get("sensor.lumen_status_text").state == "Standby"


async def test_data_received_timestamp(hass: HomeAssistant, setup_lumen: MockConfigEntry) -> None:
    """The data-received timestamp is set once a response has been ingested."""
    state = hass.states.get("sensor.lumen_data_received")
    assert state is not None
    assert state.state not in ("unknown", "unavailable")


async def test_reenabled_parity_sensor_present(hass: HomeAssistant, setup_lumen: MockConfigEntry) -> None:
    """A sensor re-enabled for parity (CT clamp / inverter current) now has a state."""
    state = hass.states.get("sensor.lumen_inverter_current")
    assert state is not None
    assert float(state.state) == 0.18  # reg 18 * 0.01 A
