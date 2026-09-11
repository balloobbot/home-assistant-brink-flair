"""The Modbus flow-rate setpoint.

Register 8002, the flow the appliance runs at while Modbus is driving it.
Writing it switches the appliance into that mode first, which is what the
library's ``async_set_flow_rate`` does.

The slider's maximum is the integration's, not the appliance's: the spec
makes the real bounds depend on the model and gives no register to read them
from. It is deliberately generous, so an appliance is never capped below what
it can do.
"""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import UnitOfVolumeFlowRate
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from modbus_connection import ModbusError

from .const import FLOW_RATE_STEP, MAX_FLOW_RATE
from .coordinator import BrinkFlairConfigEntry, BrinkFlairCoordinator
from .entity import BrinkFlairEntity, write_error

PARALLEL_UPDATES = 1

TRANSLATION_KEY = "flow_rate"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: BrinkFlairConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the flow-rate setpoint."""
    async_add_entities([BrinkFlairFlowRate(entry.runtime_data.readings)])


class BrinkFlairFlowRate(BrinkFlairEntity, NumberEntity):
    """The flow rate Modbus is asking the appliance for."""

    _attr_translation_key = TRANSLATION_KEY
    _attr_device_class = NumberDeviceClass.VOLUME_FLOW_RATE
    _attr_native_unit_of_measurement = UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR
    _attr_native_min_value = 0
    _attr_native_max_value = MAX_FLOW_RATE
    _attr_native_step = FLOW_RATE_STEP
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator: BrinkFlairCoordinator) -> None:
        """Bind the setpoint to the remote-control block."""
        super().__init__(coordinator, EntityDescription(key="flow_rate"), "control")

    @property
    def native_value(self) -> float | None:
        """The last flow rate the appliance accepted."""
        return self.device.control.flow_rate

    async def async_set_native_value(self, value: float) -> None:
        """Put the appliance in flow-rate mode and hand it the new flow."""
        try:
            await self.device.control.async_set_flow_rate(int(value))
        except ModbusError as err:
            raise write_error(err) from err
        await self.coordinator.async_request_refresh()
