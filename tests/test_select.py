"""Tests for the Lumen select platform."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

ENTITY = "select.lumen_on_grid_working_mode"


async def test_select_reflects_register_bit(hass: HomeAssistant, setup_lumen: MockConfigEntry) -> None:
    """The select reads bit 11 of register 110 (FakeTransport raw 110 -> bit clear)."""
    state = hass.states.get(ENTITY)
    assert state.state == "Self-Consumption"
    assert state.attributes["options"] == ["Self-Consumption", "Charge-First"]


async def test_select_option_writes_bit(hass: HomeAssistant, setup_lumen: MockConfigEntry) -> None:
    """Selecting an option writes the bit via read-modify-write."""
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": ENTITY, "option": "Charge-First"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY).state == "Charge-First"
