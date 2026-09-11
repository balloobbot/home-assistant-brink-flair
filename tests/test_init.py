"""Setting the entry up, and what happens when the appliance goes quiet."""

from __future__ import annotations

from datetime import timedelta

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from modbus_connection import IllegalDataAddressError, ModbusTimeoutError
from modbus_connection.mock import MockModbusUnit
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.brink_flair.const import DOMAIN, READINGS_INTERVAL

from .conftest import setup_integration


async def test_setup(
    hass: HomeAssistant, modbus: MockModbusUnit, config_entry: MockConfigEntry
) -> None:
    await setup_integration(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED


async def test_the_device_is_registered_with_what_the_appliance_reported(
    hass: HomeAssistant,
    modbus: MockModbusUnit,
    config_entry: MockConfigEntry,
    device_registry: dr.DeviceRegistry,
) -> None:
    await setup_integration(hass, config_entry)

    device = device_registry.async_get_device_by_identifier(
        (DOMAIN, "123456789012"), config_entry.entry_id
    )
    assert device is not None
    assert device.manufacturer == "Brink"
    assert device.model == "Flair"
    assert device.sw_version == "S1.01.03.0001"
    assert device.hw_version == "H1.1"
    assert device.serial_number == "123456789012"


async def test_an_unreachable_appliance_is_retried(
    hass: HomeAssistant, modbus: MockModbusUnit, config_entry: MockConfigEntry
) -> None:
    """The first poll establishes the link, so a dead appliance is not ready."""
    modbus.fail_requests(ModbusTimeoutError())
    config_entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload(
    hass: HomeAssistant, modbus: MockModbusUnit, config_entry: MockConfigEntry
) -> None:
    await setup_integration(hass, config_entry)

    assert await hass.config_entries.async_unload(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_hardware_the_appliance_lacks_gets_no_entities(
    hass: HomeAssistant, bare_modbus: MockModbusUnit, config_entry: MockConfigEntry
) -> None:
    """A bare UWA2-B has no CO2 board, so it has no CO2 sensors."""
    await setup_integration(hass, config_entry)

    assert hass.states.get("sensor.brink_flair_co2_sensor_1") is None
    assert hass.states.get("sensor.brink_flair_extension_temperature") is None
    assert hass.states.get("sensor.brink_flair_supply_flow") is not None


async def test_one_sub_system_failing_leaves_the_others_alone(
    hass: HomeAssistant,
    modbus: MockModbusUnit,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A CO2 board pulled after setup takes its own entities unavailable."""
    await setup_integration(hass, config_entry)
    assert hass.states.get("sensor.brink_flair_co2_sensor_1").state == "650"

    modbus.fail_read(4200, IllegalDataAddressError(), register_type="input")
    freezer.tick(READINGS_INTERVAL + timedelta(seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get("sensor.brink_flair_co2_sensor_1").state == STATE_UNAVAILABLE
    assert hass.states.get("sensor.brink_flair_supply_flow").state == "148"


@pytest.mark.parametrize(
    ("entity_id", "expected"),
    [
        ("sensor.brink_flair_supply_flow", STATE_UNAVAILABLE),
        ("binary_sensor.brink_flair_filter", STATE_UNAVAILABLE),
        # A counter holds its last value, so long-term statistics keep going.
        ("sensor.brink_flair_operating_time", "12345"),
    ],
)
async def test_an_appliance_that_stops_answering(
    hass: HomeAssistant,
    modbus: MockModbusUnit,
    config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    entity_id: str,
    expected: str,
) -> None:
    await setup_integration(hass, config_entry)

    modbus.fail_requests(ModbusTimeoutError())
    freezer.tick(READINGS_INTERVAL + timedelta(seconds=1))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(entity_id).state == expected
