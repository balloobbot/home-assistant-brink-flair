"""The config flow: both transports, and what it does when they fail."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from modbus_connection import ModbusTimeoutError
from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.brink_flair.connection import CONF_UNIT_ID
from custom_components.brink_flair.const import (
    CONF_BAUDRATE,
    CONF_DEVICE,
    CONF_PARITY,
    CONF_STOPBITS,
    CONF_TRANSPORT,
    DOMAIN,
    TRANSPORT_SERIAL,
    TRANSPORT_TCP,
)

from .conftest import UNIT_ID


async def start(hass: HomeAssistant, transport: str) -> str:
    """Open the flow and pick a transport."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.MENU
    assert set(result["menu_options"]) == {TRANSPORT_SERIAL, TRANSPORT_TCP}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": transport}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == transport
    return str(result["flow_id"])


async def test_a_serial_appliance(hass: HomeAssistant, modbus: MockModbusUnit) -> None:
    flow_id = await start(hass, TRANSPORT_SERIAL)

    result = await hass.config_entries.flow.async_configure(
        flow_id,
        {
            CONF_DEVICE: "/dev/ttyUSB0",
            CONF_UNIT_ID: 20,
            CONF_BAUDRATE: "19200",
            CONF_PARITY: "E",
            CONF_STOPBITS: "1",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Brink Flair (/dev/ttyUSB0)"
    assert result["result"].unique_id == "123456789012"
    assert result["data"] == {
        CONF_TRANSPORT: TRANSPORT_SERIAL,
        CONF_DEVICE: "/dev/ttyUSB0",
        CONF_UNIT_ID: 20,
        CONF_BAUDRATE: 19200,
        CONF_PARITY: "E",
        CONF_STOPBITS: 1,
    }


async def test_the_numbers_are_stored_as_numbers(
    hass: HomeAssistant, modbus: MockModbusUnit
) -> None:
    """The selectors hand back strings and floats, and the parameter objects
    are compared by value to find a shared connection — so a baud rate stored
    as ``"19200"`` would open a second connection to the same device."""
    flow_id = await start(hass, TRANSPORT_SERIAL)

    result = await hass.config_entries.flow.async_configure(
        flow_id,
        {
            CONF_DEVICE: "/dev/ttyUSB0",
            CONF_UNIT_ID: 20.0,
            CONF_BAUDRATE: "9600",
            CONF_PARITY: "N",
            CONF_STOPBITS: "2",
        },
    )

    data = result["data"]
    assert data[CONF_BAUDRATE] == 9600
    assert data[CONF_STOPBITS] == 2
    assert data[CONF_UNIT_ID] == 20
    assert all(isinstance(data[key], int) for key in (CONF_BAUDRATE, CONF_UNIT_ID))


async def test_an_appliance_behind_a_gateway(
    hass: HomeAssistant, modbus: MockModbusUnit
) -> None:
    flow_id = await start(hass, TRANSPORT_TCP)

    result = await hass.config_entries.flow.async_configure(
        flow_id,
        {CONF_HOST: "192.168.1.50", CONF_PORT: 502, CONF_UNIT_ID: UNIT_ID},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Brink Flair (192.168.1.50:502)"
    assert result["data"][CONF_PORT] == 502


async def test_an_appliance_that_does_not_answer(
    hass: HomeAssistant, modbus: MockModbusUnit
) -> None:
    modbus.fail_requests(ModbusTimeoutError())
    flow_id = await start(hass, TRANSPORT_TCP)

    result = await hass.config_entries.flow.async_configure(
        flow_id,
        {CONF_HOST: "192.168.1.50", CONF_PORT: 502, CONF_UNIT_ID: UNIT_ID},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    # The form comes back, so the same details can be retried once it answers.
    modbus.fail_requests(None)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: "192.168.1.50", CONF_PORT: 502, CONF_UNIT_ID: UNIT_ID},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_an_endpoint_already_held_on_other_link_settings(
    hass: HomeAssistant, modbus: MockModbusUnit, monkeypatch
) -> None:
    """``modbus`` refuses to serve one device over two sets of link settings."""

    def refuse(*args: object, **kwargs: object) -> None:
        raise HomeAssistantError("already in use with different link settings")

    monkeypatch.setattr(
        "custom_components.brink_flair.config_flow.async_get_temporary_unit", refuse
    )
    flow_id = await start(hass, TRANSPORT_TCP)

    result = await hass.config_entries.flow.async_configure(
        flow_id,
        {CONF_HOST: "192.168.1.50", CONF_PORT: 502, CONF_UNIT_ID: UNIT_ID},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "link_conflict"}


async def test_the_same_appliance_twice(
    hass: HomeAssistant, modbus: MockModbusUnit, config_entry: MockConfigEntry
) -> None:
    """The serial number is the unique id, so the transport does not matter."""
    config_entry.add_to_hass(hass)
    flow_id = await start(hass, TRANSPORT_SERIAL)

    result = await hass.config_entries.flow.async_configure(
        flow_id,
        {
            CONF_DEVICE: "/dev/ttyUSB0",
            CONF_UNIT_ID: 20,
            CONF_BAUDRATE: "19200",
            CONF_PARITY: "E",
            CONF_STOPBITS: "1",
        },
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_an_appliance_whose_serial_does_not_decode(
    hass: HomeAssistant, modbus: MockModbusUnit
) -> None:
    """A nibble above 9 is not BCD, so the endpoint becomes the unique id."""
    modbus.input[4010] = [0x1234, 0x5678, 0x90AB]
    flow_id = await start(hass, TRANSPORT_TCP)

    result = await hass.config_entries.flow.async_configure(
        flow_id,
        {CONF_HOST: "192.168.1.50", CONF_PORT: 502, CONF_UNIT_ID: UNIT_ID},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == "192.168.1.50:502-20"
