"""Sensor platform for Lumen — entity descriptions generated from the register map."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from luxmodbus import INPUT_REGISTERS, Measurement, RegisterDef

from .coordinator import LumenCoordinator

# Map the library's neutral measurement kind to HA device/state classes.
_CLASSES: dict[Measurement, tuple[SensorDeviceClass | None, SensorStateClass | None]] = {
    Measurement.POWER: (SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    Measurement.APPARENT_POWER: (SensorDeviceClass.APPARENT_POWER, SensorStateClass.MEASUREMENT),
    Measurement.REACTIVE_POWER: (SensorDeviceClass.REACTIVE_POWER, SensorStateClass.MEASUREMENT),
    Measurement.ENERGY: (SensorDeviceClass.ENERGY, SensorStateClass.TOTAL_INCREASING),
    Measurement.VOLTAGE: (SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT),
    Measurement.CURRENT: (SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT),
    Measurement.FREQUENCY: (SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT),
    Measurement.TEMPERATURE: (SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
    Measurement.PERCENT: (None, SensorStateClass.MEASUREMENT),
    Measurement.POWER_FACTOR: (SensorDeviceClass.POWER_FACTOR, SensorStateClass.MEASUREMENT),
    Measurement.DURATION: (SensorDeviceClass.DURATION, None),
    Measurement.COUNT: (None, SensorStateClass.MEASUREMENT),
    Measurement.ENUM: (None, None),
    Measurement.NONE: (None, None),
}


@dataclass(frozen=True, kw_only=True)
class LumenSensorEntityDescription(SensorEntityDescription):
    """Describes a Lumen sensor, tied to a register key in the decoded data."""

    register_key: str


def _description(defn: RegisterDef) -> LumenSensorEntityDescription:
    """Build an entity description from one input register definition."""
    device_class, state_class = _CLASSES[defn.measurement]
    if defn.key in ("soc", "soh"):
        device_class = SensorDeviceClass.BATTERY
    return LumenSensorEntityDescription(
        key=defn.key,
        register_key=defn.key,
        name=defn.name,
        native_unit_of_measurement=defn.unit,
        device_class=device_class,
        state_class=state_class,
        entity_registry_enabled_default=defn.enabled_default,
    )


SENSOR_DESCRIPTIONS: tuple[LumenSensorEntityDescription, ...] = tuple(_description(defn) for defn in INPUT_REGISTERS)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lumen sensors from a config entry."""
    coordinator: LumenCoordinator = entry.runtime_data
    entities: list[SensorEntity] = [LumenSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS]
    entities.append(LumenUndecodedRegistersSensor(coordinator))
    async_add_entities(entities)


class LumenSensor(CoordinatorEntity[LumenCoordinator], SensorEntity):
    """A single decoded register surfaced as a sensor."""

    _attr_has_entity_name = True
    entity_description: LumenSensorEntityDescription

    def __init__(self, coordinator: LumenCoordinator, description: LumenSensorEntityDescription) -> None:
        """Initialise the sensor from its description."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.serial_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float | int | str | None:
        """Return the latest decoded value for this register."""
        return self.coordinator.data.get(self.entity_description.register_key)


class LumenUndecodedRegistersSensor(CoordinatorEntity[LumenCoordinator], SensorEntity):
    """Diagnostic sensor counting registers seen in traffic but absent from the map."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:help-circle-outline"
    _attr_name = "Undecoded registers"

    def __init__(self, coordinator: LumenCoordinator) -> None:
        """Initialise the diagnostic sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.serial_id}_undecoded_registers"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> int:
        """Return the number of distinct unmapped registers seen so far."""
        return self.coordinator.discovery.count()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """List each unmapped register with its bank, address, last value and sightings."""
        registers = [
            {
                "bank": record.bank.value,
                "address": record.address,
                "last_value": record.last_value,
                "times_seen": record.times_seen,
            }
            for record in sorted(
                self.coordinator.discovery.unknown.values(),
                key=lambda record: (record.bank.value, record.address),
            )
        ]
        return {"registers": registers}
