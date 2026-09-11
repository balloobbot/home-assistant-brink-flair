"""The base entity: one attribute of one sub-system of the appliance.

An entity names the sub-system it reads from. The coordinator's data is the
library's ``UpdateReport``, so "is my sub-system currently answering?" is a
membership test rather than a guess — a pulled CO2 board takes its own
entities unavailable and leaves the rest alone.
"""

from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from modbus_connection import ModbusError

from .brink_flair_modbus import BrinkFlair
from .const import DOMAIN
from .coordinator import BrinkFlairCoordinator, describe


def write_error(err: ModbusError) -> HomeAssistantError:
    """The error a refused write surfaces to the user as."""
    return HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key="write_failed",
        translation_placeholders={"error": describe(err)},
    )


class BrinkFlairEntity(CoordinatorEntity[BrinkFlairCoordinator]):
    """An entity backed by one of the appliance's sub-systems."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: BrinkFlairCoordinator,
        description: EntityDescription,
        report_name: str,
    ) -> None:
        """Tie the entity to the sub-system whose report line covers it."""
        super().__init__(coordinator)
        self.entity_description = description
        self._report_name = report_name
        self._attr_unique_id = f"{coordinator.config_entry.unique_id}-{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def device(self) -> BrinkFlair:
        """The appliance this entity reads."""
        return self.coordinator.device

    @property
    def available(self) -> bool:
        """Whether this entity's own sub-system answered the last poll."""
        return super().available and self._report_name in self.coordinator.data.updated
