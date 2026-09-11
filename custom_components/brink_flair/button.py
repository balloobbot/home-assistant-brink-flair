"""The appliance's two one-shot commands.

Both are write-only registers: a read of either answers whether the action
ran and clears itself doing so, which is why the library never polls them and
why there is nothing to show but the button.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from modbus_connection import ModbusError

from .brink_flair_modbus import BrinkFlair
from .coordinator import BrinkFlairConfigEntry, BrinkFlairCoordinator
from .entity import BrinkFlairEntity, write_error

PARALLEL_UPDATES = 1

ACTION_REQUESTED = 1
"""The only value the spec gives either command register a meaning for."""


@dataclass(frozen=True, kw_only=True)
class BrinkFlairButtonDescription(ButtonEntityDescription):
    """Describe a one-shot command."""

    press_fn: Callable[[BrinkFlair], Coroutine[Any, Any, None]]


BUTTONS: tuple[BrinkFlairButtonDescription, ...] = (
    BrinkFlairButtonDescription(
        key="reset_filter_warning",
        translation_key="reset_filter_warning",
        press_fn=lambda device: device.commands.write(
            "reset_filter_warning", ACTION_REQUESTED
        ),
    ),
    BrinkFlairButtonDescription(
        key="appliance_reset",
        translation_key="appliance_reset",
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda device: device.commands.write(
            "appliance_reset", ACTION_REQUESTED
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BrinkFlairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the command buttons."""
    coordinator = entry.runtime_data.readings
    async_add_entities(
        BrinkFlairButton(coordinator, description) for description in BUTTONS
    )


class BrinkFlairButton(BrinkFlairEntity, ButtonEntity):
    """One command the appliance takes."""

    entity_description: BrinkFlairButtonDescription

    def __init__(
        self,
        coordinator: BrinkFlairCoordinator,
        description: BrinkFlairButtonDescription,
    ) -> None:
        """Tie the button to the poll that says the appliance is reachable."""
        super().__init__(coordinator, description, "measurements")

    async def async_press(self) -> None:
        """Send the command."""
        try:
            await self.entity_description.press_fn(self.device)
        except ModbusError as err:
            raise write_error(err) from err
