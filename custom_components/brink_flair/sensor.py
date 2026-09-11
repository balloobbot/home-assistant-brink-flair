"""Sensors for the Brink Flair integration.

Every reading the appliance answers for, plus the two modules' analogue
inputs and outputs. The coded registers become enum sensors, so a status
reads as ``running`` rather than ``4``; their options come straight off the
library's enums, which are the spec's own code lists.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .brink_flair_modbus import (
    ActiveFunction,
    BrinkFlair,
    BypassStatus,
    Co2SensorStatus,
    EbusPowerStatus,
    FanControlType,
    FanStatus,
    FlowSwitchPosition,
    FrostStatus,
    GeoHeatExchangerStatus,
    PreheaterStatus,
    SignalOutputState,
    VentilationMode,
)
from .coordinator import BrinkFlairConfigEntry, BrinkFlairCoordinator
from .entity import BrinkFlairEntity

PARALLEL_UPDATES = 0

MASS_FLOW_UNIT = "kg/h"
"""No Home Assistant unit constant covers a mass flow, so it is a plain label."""


def options(enum_type: type[IntEnum]) -> list[str]:
    """The states an enum register can report, as Home Assistant spells them."""
    return [member.name.lower() for member in enum_type]


def state_of(member: IntEnum | None) -> str | None:
    """One enum reading as its state string."""
    return member.name.lower() if member is not None else None


@dataclass(frozen=True, kw_only=True)
class BrinkFlairSensorDescription(SensorEntityDescription):
    """Describe a sensor backed by one attribute of the appliance."""

    value_fn: Callable[[BrinkFlair], StateType]
    report_name: str


def _measurement(
    key: str, value_fn: Callable[[BrinkFlair], StateType], **kwargs: object
) -> BrinkFlairSensorDescription:
    """A sensor off the main readings block, measured every poll."""
    return BrinkFlairSensorDescription(
        key=key,
        translation_key=key,
        report_name="measurements",
        value_fn=value_fn,
        state_class=SensorStateClass.MEASUREMENT,
        **kwargs,  # type: ignore[arg-type]
    )


def _status(
    key: str, enum_type: type[IntEnum], value_fn: Callable[[BrinkFlair], StateType]
) -> BrinkFlairSensorDescription:
    """A coded register off the main readings block, as an enum sensor."""
    return BrinkFlairSensorDescription(
        key=key,
        translation_key=key,
        report_name="measurements",
        value_fn=value_fn,
        device_class=SensorDeviceClass.ENUM,
        options=options(enum_type),
    )


TEMPERATURE = {
    "device_class": SensorDeviceClass.TEMPERATURE,
    "native_unit_of_measurement": UnitOfTemperature.CELSIUS,
}
HUMIDITY = {
    "device_class": SensorDeviceClass.HUMIDITY,
    "native_unit_of_measurement": PERCENTAGE,
}
FLOW = {
    "device_class": SensorDeviceClass.VOLUME_FLOW_RATE,
    "native_unit_of_measurement": UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
}
PRESSURE = {
    "device_class": SensorDeviceClass.PRESSURE,
    "native_unit_of_measurement": UnitOfPressure.PA,
}
SPEED = {
    "native_unit_of_measurement": REVOLUTIONS_PER_MINUTE,
    "entity_category": EntityCategory.DIAGNOSTIC,
}
PERCENT = {"native_unit_of_measurement": PERCENTAGE}
VOLTAGE = {
    "device_class": SensorDeviceClass.VOLTAGE,
    "native_unit_of_measurement": UnitOfElectricPotential.VOLT,
    "entity_category": EntityCategory.DIAGNOSTIC,
}

MEASUREMENT_SENSORS: tuple[BrinkFlairSensorDescription, ...] = (
    _measurement("supply_flow", lambda d: d.measurements.supply_flow, **FLOW),
    _measurement("exhaust_flow", lambda d: d.measurements.exhaust_flow, **FLOW),
    _measurement(
        "supply_flow_setpoint",
        lambda d: d.measurements.supply_flow_setpoint,
        entity_registry_enabled_default=False,
        **FLOW,
    ),
    _measurement(
        "exhaust_flow_setpoint",
        lambda d: d.measurements.exhaust_flow_setpoint,
        entity_registry_enabled_default=False,
        **FLOW,
    ),
    _measurement(
        "supply_mass_flow",
        lambda d: d.measurements.supply_mass_flow,
        native_unit_of_measurement=MASS_FLOW_UNIT,
        entity_registry_enabled_default=False,
    ),
    _measurement(
        "exhaust_mass_flow",
        lambda d: d.measurements.exhaust_mass_flow,
        native_unit_of_measurement=MASS_FLOW_UNIT,
        entity_registry_enabled_default=False,
    ),
    _measurement(
        "supply_fan_temperature",
        lambda d: d.measurements.supply_fan_temperature,
        **TEMPERATURE,
    ),
    _measurement(
        "exhaust_fan_temperature",
        lambda d: d.measurements.exhaust_fan_temperature,
        **TEMPERATURE,
    ),
    _measurement(
        "supply_humidity", lambda d: d.measurements.supply_humidity, **HUMIDITY
    ),
    _measurement(
        "exhaust_humidity", lambda d: d.measurements.exhaust_humidity, **HUMIDITY
    ),
    _measurement(
        "ntc1_temperature", lambda d: d.measurements.ntc1_temperature, **TEMPERATURE
    ),
    _measurement(
        "ntc2_temperature", lambda d: d.measurements.ntc2_temperature, **TEMPERATURE
    ),
    _measurement("rht_humidity", lambda d: d.measurements.rht_humidity, **HUMIDITY),
    _measurement(
        "supply_pressure", lambda d: d.measurements.supply_pressure, **PRESSURE
    ),
    _measurement(
        "exhaust_pressure", lambda d: d.measurements.exhaust_pressure, **PRESSURE
    ),
    _measurement(
        "supply_fan_speed", lambda d: d.measurements.supply_fan_speed, **SPEED
    ),
    _measurement(
        "exhaust_fan_speed", lambda d: d.measurements.exhaust_fan_speed, **SPEED
    ),
    _measurement(
        "supply_anemometer_speed",
        lambda d: d.measurements.supply_anemometer_speed,
        entity_registry_enabled_default=False,
        **SPEED,
    ),
    _measurement(
        "exhaust_anemometer_speed",
        lambda d: d.measurements.exhaust_anemometer_speed,
        entity_registry_enabled_default=False,
        **SPEED,
    ),
    _measurement(
        "preheater_capacity", lambda d: d.measurements.preheater_capacity, **PERCENT
    ),
    _measurement(
        "frost_heater_power", lambda d: d.measurements.frost_heater_power, **PERCENT
    ),
    _measurement(
        "fan_frost_reduction", lambda d: d.measurements.fan_frost_reduction, **PERCENT
    ),
    _measurement(
        "bypass_position",
        lambda d: d.measurements.bypass_position,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    _measurement(
        "filter_hours",
        lambda d: d.measurements.filter_hours,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
    ),
)

STATUS_SENSORS: tuple[BrinkFlairSensorDescription, ...] = (
    _status(
        "active_function",
        ActiveFunction,
        lambda d: state_of(d.measurements.active_function),
    ),
    _status(
        "fan_control_type",
        FanControlType,
        lambda d: state_of(d.measurements.fan_control_type),
    ),
    _status(
        "ventilation_mode",
        VentilationMode,
        lambda d: state_of(d.measurements.ventilation_mode),
    ),
    _status(
        "supply_fan_status",
        FanStatus,
        lambda d: state_of(d.measurements.supply_fan_status),
    ),
    _status(
        "exhaust_fan_status",
        FanStatus,
        lambda d: state_of(d.measurements.exhaust_fan_status),
    ),
    _status(
        "bypass_status", BypassStatus, lambda d: state_of(d.measurements.bypass_status)
    ),
    _status(
        "preheater_status",
        PreheaterStatus,
        lambda d: state_of(d.measurements.preheater_status),
    ),
    _status(
        "frost_status", FrostStatus, lambda d: state_of(d.measurements.frost_status)
    ),
    _status(
        "flow_switch_position",
        FlowSwitchPosition,
        lambda d: state_of(d.measurements.flow_switch_position),
    ),
    _status(
        "signal_output",
        SignalOutputState,
        lambda d: state_of(d.measurements.signal_output),
    ),
    _status(
        "ebus_power_status",
        EbusPowerStatus,
        lambda d: state_of(d.measurements.ebus_power_status),
    ),
)

# The counters. These outlive the appliance being reachable, so they stay
# available and restore their last value across a restart.
TOTAL_SENSORS: tuple[BrinkFlairSensorDescription, ...] = (
    BrinkFlairSensorDescription(
        key="operating_time",
        translation_key="operating_time",
        report_name="measurements",
        value_fn=lambda d: d.measurements.operating_time,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    BrinkFlairSensorDescription(
        key="filter_flow",
        translation_key="filter_flow",
        report_name="measurements",
        value_fn=lambda d: d.measurements.filter_flow,
        device_class=SensorDeviceClass.VOLUME,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    BrinkFlairSensorDescription(
        key="total_flow",
        translation_key="total_flow",
        report_name="measurements",
        value_fn=lambda d: d.measurements.total_flow,
        device_class=SensorDeviceClass.VOLUME,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
)

GEO_SENSORS: tuple[BrinkFlairSensorDescription, ...] = (
    BrinkFlairSensorDescription(
        key="geo_heat_exchanger_status",
        translation_key="geo_heat_exchanger_status",
        report_name="geo_heat_exchanger",
        value_fn=lambda d: state_of(
            d.geo_heat_exchanger.status if d.geo_heat_exchanger else None
        ),
        device_class=SensorDeviceClass.ENUM,
        options=options(GeoHeatExchangerStatus),
    ),
)


def _co2_value(index: int) -> Callable[[BrinkFlair], StateType]:
    """Read one CO2 sensor's concentration."""
    return lambda d: (
        getattr(d.co2_sensors, f"sensor_{index}_value") if d.co2_sensors else None
    )


