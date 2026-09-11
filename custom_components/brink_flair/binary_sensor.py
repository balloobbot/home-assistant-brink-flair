"""Binary sensors for the Brink Flair integration.

The filter warning, and the UWA2-E's two digital contacts and two relay
outputs where that module is fitted.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .brink_flair_modbus import BrinkFlair, SignalOutputState
from .coordinator import BrinkFlairConfigEntry, BrinkFlairCoordinator
from .entity import BrinkFlairEntity
from .sensor import sub_system_present

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class BrinkFlairBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a binary sensor backed by one attribute of the appliance."""

    value_fn: Callable[[BrinkFlair], bool | None]
    report_name: str


def _relay(index: int) -> Callable[[BrinkFlair], bool | None]:
    """Whether one UWA2-E relay output is driving 24 V."""

    def value(device: BrinkFlair) -> bool | None:
        if device.extension is None:
            return None
        state = getattr(device.extension, f"relay_output_{index}")
        return state is SignalOutputState.TWENTY_FOUR_VOLT if state else None

    return value


def _contact(index: int) -> Callable[[BrinkFlair], bool | None]:
    """Whether one UWA2-E digital contact is closed."""
    return lambda device: (
        getattr(device.extension, f"contact_{index}_closed")
        if device.extension
        else None
    )


BINARY_SENSORS: tuple[BrinkFlairBinarySensorDescription, ...] = (
    BrinkFlairBinarySensorDescription(
        key="filter_dirty",
        translation_key="filter_dirty",
        report_name="measurements",
        value_fn=lambda device: device.measurements.filter_dirty,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    *(
        BrinkFlairBinarySensorDescription(
            key=f"extension_contact_{index}",
            translation_key="extension_contact",
            translation_placeholders={"index": str(index)},
            report_name="extension",
            value_fn=_contact(index),
            entity_category=EntityCategory.DIAGNOSTIC,
        )
        for index in (1, 2)
    ),
    *(
        BrinkFlairBinarySensorDescription(
            key=f"extension_relay_{index}",
            translation_key="extension_relay",
            translation_placeholders={"index": str(index)},
            report_name="extension",
            value_fn=_relay(index),
            entity_category=EntityCategory.DIAGNOSTIC,
        )
        for index in (1, 2)
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BrinkFlairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the binary sensors the appliance has hardware for."""
    coordinator = entry.runtime_data.readings
    async_add_entities(
        BrinkFlairBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
        if sub_system_present(coordinator.device, description.report_name)
    )


class BrinkFlairBinarySensor(BrinkFlairEntity, BinarySensorEntity):
    """One on/off reading of the appliance."""

    entity_description: BrinkFlairBinarySensorDescription

    def __init__(
        self,
        coordinator: BrinkFlairCoordinator,
        description: BrinkFlairBinarySensorDescription,
    ) -> None:
        """Bind the sensor to the sub-system its reading comes from."""
        super().__init__(coordinator, description, description.report_name)

    @property
    def is_on(self) -> bool | None:
        """The reading, or ``None`` while the appliance has not given one."""
        return self.entity_description.value_fn(self.device)
