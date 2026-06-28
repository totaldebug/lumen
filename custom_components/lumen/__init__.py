"""The Lumen integration — a modern LuxPower inverter integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.typing import ConfigType
from luxmodbus import ClientTransport, ServerTransport, Transport, TransportConnectError

from .const import CONF_DONGLE_SERIAL, CONF_MODE, CONF_SERIAL, MODE_CLIENT
from .coordinator import LumenCoordinator
from .services import async_setup_services

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.EVENT,
    Platform.SELECT,
    Platform.TIME,
]

type LumenConfigEntry = ConfigEntry[LumenCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Lumen integration; registers the register read/write services."""
    async_setup_services(hass)
    return True


def _build_transport(entry: LumenConfigEntry) -> tuple[Transport, bool]:
    """Create the transport for the configured mode; returns (transport, client_mode)."""
    host: str = entry.data[CONF_HOST]
    port: int = entry.data[CONF_PORT]
    if entry.data[CONF_MODE] == MODE_CLIENT:
        return ClientTransport(host, port), True
    return ServerTransport(port=port), False


async def async_setup_entry(hass: HomeAssistant, entry: LumenConfigEntry) -> bool:
    """Set up Lumen from a config entry."""
    transport, client_mode = _build_transport(entry)
    coordinator = LumenCoordinator(
        hass,
        entry,
        transport,
        client_mode=client_mode,
        dongle_serial=entry.data[CONF_DONGLE_SERIAL].encode("ascii"),
        inverter_serial=entry.data[CONF_SERIAL].encode("ascii"),
    )

    try:
        await coordinator.async_setup()
    except TransportConnectError as err:
        raise ConfigEntryNotReady(f"Could not connect to the dongle: {err}") from err

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    # Register the dongle (gateway) device explicitly so the inverter's
    # via_device link resolves even though nothing attaches entities to it.
    dr.async_get(hass).async_get_or_create(config_entry_id=entry.entry_id, **coordinator.dongle_device_info)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LumenConfigEntry) -> bool:
    """Unload a Lumen config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_shutdown()
    return unloaded
