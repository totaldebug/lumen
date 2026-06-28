"""Services for the Lumen integration.

Two low-level register services that pair with discovery: probe and poke a
register by address (handy for the long tail not yet in the map). They target a
Lumen device (dongle or inverter) and resolve its coordinator.
"""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_DEVICE_ID
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from luxmodbus import RegisterBank

from .const import DOMAIN
from .coordinator import LumenCoordinator

SERVICE_WRITE_REGISTER = "write_register"
SERVICE_READ_REGISTER = "read_register"
SERVICE_DISCOVER_SWEEP = "discover_sweep"

ATTR_REGISTER = "register"
ATTR_VALUE = "value"
ATTR_BANK = "bank"
ATTR_INPUT_END = "input_end"
ATTR_HOLD_END = "hold_end"

_REGISTER = vol.All(vol.Coerce(int), vol.Range(min=0, max=0xFFFF))
_END = vol.All(vol.Coerce(int), vol.Range(min=1, max=0x10000))

_WRITE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_REGISTER): _REGISTER,
        vol.Required(ATTR_VALUE): _REGISTER,
    }
)

_READ_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Required(ATTR_REGISTER): _REGISTER,
        vol.Optional(ATTR_BANK, default=RegisterBank.INPUT.value): vol.In([bank.value for bank in RegisterBank]),
    }
)

_SWEEP_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Optional(ATTR_INPUT_END, default=256): _END,
        vol.Optional(ATTR_HOLD_END, default=256): _END,
    }
)


def _coordinator_for_device(hass: HomeAssistant, device_id: str) -> LumenCoordinator:
    """Resolve the loaded Lumen coordinator that owns ``device_id``."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        raise ServiceValidationError(f"Device {device_id} not found")
    for entry_id in device.config_entries:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is not None and entry.domain == DOMAIN and entry.state is ConfigEntryState.LOADED:
            return entry.runtime_data
    raise ServiceValidationError(f"Device {device_id} is not a loaded Lumen device")


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the Lumen services (once per Home Assistant instance)."""

    async def _write_register(call: ServiceCall) -> None:
        """Write a single hold register on the targeted inverter."""
        coordinator = _coordinator_for_device(hass, call.data[ATTR_DEVICE_ID])
        await coordinator.async_write_register(call.data[ATTR_REGISTER], call.data[ATTR_VALUE])

    async def _read_register(call: ServiceCall) -> ServiceResponse:
        """Read a single register on demand and return its raw value."""
        coordinator = _coordinator_for_device(hass, call.data[ATTR_DEVICE_ID])
        value = await coordinator.async_read_register(RegisterBank(call.data[ATTR_BANK]), call.data[ATTR_REGISTER])
        return {"value": value}

    async def _discover_sweep(call: ServiceCall) -> ServiceResponse:
        """Read a wide register range to feed discovery; return the unknown count."""
        coordinator = _coordinator_for_device(hass, call.data[ATTR_DEVICE_ID])
        count = await coordinator.async_sweep(input_end=call.data[ATTR_INPUT_END], hold_end=call.data[ATTR_HOLD_END])
        return {"unknown_count": count}

    hass.services.async_register(DOMAIN, SERVICE_WRITE_REGISTER, _write_register, schema=_WRITE_SCHEMA)
    hass.services.async_register(
        DOMAIN,
        SERVICE_READ_REGISTER,
        _read_register,
        schema=_READ_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DISCOVER_SWEEP,
        _discover_sweep,
        schema=_SWEEP_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
