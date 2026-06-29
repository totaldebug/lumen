"""Binary sensor platform for Lumen — inverter connectivity."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import LumenCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Lumen connectivity binary sensor from a config entry."""
    coordinator: LumenCoordinator = entry.runtime_data
    async_add_entities([LumenConnectivitySensor(coordinator)])


class LumenConnectivitySensor(CoordinatorEntity[LumenCoordinator], BinarySensorEntity):
    """Reports whether Lumen is currently receiving data from the inverter."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_name = "Connectivity"

    def __init__(self, coordinator: LumenCoordinator) -> None:
        """Initialise the connectivity sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.serial_id}_connectivity"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Stay available so the disconnected state shows as 'off', not unavailable."""
        return True

    @property
    def is_on(self) -> bool:
        """True when the most recent poll of (or push from) the inverter succeeded."""
        return self.coordinator.last_update_success
