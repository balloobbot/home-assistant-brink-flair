"""Turn an entry's stored data into modbus-connection parameters.

Shared by the config flow, which probes with them, and by setup, which asks
``modbus`` for a unit with them. Both must build the same object from the
same data, or the two would land on different connections.

The appliance speaks Modbus RTU on RS-485 and nothing else, so what differs
between the two network transports is the box in front of the line rather
than the appliance.

A serial server forwards the line byte for byte, so it is a serial link over
a socket: ``ModbusSerialParams`` with a ``socket://`` device. A Modbus
gateway terminates Modbus TCP and re-frames to RTU itself, so the network
carries Modbus TCP: ``ModbusTcpParams``.

Naming a serial server that way is what lets two integrations reaching one
box share a connection, rather than opening two sockets onto one half-duplex
line and interleaving frames on it.
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
    TRANSPORT_GATEWAY,
    TRANSPORT_SERIAL,
)

CONF_UNIT_ID = "unit_id"

type BrinkFlairParams = ModbusSerialParams | ModbusTcpParams


def _socket_device(host: str, port: int) -> str:
    """A serial server's line, as the serial device URL that names it.

    An IPv6 literal is bracketed. Without the brackets the URL does not
    parse, because the address's own colons are read as the port separator.
    """
    address = f"[{host}]" if ":" in host else host
    return f"socket://{address}:{port}"


def connection_params(data: Mapping[str, Any]) -> tuple[BrinkFlairParams, int]:
    """The link parameters and unit id an entry's data describes."""
    transport = data[CONF_TRANSPORT]
    params: BrinkFlairParams
    if transport == TRANSPORT_GATEWAY:
        params = ModbusTcpParams(host=data[CONF_HOST], port=data[CONF_PORT])
    elif transport == TRANSPORT_SERIAL:
        params = ModbusSerialParams(
            device=data[CONF_DEVICE],
            baudrate=data[CONF_BAUDRATE],
            parity=data[CONF_PARITY],
            stopbits=data[CONF_STOPBITS],
        )
    else:
        # The baud rate spaces the frames rather than configuring a port, so
        # it is the speed the box runs its own line at. Parity and stop bits
        # do configure a port, and there is none here, so they are left out:
        # they would make two descriptions of one server compare unequal.
        params = ModbusSerialParams(
            device=_socket_device(data[CONF_HOST], data[CONF_PORT]),
            baudrate=data[CONF_BAUDRATE],
        )
    return params, data[CONF_UNIT_ID]


def endpoint_name(data: Mapping[str, Any]) -> str:
    """How the appliance is reached, for an entry title."""
    if data[CONF_TRANSPORT] == TRANSPORT_SERIAL:
        return str(data[CONF_DEVICE])
    return f"{data[CONF_HOST]}:{data[CONF_PORT]}"
