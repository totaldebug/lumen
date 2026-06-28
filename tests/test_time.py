"""Tests for the Lumen time platform."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

ENTITY = "time.lumen_ac_charge_start"


async def test_time_round_trips(hass: HomeAssistant, setup_lumen: MockConfigEntry) -> None:
    """Setting a time packs HH:MM into the register and reads back the same time."""
    # FakeTransport seeds register 68 with raw 68 -> hour 68 is invalid -> unknown.
    assert hass.states.get(ENTITY).state == "unknown"

    await hass.services.async_call(
        "time",
        "set_value",
        {"entity_id": ENTITY, "time": "09:45:00"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY).state == "09:45:00"
