"""Tests for the Lumen switch platform."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

ENTITY = "switch.lumen_ac_charge_enable"


async def test_switch_reflects_flag_bit(hass: HomeAssistant, setup_lumen: MockConfigEntry) -> None:
    """The switch reflects its bit in flag register 21 (raw value 21)."""
    # reg 21 == 0b10101 -> bit 7 (AC charge) is clear.
    assert hass.states.get(ENTITY).state == "off"
    # bit 0 (EPS enable) is set.
    assert hass.states.get("switch.lumen_off_grid_eps_enable").state == "on"


async def test_switch_turn_on_writes_flag(hass: HomeAssistant, setup_lumen: MockConfigEntry) -> None:
    """Turning the switch on sets its bit via read-modify-write."""
    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": ENTITY},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY).state == "on"
