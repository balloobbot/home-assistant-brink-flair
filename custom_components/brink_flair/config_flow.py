"""Config flow for the Brink Flair integration.

The appliance is an RS-485 device, so the flow first asks how it is reached —
a serial adapter on the machine running Home Assistant, or a gateway on the
network — and then only what that transport needs. Nothing else is asked:
which optional modules the appliance carries is settled by probing it.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)
from modbus_connection import ModbusError

from .brink_flair_modbus import SLAVE_ADDRESS_MAX, SLAVE_ADDRESS_MIN, BrinkFlair
from .connection import CONF_UNIT_ID, connection_params, endpoint_name
from .const import (
    BAUDRATES,
    CONF_BAUDRATE,
    CONF_DEVICE,
    CONF_PARITY,
    CONF_STOPBITS,
    CONF_TRANSPORT,
    DEFAULT_BAUDRATE,
    DEFAULT_PARITY,
    DEFAULT_PORT,
    DEFAULT_STOPBITS,
    DEFAULT_UNIT_ID,
    DOMAIN,
    PARITIES,
    TRANSPORT_SERIAL,
    TRANSPORT_TCP,
)

UNIT_ID_SELECTOR = NumberSelector(
    NumberSelectorConfig(
        min=SLAVE_ADDRESS_MIN, max=SLAVE_ADDRESS_MAX, mode=NumberSelectorMode.BOX
    )
)


def _options(values: list[Any]) -> SelectSelector:
    """A dropdown of fixed values, shown as given rather than translated."""
    return SelectSelector(
        SelectSelectorConfig(
            options=[str(value) for value in values], mode=SelectSelectorMode.DROPDOWN
        )
    )


SERIAL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE, default="/dev/ttyUSB0"): TextSelector(),
        vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): UNIT_ID_SELECTOR,
        vol.Required(CONF_BAUDRATE, default=str(DEFAULT_BAUDRATE)): _options(BAUDRATES),
        vol.Required(CONF_PARITY, default=DEFAULT_PARITY): _options(PARITIES),
        vol.Required(CONF_STOPBITS, default=str(DEFAULT_STOPBITS)): _options([1, 2]),
    }
)

TCP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): TextSelector(),
        vol.Required(CONF_PORT, default=DEFAULT_PORT): NumberSelector(
            NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)
        ),
        vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): UNIT_ID_SELECTOR,
    }
)


class BrinkFlairConfigFlow(ConfigFlow, domain=DOMAIN):
    """Gather how to reach a Brink appliance, and check it answers."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask which transport the appliance is reached over."""
        return self.async_show_menu(
            step_id="user", menu_options=[TRANSPORT_SERIAL, TRANSPORT_TCP]
        )

    async def async_step_serial(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure an appliance on a local serial adapter."""
        return await self._async_configure(TRANSPORT_SERIAL, SERIAL_SCHEMA, user_input)

    async def async_step_tcp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure an appliance behind an RTU-to-TCP gateway."""
        return await self._async_configure(TRANSPORT_TCP, TCP_SCHEMA, user_input)

    async def _async_configure(
        self,
        transport: str,
        schema: vol.Schema,
        user_input: dict[str, Any] | None,
    ) -> ConfigFlowResult:
        """Validate one transport's form by talking to the appliance."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = _normalise({**user_input, CONF_TRANSPORT: transport})
            try:
                serial_number = await self._async_probe(data)
            except ModbusError:
                errors["base"] = "cannot_connect"
            except HomeAssistantError:
                # The endpoint is already held on different link settings.
                errors["base"] = "link_conflict"
            else:
                endpoint = endpoint_name(data)
                await self.async_set_unique_id(
                    serial_number or f"{endpoint}-{data[CONF_UNIT_ID]}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Brink Flair ({endpoint})", data=data
                )

        return self.async_show_form(
            step_id=transport, data_schema=schema, errors=errors
        )

    async def _async_probe(self, data: dict[str, Any]) -> str | None:
        """Read the appliance's identity, or raise if it does not answer.

        Two register reads. The serial number becomes the unique id; an
        appliance whose serial does not decode falls back to the endpoint it
        was found at.
        """
        params, unit_id = connection_params(data)
        async with async_get_temporary_unit(self.hass, params, unit_id) as unit:
            appliance = BrinkFlair(unit)
            await appliance.identity.async_update()
            return appliance.identity.serial_number


def _normalise(data: dict[str, Any]) -> dict[str, Any]:
    """Give the numeric fields their real types.

    The number and dropdown selectors hand back floats and strings, and the
    parameter dataclasses are compared by value to find a shared connection —
    so ``19200`` and ``"19200"`` would open two connections to one device.
    """
    normalised = dict(data)
    for key in (CONF_UNIT_ID, CONF_PORT, CONF_BAUDRATE, CONF_STOPBITS):
        if key in normalised:
            normalised[key] = int(normalised[key])
    return normalised