def _co2_status(index: int) -> Callable[[BrinkFlair], StateType]:
    """Read one CO2 sensor's own status."""
    return lambda d: state_of(
        getattr(d.co2_sensors, f"sensor_{index}_status") if d.co2_sensors else None
    )


CO2_SENSORS: tuple[BrinkFlairSensorDescription, ...] = tuple(
    description
    for index in (1, 2, 3, 4)
    for description in (
        BrinkFlairSensorDescription(
            key=f"co2_sensor_{index}",
            translation_key="co2_sensor",
            translation_placeholders={"index": str(index)},
            report_name="co2_sensors",
            value_fn=_co2_value(index),
            device_class=SensorDeviceClass.CO2,
            native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        BrinkFlairSensorDescription(
            key=f"co2_sensor_{index}_status",
            translation_key="co2_sensor_status",
            translation_placeholders={"index": str(index)},
            report_name="co2_sensors",
            value_fn=_co2_status(index),
            device_class=SensorDeviceClass.ENUM,
            options=options(Co2SensorStatus),
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
    )
)

USER_INTERFACE_SENSORS: tuple[BrinkFlairSensorDescription, ...] = (
    BrinkFlairSensorDescription(
        key="display_switch",
        translation_key="display_switch",
        report_name="user_interface",
        value_fn=lambda d: d.user_interface.local_switch if d.user_interface else None,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

EXTENSION_SENSORS: tuple[BrinkFlairSensorDescription, ...] = (
    BrinkFlairSensorDescription(
        key="extension_temperature",
        translation_key="extension_temperature",
        report_name="extension",
        value_fn=lambda d: d.extension.ntc_temperature if d.extension else None,
        state_class=SensorStateClass.MEASUREMENT,
        **TEMPERATURE,  # type: ignore[arg-type]
    ),
    *(
        BrinkFlairSensorDescription(
            key=f"extension_analogue_{direction}_{index}",
            translation_key=f"extension_analogue_{direction}",
            translation_placeholders={"index": str(index)},
            report_name="extension",
            value_fn=(
                lambda d, attribute=f"analogue_{direction}_{index}": (  # type: ignore[misc]
                    getattr(d.extension, attribute) if d.extension else None
                )
            ),
            state_class=SensorStateClass.MEASUREMENT,
            **VOLTAGE,  # type: ignore[arg-type]
        )
        for direction in ("input", "output")
        for index in (1, 2)
    ),
)

ALL_SENSORS: tuple[BrinkFlairSensorDescription, ...] = (
    MEASUREMENT_SENSORS
    + STATUS_SENSORS
    + GEO_SENSORS
    + CO2_SENSORS
    + USER_INTERFACE_SENSORS
    + EXTENSION_SENSORS
)


def sub_system_present(device: BrinkFlair, report_name: str) -> bool:
    """Whether the appliance carries the sub-system a description names."""
    return report_name in ("measurements", "control", "parameters") or (
        getattr(device, report_name) is not None
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BrinkFlairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a sensor per reading the appliance actually has."""
    coordinator = entry.runtime_data.readings
    device = coordinator.device

    async_add_entities(
        BrinkFlairSensor(coordinator, description)
        for description in ALL_SENSORS
        if sub_system_present(device, description.report_name)
    )
    async_add_entities(
        BrinkFlairTotalSensor(coordinator, description) for description in TOTAL_SENSORS
    )


class BrinkFlairSensor(BrinkFlairEntity, SensorEntity):
    """One reading of the appliance."""

    entity_description: BrinkFlairSensorDescription

    def __init__(
        self,
        coordinator: BrinkFlairCoordinator,
        description: BrinkFlairSensorDescription,
    ) -> None:
        """Bind the sensor to the sub-system its reading comes from."""
        super().__init__(coordinator, description, description.report_name)

    @property
    def native_value(self) -> StateType:
        """The reading, or ``None`` while the appliance has not given one."""
        return self.entity_description.value_fn(self.device)


class BrinkFlairTotalSensor(BrinkFlairEntity, RestoreSensor):
    """A lifetime counter: it holds its last value and may outlive the link.

    A gap in one of these damages long-term statistics, and an appliance is
    legitimately unreachable now and then, so they stay available and restore
    across a restart.
    """

    entity_description: BrinkFlairSensorDescription

    def __init__(
        self,
        coordinator: BrinkFlairCoordinator,
        description: BrinkFlairSensorDescription,
    ) -> None:
        """Bind the counter to the sub-system it comes from."""
        super().__init__(coordinator, description, description.report_name)

    @property
    def available(self) -> bool:
        """Always: a counter keeps its last value when the appliance is gone."""
        return True

    async def async_added_to_hass(self) -> None:
        """Restore the value this counter last had."""
        await super().async_added_to_hass()
        if (last_data := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = last_data.native_value
        self._process_data()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._process_data()
        super()._handle_coordinator_update()

    def _process_data(self) -> None:
        value = self.entity_description.value_fn(self.device)
        if value is None:
            return
        self._attr_native_value = value
