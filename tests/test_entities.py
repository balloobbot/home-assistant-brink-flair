"""The entities: what they read, and what a service call writes."""

from __future__ import annotations

import pytest
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button import SERVICE_PRESS
from homeassistant.components.fan import (
    ATTR_PRESET_MODE,
    ATTR_PRESET_MODES,
    SERVICE_SET_PRESET_MODE,
)
from homeassistant.components.fan import (
    DOMAIN as FAN_DOMAIN,
)
from homeassistant.components.number import (
    ATTR_VALUE,
    SERVICE_SET_VALUE,
)
from homeassistant.components.number import (
    DOMAIN as NUMBER_DOMAIN,
)
from homeassistant.components.select import (
    ATTR_OPTION,
    SERVICE_SELECT_OPTION,
)
from homeassistant.components.select import (
    DOMAIN as SELECT_DOMAIN,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from modbus_connection import IllegalDataValueError
from modbus_connection.mock import MockModbusUnit, WriteEvent
from pytest_homeassistant_custom_component.common import MockConfigEntry

from .conftest import setup_integration

FAN = "fan.brink_flair"


@pytest.mark.parametrize(
    ("entity_id", "expected"),
    [
        ("sensor.brink_flair_supply_flow", "148"),
        ("sensor.brink_flair_exhaust_flow", "152"),
        ("sensor.brink_flair_supply_fan_temperature", "19.5"),
        ("sensor.brink_flair_ntc_1_temperature", "-3.5"),
        ("sensor.brink_flair_supply_humidity", "45.2"),
        ("sensor.brink_flair_exhaust_pressure", "-38.9"),
        ("sensor.brink_flair_supply_fan_speed", "2100"),
        ("sensor.brink_flair_operating_time", "12345"),
        ("sensor.brink_flair_total_airflow", "5432109"),
        ("sensor.brink_flair_airflow_since_filter_reset", "987654"),
        ("sensor.brink_flair_co2_sensor_1", "650"),
        ("sensor.brink_flair_extension_temperature", "12.0"),
        ("sensor.brink_flair_extension_analogue_input_1", "2.5"),
        # The coded registers read as names rather than as numbers.
        ("sensor.brink_flair_active_function", "auto_modbus"),
        ("sensor.brink_flair_ventilation_mode", "normal"),
        ("sensor.brink_flair_bypass_status", "closed"),
        ("sensor.brink_flair_frost_status", "no_frost"),
        ("sensor.brink_flair_supply_fan_status", "running"),
        ("sensor.brink_flair_co2_sensor_2_status", "not_initialized"),
        ("sensor.brink_flair_geo_heat_exchanger_status", "closed"),
        ("binary_sensor.brink_flair_filter", STATE_OFF),
        ("binary_sensor.brink_flair_extension_contact_1", STATE_OFF),
        ("binary_sensor.brink_flair_extension_contact_2", STATE_ON),
        ("binary_sensor.brink_flair_extension_relay_2", STATE_ON),
        ("number.brink_flair_modbus_flow_rate", "150"),
        ("select.brink_flair_bypass_mode", "automatic"),
        ("select.brink_flair_flow_type", "constant_flow"),
    ],
)
async def test_entity_states(
    hass: HomeAssistant,
    modbus: MockModbusUnit,
    config_entry: MockConfigEntry,
    entity_id: str,
    expected: str,
) -> None:
    await setup_integration(hass, config_entry)
    state = hass.states.get(entity_id)
    assert state is not None, f"{entity_id} was never added"
    assert state.state == expected


async def test_the_fan_reports_what_the_appliance_is_doing(
    hass: HomeAssistant, modbus: MockModbusUnit, config_entry: MockConfigEntry
) -> None:
    await setup_integration(hass, config_entry)

    state = hass.states.get(FAN)
    assert state.state == STATE_ON  # 8003 reads 0, so not in standby
    assert state.attributes[ATTR_PRESET_MODE] == "normal"
    assert state.attributes[ATTR_PRESET_MODES] == ["holiday", "low", "normal", "high"]


async def test_the_fan_has_no_preset_while_the_appliance_is_on_auto(
    hass: HomeAssistant, modbus: MockModbusUnit, config_entry: MockConfigEntry
) -> None:
    """Register 8001 has no code for auto, so it cannot be a preset."""
    modbus.input[4022] = 4  # ventilation mode -> auto
    await setup_integration(hass, config_entry)

    assert hass.states.get(FAN).attributes[ATTR_PRESET_MODE] is None


async def test_setting_a_preset_takes_control_first(
    hass: HomeAssistant, modbus: MockModbusUnit, config_entry: MockConfigEntry
) -> None:
    await setup_integration(hass, config_entry)
    written: list[WriteEvent] = []
    modbus.on_write(written.append)

    await hass.services.async_call(
        FAN_DOMAIN,
        SERVICE_SET_PRESET_MODE,
        {ATTR_ENTITY_ID: FAN, ATTR_PRESET_MODE: "high"},
        blocking=True,
    )

    assert [(event.address, event.values) for event in written] == [
        (8000, [1]),  # Modbus drives the switch position
        (8001, [3]),  # high
    ]


async def test_turning_the_fan_off_puts_the_appliance_in_standby(
    hass: HomeAssistant, modbus: MockModbusUnit, config_entry: MockConfigEntry
) -> None:
    await setup_integration(hass, config_entry)

    await hass.services.async_call(
        FAN_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: FAN}, blocking=True
    )
    assert await modbus.read_holding_registers(8003, 1) == [1]

    await hass.services.async_call(
        FAN_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: FAN}, blocking=True
    )
    assert await modbus.read_holding_registers(8003, 1) == [2]


async def test_setting_the_flow_rate(
    hass: HomeAssistant, modbus: MockModbusUnit, config_entry: MockConfigEntry
) -> None:
    await setup_integration(hass, config_entry)
    written: list[WriteEvent] = []
    modbus.on_write(written.append)

    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: "number.brink_flair_modbus_flow_rate", ATTR_VALUE: 225},
        blocking=True,
    )

    assert [(event.address, event.values) for event in written] == [
        (8000, [2]),  # Modbus drives the flow rate
        (8002, [225]),
    ]
    assert hass.states.get("number.brink_flair_modbus_flow_rate").state == "225"


async def test_selecting_a_setting_writes_and_reads_back(
    hass: HomeAssistant, modbus: MockModbusUnit, config_entry: MockConfigEntry
) -> None:
    await setup_integration(hass, config_entry)

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: "select.brink_flair_bypass_mode", ATTR_OPTION: "open"},
        blocking=True,
    )

    assert await modbus.read_holding_registers(6100, 1) == [2]
    assert hass.states.get("select.brink_flair_bypass_mode").state == "open"


async def test_pressing_a_command_button(
    hass: HomeAssistant, modbus: MockModbusUnit, config_entry: MockConfigEntry
) -> None:
    await setup_integration(hass, config_entry)
    written: list[WriteEvent] = []
    modbus.on_write(written.append)

    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: "button.brink_flair_reset_filter_warning"},
        blocking=True,
    )

    assert [(event.address, event.values) for event in written] == [(8010, [1])]


async def test_a_write_the_appliance_rejects_surfaces_to_the_user(
    hass: HomeAssistant, modbus: MockModbusUnit, config_entry: MockConfigEntry
) -> None:
    await setup_integration(hass, config_entry)
    modbus.fail_write(6100, IllegalDataValueError())

    with pytest.raises(HomeAssistantError, match="did not accept the write"):
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: "select.brink_flair_bypass_mode", ATTR_OPTION: "open"},
            blocking=True,
        )
