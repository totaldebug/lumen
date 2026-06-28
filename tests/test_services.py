"""Tests for the Lumen register services."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lumen.const import DOMAIN

INVERTER_SERIAL = "1234567890"


def _inverter_device_id(hass: HomeAssistant) -> str:
    """Return the registry id of the inverter device."""
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, INVERTER_SERIAL)})
    assert device is not None
    return device.id


async def test_write_register_service(hass: HomeAssistant, setup_lumen: MockConfigEntry) -> None:
    """write_register writes the targeted hold register."""
    await hass.services.async_call(
        DOMAIN,
        "write_register",
        {"device_id": _inverter_device_id(hass), "register": 64, "value": 55},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert setup_lumen.runtime_data.raw_hold(64) == 55


async def test_read_register_service(hass: HomeAssistant, setup_lumen: MockConfigEntry) -> None:
    """read_register returns the raw value (FakeTransport echoes the address)."""
    response = await hass.services.async_call(
        DOMAIN,
        "read_register",
        {"device_id": _inverter_device_id(hass), "register": 15, "bank": "input"},
        blocking=True,
        return_response=True,
    )
    assert response == {"value": 15}


async def test_discover_sweep_finds_unpolled_registers(hass: HomeAssistant, setup_lumen: MockConfigEntry) -> None:
    """discover_sweep reads past the normal poll ranges and records new unknowns."""
    coordinator = setup_lumen.runtime_data
    before = coordinator.discovery.count()

    response = await hass.services.async_call(
        DOMAIN,
        "discover_sweep",
        {"device_id": _inverter_device_id(hass), "input_end": 256, "hold_end": 256},
        blocking=True,
        return_response=True,
    )
    await hass.async_block_till_done()

    assert response["unknown_count"] >= before
    # The normal poll only reaches input 0-199 / hold 0-119; the sweep reaches further.
    assert any(address >= 200 for _bank, address in coordinator.discovery.unknown)
