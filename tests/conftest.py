"""Fixtures for the Brink Flair integration tests.

The appliance is modbus-connection's in-memory mock, seeded with the same
register map the library's own tests use. Home Assistant's ``modbus``
integration is what hands out units, so the tests patch the two functions
that do so rather than the transport underneath them — the integration only
ever sees a ``ModbusUnit``, which is exactly what the mock is.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from modbus_connection.mock import MockModbusConnection, MockModbusUnit
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.brink_flair.connection import CONF_UNIT_ID
from custom_components.brink_flair.const import (
    CONF_BAUDRATE,
    CONF_TRANSPORT,
    DOMAIN,
    TRANSPORT_SERIAL_SERVER,
)

from .registers import SERIAL, seed

UNIT_ID = 20


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> None:
    """Let Home Assistant load the integration from custom_components."""


@pytest.fixture
def unit() -> MockModbusUnit:
    """A mock appliance carrying every optional module."""
    connection = MockModbusConnection()
    return seed(connection.for_unit(UNIT_ID))


@pytest.fixture
def bare_unit() -> MockModbusUnit:
    """A mock appliance with a UWA2-B and nothing else."""
    from modbus_connection import IllegalDataAddressError

    connection = MockModbusConnection()
    bare = seed(connection.for_unit(UNIT_ID), optional=False)
    for address in (4150, 4200, 4400, 4500):
        bare.fail_read(address, IllegalDataAddressError(), register_type="input")
    return bare


@pytest.fixture
def modbus(unit: MockModbusUnit) -> Generator[MockModbusUnit]:
    """Hand the integration the mock unit wherever it asks modbus for one."""
    with _patched(unit):
        yield unit


@pytest.fixture
def bare_modbus(bare_unit: MockModbusUnit) -> Generator[MockModbusUnit]:
    """The same, for an appliance without the optional modules."""
    with _patched(bare_unit):
        yield bare_unit


def _patched(unit: MockModbusUnit) -> Any:
    """Patch both of the modbus integration's unit factories."""

    @asynccontextmanager
    async def temporary(*args: Any, **kwargs: Any) -> AsyncIterator[MockModbusUnit]:
        yield unit

    get_unit = patch("custom_components.brink_flair.async_get_unit", return_value=unit)
    get_temporary = patch(
        "custom_components.brink_flair.config_flow.async_get_temporary_unit",
        temporary,
    )

    class _Both:
        def __enter__(self) -> MockModbusUnit:
            get_unit.start()
            get_temporary.start()
            return unit

        def __exit__(self, *exc: object) -> None:
            get_temporary.stop()
            get_unit.stop()

    return _Both()


ENTRY_DATA = {
    CONF_TRANSPORT: TRANSPORT_SERIAL_SERVER,
    CONF_HOST: "192.168.1.50",
    CONF_PORT: 502,
    CONF_BAUDRATE: 19200,
    CONF_UNIT_ID: UNIT_ID,
}


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """A configured appliance behind a gateway."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Brink Flair (192.168.1.50:502)",
        unique_id=SERIAL,
        data=ENTRY_DATA,
    )


async def setup_integration(
    hass: HomeAssistant, entry: MockConfigEntry
) -> MockConfigEntry:
    """Add the entry and run setup."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
