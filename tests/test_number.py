"""Tests for the Lumen number platform."""

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lumen.number import NUMBER_DESCRIPTIONS, LumenNumber

ENTITY = "number.lumen_system_charge_power_rate"


def _number(entry: MockConfigEntry, key: str) -> LumenNumber:
    """Build a LumenNumber for ``key`` against the entry's live coordinator."""
    description = next(d for d in NUMBER_DESCRIPTIONS if d.key == key)
    return LumenNumber(entry.runtime_data, description)


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


async def test_number_write_encodes_scale_and_bounds(hass: HomeAssistant, setup_lumen: MockConfigEntry) -> None:
    """A scaled write goes through encode_value, and out-of-range raises."""
    coordinator = setup_lumen.runtime_data
    number = _number(setup_lumen, "float_charge_voltage")  # addr 144, scale 0.1, 50-56 V
    await number.async_set_native_value(53.0)
    assert coordinator.raw_hold(144) == 530  # 53.0 / 0.1
    with pytest.raises(HomeAssistantError):
        await number.async_set_native_value(70.0)  # above value_max 56.0


async def test_number_write_signed_register(hass: HomeAssistant, setup_lumen: MockConfigEntry) -> None:
    """A signed (s16) hold encodes a negative value as two's complement."""
    coordinator = setup_lumen.runtime_data
    number = _number(setup_lumen, "lead_acid_temp_lower_discharge")  # addr 106, s16, 0.1 °C
    await number.async_set_native_value(-20.0)
    assert coordinator.raw_hold(106) == 0xFF38  # -200 as u16
