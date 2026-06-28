"""Number platform for Lumen — writable hold registers."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from luxmodbus import HOLD_REGISTERS, Measurement, RegisterDef, encode_value, find_hold

from .coordinator import LumenCoordinator

_DEVICE_CLASSES: dict[Measurement, NumberDeviceClass | None] = {
    Measurement.POWER: NumberDeviceClass.POWER,
    Measurement.VOLTAGE: NumberDeviceClass.VOLTAGE,
    Measurement.CURRENT: NumberDeviceClass.CURRENT,
    Measurement.FREQUENCY: NumberDeviceClass.FREQUENCY,
    Measurement.TEMPERATURE: NumberDeviceClass.TEMPERATURE,
}


@dataclass(frozen=True, kw_only=True)
class LumenNumberEntityDescription(NumberEntityDescription):
    """Describes a Lumen number, tied to a writable hold register."""

    register_key: str
    register_address: int


def _description(defn: RegisterDef) -> LumenNumberEntityDescription:
    """Build an entity description from one writable hold register definition."""
    return LumenNumberEntityDescription(
        key=defn.key,
        register_key=defn.key,
        register_address=defn.address,
        name=defn.name,
        native_unit_of_measurement=defn.unit,
        device_class=_DEVICE_CLASSES.get(defn.measurement),
        native_min_value=defn.value_min,
        native_max_value=defn.value_max,
        native_step=defn.scale,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=defn.enabled_default,
    )


NUMBER_DESCRIPTIONS: tuple[LumenNumberEntityDescription, ...] = tuple(
    _description(defn) for defn in HOLD_REGISTERS if defn.writable
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lumen numbers from a config entry."""
    coordinator: LumenCoordinator = entry.runtime_data
    async_add_entities(LumenNumber(coordinator, description) for description in NUMBER_DESCRIPTIONS)


class LumenNumber(CoordinatorEntity[LumenCoordinator], NumberEntity):
    """A writable hold register surfaced as a number."""

    _attr_has_entity_name = True
    entity_description: LumenNumberEntityDescription

    def __init__(self, coordinator: LumenCoordinator, description: LumenNumberEntityDescription) -> None:
        """Initialise the number from its description."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.serial_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float | int | None:
        """Return the latest decoded value for this register."""
        value = self.coordinator.data.get(self.entity_description.register_key)
        return value if isinstance(value, int | float) else None

    async def async_set_native_value(self, value: float) -> None:
        """Encode the value (scale + bounds) and write it to the hold register."""
        defn = find_hold(self.entity_description.register_key)
        assert defn is not None  # description was built from HOLD_REGISTERS
        try:
            raw = encode_value(defn, value)
        except ValueError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_write_register(self.entity_description.register_address, raw)
