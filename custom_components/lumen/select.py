"""Select platform for Lumen — enumerated hold-register settings (working mode)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from luxmodbus import SELECT_REGISTERS, SelectRegister, decode_select, set_select

from .coordinator import LumenCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lumen select entities from a config entry."""
    coordinator: LumenCoordinator = entry.runtime_data
    async_add_entities(LumenSelect(coordinator, register) for register in SELECT_REGISTERS)


class LumenSelect(CoordinatorEntity[LumenCoordinator], SelectEntity):
    """An enumerated bitfield within a hold register surfaced as a select."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: LumenCoordinator, register: SelectRegister) -> None:
        """Initialise the select from its register definition."""
        super().__init__(coordinator)
        self._register = register
        self._attr_name = register.name
        self._attr_unique_id = f"{coordinator.serial_id}_{register.key}"
        self._attr_device_info = coordinator.device_info
        self._attr_options = list(register.options)
        self._attr_entity_registry_enabled_default = register.enabled_default

    @property
    def current_option(self) -> str | None:
        """Return the selected option, or None if not yet read."""
        raw = self.coordinator.raw_hold(self._register.address)
        return decode_select(raw, self._register) if raw is not None else None

    async def async_select_option(self, option: str) -> None:
        """Write the chosen option to the register via read-modify-write."""
        current = self.coordinator.raw_hold(self._register.address) or 0
        await self.coordinator.async_write_register(self._register.address, set_select(current, self._register, option))
