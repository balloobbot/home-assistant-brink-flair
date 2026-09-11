"""The diagnostics download."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from modbus_connection import ModbusTimeoutError
from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.brink_flair.diagnostics import (
    async_get_config_entry_diagnostics,
)

from .conftest import setup_integration


async def test_diagnostics(
    hass: HomeAssistant, modbus: MockModbusUnit, config_entry: MockConfigEntry
) -> None:
    await setup_integration(hass, config_entry)

    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    assert diagnostics["sub_systems"] == {
        "geo_heat_exchanger": True,
        "co2_sensors": True,
        "user_interface": True,
        "extension": True,
    }
    assert "measurements" in diagnostics["readings"]["updated"]
    assert diagnostics["settings"]["updated"] == ["parameters"]
    assert diagnostics["read_error"] is None

    registers = diagnostics["registers"]
    assert registers["input"][4032] == 148
    assert registers["holding"][6101] == 220


async def test_the_serial_number_is_left_out(
    hass: HomeAssistant, modbus: MockModbusUnit, config_entry: MockConfigEntry
) -> None:
    """It identifies the appliance and no decode depends on it."""
    await setup_integration(hass, config_entry)

    registers = (await async_get_config_entry_diagnostics(hass, config_entry))[
        "registers"
    ]

    assert 4000 in registers["input"]  # the rest of the identity stays
    assert not {4010, 4011, 4012} & registers["input"].keys()


async def test_the_one_shot_commands_are_left_out(
    hass: HomeAssistant, modbus: MockModbusUnit, config_entry: MockConfigEntry
) -> None:
    """Reading 8010 or 8011 clears the outcome they report."""
    await setup_integration(hass, config_entry)

    registers = (await async_get_config_entry_diagnostics(hass, config_entry))[
        "registers"
    ]

    assert 8000 in registers["holding"]
    assert not {8010, 8011} & registers["holding"].keys()


async def test_an_appliance_that_stops_answering_still_gives_a_payload(
    hass: HomeAssistant, modbus: MockModbusUnit, config_entry: MockConfigEntry
) -> None:
    """Better a download that says what went wrong than one that fails."""
    await setup_integration(hass, config_entry)
    modbus.fail_requests(ModbusTimeoutError())

    diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    assert diagnostics["registers"] is None
    assert diagnostics["read_error"]
