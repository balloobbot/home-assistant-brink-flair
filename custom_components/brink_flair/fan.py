"""The ventilation itself, as a fan entity.

Setting a preset puts the appliance under Modbus control — the spec's
register 8000 — and hands it the switch position. Turning the entity off puts
the appliance into standby and turning it on brings it back, which is a
different register and works whether or not Modbus is driving the flow.

There is no percentage: the appliance takes a flow in m³/h whose minimum and
maximum the spec says depend on the appliance, and it publishes neither. The
flow rate is a number entity instead, where a bound the integration chose
does not masquerade as the appliance's own.
"""

from __future__ import annotations

from collections.abc import Coroutine
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from modbus_connection import ModbusError

from .brink_flair_modbus import SwitchPosition, VentilationMode
from .coordinator import BrinkFlairConfigEntry, BrinkFlairCoordinator
from .entity import BrinkFlairEntity, write_error

PARALLEL_UPDATES = 1

PRESET_MODES = [position.name.lower() for position in SwitchPosition]
"""Holiday, low, normal and high — the four positions 8001 accepts.

The appliance's own ``auto`` is not among them: register 8001 has no code for
it, so it can be reported but not asked for.
"""


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BrinkFlairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the ventilation entity."""
    async_add_entities([BrinkFlairFan(entry.runtime_data.readings)])


class BrinkFlairFan(BrinkFlairEntity, FanEntity):
    """The appliance's ventilation."""

    _attr_name = None
    _attr_supported_features = (
        FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_preset_modes = PRESET_MODES

    def __init__(self, coordinator: BrinkFlairCoordinator) -> None:
        """Drive the appliance through its remote-control block."""
        super().__init__(coordinator, EntityDescription(key="ventilation"), "control")

    @property
    def is_on(self) -> bool | None:
        """Whether the appliance is out of standby."""
        standby = self.device.control.standby
        return None if standby is None else not standby

    @property
    def preset_mode(self) -> str | None:
        """The mode the appliance reports, when 8001 has a code for it.

        This is what the appliance is doing rather than what was last asked
        of it, so a position set on the display shows here too. ``auto`` has
        no preset, so it reads as no preset.
        """
        mode = self.device.measurements.ventilation_mode
        if mode is None or mode is VentilationMode.AUTO:
            return None
        return mode.name.lower()

    @property
    def available(self) -> bool:
        """The fan needs both the control block and the readings."""
        updated = self.coordinator.data.updated
        return super().available and "measurements" in updated

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Hand the appliance a switch position over Modbus."""
        position = SwitchPosition[preset_mode.upper()]
        await self._async_command(
            self.device.control.async_set_switch_position(position)
        )

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Bring the appliance out of standby, and set a preset if given."""
        await self._async_command(self.device.control.async_request_standby(False))
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Put the appliance into standby."""
        await self._async_command(self.device.control.async_request_standby(True))

    async def _async_command(self, command: Coroutine[Any, Any, None]) -> None:
        """Run one write, then refresh so the new state shows at once."""
        try:
            await command
        except ModbusError as err:
            raise write_error(err) from err
        await self.coordinator.async_request_refresh()
