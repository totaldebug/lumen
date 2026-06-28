"""Event platform for Lumen — fires when discovery sees a register for the first time."""

from __future__ import annotations

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from luxmodbus import UnknownRegister

from .coordinator import LumenCoordinator

EVENT_NEW_REGISTER = "new_register"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Lumen discovery event entity from a config entry."""
    coordinator: LumenCoordinator = entry.runtime_data
    async_add_entities([LumenNewRegisterEvent(coordinator)])


class LumenNewRegisterEvent(EventEntity):
    """Fires whenever discovery records a register that was never seen before."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:database-search"
    _attr_name = "New register seen"
    _attr_event_types = [EVENT_NEW_REGISTER]

    def __init__(self, coordinator: LumenCoordinator) -> None:
        """Initialise the event entity."""
        self._coordinator = coordinator
        self._attr_unique_id = f"{coordinator.serial_id}_new_register"
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self) -> None:
        """Subscribe to the coordinator's discovery notifications."""
        await super().async_added_to_hass()
        self.async_on_remove(self._coordinator.add_discovery_listener(self._on_discovered))

    @callback
    def _on_discovered(self, registers: list[UnknownRegister]) -> None:
        """Fire one event per newly-discovered register."""
        for register in registers:
            self._trigger_event(
                EVENT_NEW_REGISTER,
                {
                    "bank": register.bank.value,
                    "address": register.address,
                    "last_value": register.last_value,
                },
            )
            self.async_write_ha_state()
