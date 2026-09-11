"""Turn an entry's stored data into modbus-connection parameters.

Shared by the config flow, which probes with them, and by setup, which asks
``modbus`` for a unit with them. Both must build the same object from the
same data, or the two would land on different connections.

The appliance speaks Modbus RTU on RS-485 and nothing else, so what differs
between the two network transports is the box in front of the line rather
than the appliance. A transparent serial server forwards the RTU frames as
they are, which is ``rtu`` framing; a Modbus gateway terminates Modbus TCP
and re-frames to RTU itself, which is ``socket``.

Both are ``ModbusTcpParams``, so both key on ``("tcp", host, port)`` and
share a connection with whatever else reaches that box. Describing a serial
server as a ``socket://`` serial device would work too, and would key
differently — two integrations would then open two sockets onto one
half-duplex line and interleave frames on it.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.const import CONF_HOST, CONF_PORT
from modbus_connection import ModbusSerialParams, ModbusTcpParams

from .const import (
    CONF_BAUDRATE,
    CONF_DEVICE,
    CONF_PARITY,
    CONF_STOPBITS,
    CONF_TRANSPORT,
    TRANSPORT_SERIAL,
    TRANSPORT_SERIAL_SERVER,
)

CONF_UNIT_ID = "unit_id"

type BrinkFlairParams = ModbusSerialParams | ModbusTcpParams


def connection_params(data: Mapping[str, Any]) -> tuple[BrinkFlairParams, int]:
    """The link parameters and unit id an entry's data describes."""
    if data[CONF_TRANSPORT] == TRANSPORT_SERIAL:
        params: BrinkFlairParams = ModbusSerialParams(
            device=data[CONF_DEVICE],
            baudrate=data[CONF_BAUDRATE],
            parity=data[CONF_PARITY],
            stopbits=data[CONF_STOPBITS],
            framer="rtu",
        )
    else:
        params = ModbusTcpParams(
            host=data[CONF_HOST],
            port=data[CONF_PORT],
            framer="rtu"
            if data[CONF_TRANSPORT] == TRANSPORT_SERIAL_SERVER
            else "socket",
        )
    return params, data[CONF_UNIT_ID]


def endpoint_name(data: Mapping[str, Any]) -> str:
    """How the appliance is reached, for an entry title."""
    if data[CONF_TRANSPORT] == TRANSPORT_SERIAL:
        return str(data[CONF_DEVICE])
    return f"{data[CONF_HOST]}:{data[CONF_PORT]}"
