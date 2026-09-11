"""Settings that pick one of a fixed set of options.

These are holding registers in the appliance's settings block, so they hang
off the settings coordinator — a slow poll, because nothing but a write
changes them. A write refreshes that coordinator straight away rather than
waiting a quarter of an hour for the new value to show.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import IntEnum

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from modbus_connection import ModbusError

from .brink_flair_modbus import (
    BrinkFlair,
    BypassMode,
    FlowType,
    SignalOutputMode,
)
from .coordinator import BrinkFlairConfigEntry, BrinkFlairCoordinator
from .entity import BrinkFlairEntity, write_error

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class BrinkFlairSelectDescription(SelectEntityDescription):
    """Describe a setting whose values are one of an enum's members."""

    enum_type: type[IntEnum]
    field: str
    value_fn: Callable[[BrinkFlair], IntEnum | None]


SELECTS: tuple[BrinkFlairSelectDescription, ...] = (
    BrinkFlairSelectDescription(
        key="bypass_mode",
        translation_key="bypass_mode",
        enum_type=BypassMode,
        field="bypass_mode",
        value_fn=lambda device: device.parameters.bypass_mode,
        options=[mode.name.lower() for mode in BypassMode],
    ),
    BrinkFlairSelectDescription(
        key="flow_type",
        translation_key="flow_type",
        enum_type=FlowType,
        field="flow_type",
        value_fn=lambda device: device.parameters.flow_type,
        options=[mode.name.lower() for mode in FlowType],
        entity_category=EntityCategory.CONFIG,
    ),
    BrinkFlairSelectDescription(
        key="signal_output_mode",
        translation_key="signal_output_mode",
        enum_type=SignalOutputMode,
        field="signal_output_mode",
        value_fn=lambda device: device.parameters.signal_output_mode,
        options=[mode.name.lower() for mode in SignalOutputMode],
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BrinkFlairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the settings that pick from a fixed list."""
    coordinator = entry.runtime_data.settings
    async_add_entities(
        BrinkFlairSelect(coordinator, description) for description in SELECTS
    )


class BrinkFlairSelect(BrinkFlairEntity, SelectEntity):
    """One setting of the appliance, chosen from its own code list."""

    entity_description: BrinkFlairSelectDescription

    def __init__(
        self,
        coordinator: BrinkFlairCoordinator,
        description: BrinkFlairSelectDescription,
    ) -> None:
        """Bind the setting to the settings block."""
        super().__init__(coordinator, description, "parameters")

    @property
    def current_option(self) -> str | None:
        """The setting as it was last read."""
        value = self.entity_description.value_fn(self.device)
        return value.name.lower() if value is not None else None

    async def async_select_option(self, option: str) -> None:
        """Write the setting, then read the settings back."""
        member = self.entity_description.enum_type[option.upper()]
        try:
            await self.device.parameters.write(self.entity_description.field, member)
        except ModbusError as err:
            raise write_error(err) from err
        await self.coordinator.async_request_refresh()
