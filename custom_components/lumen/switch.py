"""Switch platform for Lumen — bit-flag hold registers (registers 21 / 110)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from luxmodbus import FLAG_REGISTERS, FlagDef

from .coordinator import LumenCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lumen switches from a config entry."""
    coordinator: LumenCoordinator = entry.runtime_data
    async_add_entities(
        LumenSwitch(coordinator, flag_register.address, flag)
        for flag_register in FLAG_REGISTERS
        for flag in flag_register.flags
    )


class LumenSwitch(CoordinatorEntity[LumenCoordinator], SwitchEntity):
    """A single bit of a flag register surfaced as a switch."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: LumenCoordinator, address: int, flag: FlagDef) -> None:
        """Initialise the switch from its flag definition."""
        super().__init__(coordinator)
        self._address = address
        self._flag = flag
        self._attr_name = flag.name
        self._attr_unique_id = f"{coordinator.serial_id}_{flag.key}"
        self._attr_device_info = coordinator.device_info
        self._attr_entity_registry_enabled_default = flag.enabled_default

    @property
    def is_on(self) -> bool | None:
        """Return whether the flag bit is set, or None if not yet read."""
        value = self.coordinator.data.get(self._flag.key)
        return bool(value) if value is not None else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Set the flag bit."""
        await self.coordinator.async_set_flag(self._address, self._flag, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Clear the flag bit."""
        await self.coordinator.async_set_flag(self._address, self._flag, False)
