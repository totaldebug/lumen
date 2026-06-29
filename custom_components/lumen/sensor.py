"""Sensor platform for Lumen — entity descriptions generated from the register map."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
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
from luxmodbus import INPUT_REGISTERS, Measurement, RegisterDef, decode_status

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


# --- Derived sensors: values computed from several decoded registers ---------


def _sum(*keys: str) -> Callable[[Mapping[str, Any]], float | None]:
    """Sum the present numeric values for ``keys`` (None if none are present)."""

    def _compute(data: Mapping[str, Any]) -> float | None:
        values = [data[k] for k in keys if isinstance(data.get(k), int | float)]
        return round(sum(values), 1) if values else None

    return _compute


def _difference(positive: str, negative: str) -> Callable[[Mapping[str, Any]], float | None]:
    """Signed flow: ``positive`` minus ``negative`` (None if neither is present)."""

    def _compute(data: Mapping[str, Any]) -> float | None:
        hi, lo = data.get(positive), data.get(negative)
        if not isinstance(hi, int | float) and not isinstance(lo, int | float):
            return None
        return round(float(hi or 0) - float(lo or 0), 1)

    return _compute


def _status_text(data: Mapping[str, Any]) -> str | None:
    """Map the raw status code to its operating-state label."""
    value = data.get("status")
    return decode_status(int(value)) if isinstance(value, int | float) else None


def _passthrough(key: str) -> Callable[[Mapping[str, Any]], str | None]:
    """Surface a pre-computed string the coordinator stored under ``key`` (e.g. model)."""

    def _compute(data: Mapping[str, Any]) -> str | None:
        value = data.get(key)
        return value if isinstance(value, str) else None

    return _compute


@dataclass(frozen=True, kw_only=True)
class LumenDerivedSensorEntityDescription(SensorEntityDescription):
    """A sensor whose value is computed from the decoded register data."""

    compute: Callable[[Mapping[str, Any]], float | str | None]


DERIVED_DESCRIPTIONS: tuple[LumenDerivedSensorEntityDescription, ...] = (
    LumenDerivedSensorEntityDescription(
        key="solar_power",
        name="Solar Output",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        compute=_sum("pv1_power", "pv2_power", "pv3_power"),
    ),
    LumenDerivedSensorEntityDescription(
        key="solar_energy_today",
        name="Solar Output Daily",
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        compute=_sum("pv1_energy_today", "pv2_energy_today", "pv3_energy_today"),
    ),
    LumenDerivedSensorEntityDescription(
        key="solar_energy_total",
        name="Solar Output Total",
        native_unit_of_measurement="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        compute=_sum("pv1_energy_total", "pv2_energy_total", "pv3_energy_total"),
    ),
    LumenDerivedSensorEntityDescription(
        key="battery_flow",
        name="Battery Flow",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        compute=_difference("battery_charge_power", "battery_discharge_power"),
    ),
    LumenDerivedSensorEntityDescription(
        key="grid_flow",
        name="Grid Flow",
        native_unit_of_measurement="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        compute=_difference("power_to_grid", "power_from_grid"),
    ),
    LumenDerivedSensorEntityDescription(
        key="status_text",
        name="Status (Text)",
        entity_category=EntityCategory.DIAGNOSTIC,
        compute=_status_text,
    ),
    LumenDerivedSensorEntityDescription(
        key="inverter_model",
        name="Inverter Model",
        entity_category=EntityCategory.DIAGNOSTIC,
        compute=_passthrough("inverter_model"),
    ),
    LumenDerivedSensorEntityDescription(
        key="firmware_version",
        name="Firmware Version",
        entity_category=EntityCategory.DIAGNOSTIC,
        compute=_passthrough("firmware_version"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Lumen sensors from a config entry."""
    coordinator: LumenCoordinator = entry.runtime_data
    entities: list[SensorEntity] = [LumenSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS]
    entities += [LumenDerivedSensor(coordinator, description) for description in DERIVED_DESCRIPTIONS]
    entities.append(LumenDataReceivedSensor(coordinator))
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


class LumenDerivedSensor(CoordinatorEntity[LumenCoordinator], SensorEntity):
    """A sensor whose value is computed from several decoded registers."""

    _attr_has_entity_name = True
    entity_description: LumenDerivedSensorEntityDescription

    def __init__(self, coordinator: LumenCoordinator, description: LumenDerivedSensorEntityDescription) -> None:
        """Initialise the derived sensor from its description."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.serial_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float | str | None:
        """Compute the value from the coordinator's decoded data."""
        return self.entity_description.compute(self.coordinator.data)


class LumenDataReceivedSensor(CoordinatorEntity[LumenCoordinator], SensorEntity):
    """Timestamp of the most recent data received from the inverter."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_name = "Data Received"

    def __init__(self, coordinator: LumenCoordinator) -> None:
        """Initialise the data-received timestamp sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.serial_id}_data_received"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> datetime | None:
        """Return when data was last received, or None before the first response."""
        return self.coordinator.last_received


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
