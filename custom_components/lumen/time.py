"""Time platform for Lumen — charge/discharge schedule slots (packed HH:MM hold registers)."""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from luxmodbus import TIME_REGISTERS, TimeRegister, decode_time, encode_time

from .coordinator import LumenCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lumen schedule time entities from a config entry."""
    coordinator: LumenCoordinator = entry.runtime_data
    async_add_entities(LumenTime(coordinator, register) for register in TIME_REGISTERS)


class LumenTime(CoordinatorEntity[LumenCoordinator], TimeEntity):
    """A schedule edge's time of day, stored as a packed HH:MM hold register."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:clock-outline"

    def __init__(self, coordinator: LumenCoordinator, register: TimeRegister) -> None:
        """Initialise the time entity from its register definition."""
        super().__init__(coordinator)
        self._register = register
        self._attr_name = register.name
        self._attr_unique_id = f"{coordinator.serial_id}_{register.key}"
        self._attr_device_info = coordinator.device_info
        self._attr_entity_registry_enabled_default = register.enabled_default

    @property
    def native_value(self) -> time | None:
        """Return the configured time of day, or None if unread or out of range."""
        raw = self.coordinator.raw_hold(self._register.address)
        if raw is None:
            return None
        hour, minute = decode_time(raw)
        if hour > 23 or minute > 59:
            return None
        return time(hour=hour, minute=minute)

    async def async_set_value(self, value: time) -> None:
        """Write the time of day back to the packed hold register."""
        await self.coordinator.async_write_register(self._register.address, encode_time(value.hour, value.minute))
