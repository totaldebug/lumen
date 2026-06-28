"""Tests for the Lumen number platform."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

ENTITY = "number.lumen_system_charge_power_rate"


async def test_number_reads_hold_register(hass: HomeAssistant, setup_lumen: MockConfigEntry) -> None:
    """A number reflects the decoded hold register value (addr 64)."""
    state = hass.states.get(ENTITY)
    assert state is not None
    assert float(state.state) == 64.0


async def test_number_writes_value(hass: HomeAssistant, setup_lumen: MockConfigEntry) -> None:
    """Setting a number writes the register and updates optimistically."""
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": ENTITY, "value": 50},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert float(hass.states.get(ENTITY).state) == 50.0
