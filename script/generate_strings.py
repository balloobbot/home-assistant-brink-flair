#!/usr/bin/env python3

"""Generate strings.json and translations/en.json.

The enum sensors and selects take their options straight off the library's
enums, which are the spec's own code lists. Writing the matching state labels
by hand would let the two drift the moment a code list changes, so they are
generated from the same enums instead.

::

    uv run --with modbus-connection script/generate_strings.py
"""

from __future__ import annotations

import json
import sys
from enum import IntEnum
from pathlib import Path
from typing import Any

COMPONENT = Path(__file__).resolve().parent.parent / "custom_components" / "brink_flair"
# Import the vendored library directly, so generating strings needs no
# Home Assistant — the integration package itself imports one.
sys.path.insert(0, str(COMPONENT))

from brink_flair_modbus import (  # noqa: E402
    ActiveFunction,
    BypassMode,
    BypassStatus,
    Co2SensorStatus,
    EbusPowerStatus,
    FanControlType,
    FanStatus,
    FlowSwitchPosition,
    FlowType,
    FrostStatus,
    GeoHeatExchangerStatus,
    PreheaterStatus,
    SignalOutputMode,
    SignalOutputState,
    VentilationMode,
)

# Member names whose sentence case is not simply the name lowercased.
WORDS = {
    "co2": "CO2",
    "ebus": "eBus",
    "lan": "LAN",
    "modbus": "Modbus",
    "pwm": "PWM",
    "wlan": "WLAN",
    "v": "V",
}


# Member names whose label no per-word rule produces.
OVERRIDES = {
    "AUTO_LAN_WLAN_LOCAL": "Auto LAN/WLAN local",
    "AUTO_LAN_WLAN_PORTAL": "Auto LAN/WLAN portal",
    "NON_BLOCKING_ERROR": "Non-blocking error",
    "TWENTY_FOUR_VOLT": "24 V",
    "ZERO_VOLT": "0 V",
}


def label(member: IntEnum) -> str:
    """A state's label, from its member name."""
    if (override := OVERRIDES.get(member.name)) is not None:
        return override
    words = member.name.lower().split("_")
    rendered = [WORDS.get(word, word) for word in words]
    if rendered[0] not in WORDS.values():
        rendered[0] = rendered[0].capitalize()
    return " ".join(rendered)


def states(enum_type: type[IntEnum]) -> dict[str, str]:
    """Every state one enum register can report."""
    return {member.name.lower(): label(member) for member in enum_type}


def sensor(name: str, enum_type: type[IntEnum] | None = None) -> dict[str, Any]:
    """One sensor's name, and its states where it has a code list."""
    entry: dict[str, Any] = {"name": name}
    if enum_type is not None:
        entry["state"] = states(enum_type)
    return entry


SENSORS: dict[str, dict[str, Any]] = {
    "supply_flow": sensor("Supply flow"),
    "exhaust_flow": sensor("Exhaust flow"),
    "supply_flow_setpoint": sensor("Supply flow setpoint"),
    "exhaust_flow_setpoint": sensor("Exhaust flow setpoint"),
    "supply_mass_flow": sensor("Supply mass flow"),
    "exhaust_mass_flow": sensor("Exhaust mass flow"),
    "supply_fan_temperature": sensor("Supply fan temperature"),
    "exhaust_fan_temperature": sensor("Exhaust fan temperature"),
    "supply_humidity": sensor("Supply humidity"),
    "exhaust_humidity": sensor("Exhaust humidity"),
    "ntc1_temperature": sensor("NTC 1 temperature"),
    "ntc2_temperature": sensor("NTC 2 temperature"),
    "rht_humidity": sensor("RHT sensor humidity"),
    "supply_pressure": sensor("Supply pressure"),
    "exhaust_pressure": sensor("Exhaust pressure"),
    "supply_fan_speed": sensor("Supply fan speed"),
    "exhaust_fan_speed": sensor("Exhaust fan speed"),
    "supply_anemometer_speed": sensor("Supply anemometer speed"),
    "exhaust_anemometer_speed": sensor("Exhaust anemometer speed"),
    "preheater_capacity": sensor("Preheater capacity"),
    "frost_heater_power": sensor("Frost heater power"),
    "fan_frost_reduction": sensor("Fan frost reduction"),
    "bypass_position": sensor("Bypass position"),
    "filter_hours": sensor("Hours since filter reset"),
    "operating_time": sensor("Operating time"),
    "filter_flow": sensor("Airflow since filter reset"),
    "total_flow": sensor("Total airflow"),
    "active_function": sensor("Active function", ActiveFunction),
    "fan_control_type": sensor("Fan control type", FanControlType),
    "ventilation_mode": sensor("Ventilation mode", VentilationMode),
    "supply_fan_status": sensor("Supply fan status", FanStatus),
    "exhaust_fan_status": sensor("Exhaust fan status", FanStatus),
    "bypass_status": sensor("Bypass status", BypassStatus),
    "preheater_status": sensor("Preheater status", PreheaterStatus),
    "frost_status": sensor("Frost status", FrostStatus),
    "flow_switch_position": sensor("Flow switch position", FlowSwitchPosition),
    "signal_output": sensor("Signal output", SignalOutputState),
    "ebus_power_status": sensor("eBus power status", EbusPowerStatus),
    "geo_heat_exchanger_status": sensor(
        "Geo heat exchanger status", GeoHeatExchangerStatus
    ),
    "co2_sensor": sensor("CO2 sensor {index}"),
    "co2_sensor_status": sensor("CO2 sensor {index} status", Co2SensorStatus),
    "display_switch": sensor("Display switch"),
    "extension_temperature": sensor("Extension temperature"),
    "extension_analogue_input": sensor("Extension analogue input {index}"),
    "extension_analogue_output": sensor("Extension analogue output {index}"),
}

BINARY_SENSORS: dict[str, Any] = {
    "filter_dirty": {"name": "Filter"},
    "extension_contact": {"name": "Extension contact {index}"},
    "extension_relay": {"name": "Extension relay {index}"},
}

SELECTS: dict[str, Any] = {
    "bypass_mode": {"name": "Bypass mode", "state": states(BypassMode)},
    "flow_type": {"name": "Flow type", "state": states(FlowType)},
    "signal_output_mode": {
        "name": "Signal output mode",
        "state": states(SignalOutputMode),
    },
}

STRINGS: dict[str, Any] = {
    "config": {
        "step": {
            "user": {
                "title": "Brink Flair",
                "description": "How is the appliance reached?",
                "menu_options": {
                    "serial": "A serial adapter on this machine",
                    "serial_server": "A serial server on the network (forwards RTU)",
                    "gateway": "A Modbus gateway on the network (converts to RTU)",
                },
            },
            "serial": {
                "title": "Serial adapter",
                "description": (
                    "The appliance leaves the factory on unit id 20 at 19200 baud, "
                    "even parity, 1 stop bit. Check step 14.1 on its display says "
                    "Modbus."
                ),
                "data": {
                    "device": "Serial device",
                    "unit_id": "Unit id",
                    "baudrate": "Baud rate",
                    "parity": "Parity",
                    "stopbits": "Stop bits",
                },
                "data_description": {
                    "device": "The RS-485 adapter, for example /dev/ttyUSB0.",
                    "unit_id": (
                        "The appliance's slave address, step 14.2 on its display."
                    ),
                    "baudrate": "Step 14.3 on the appliance's display.",
                    "parity": "Step 14.4 on the appliance's display.",
                    "stopbits": "1 unless the appliance has been changed from it.",
                },
            },
            "serial_server": {
                "title": "Serial server",
                "description": (
                    "A box that forwards the RS-485 line byte for byte, such as a "
                    "USR-TCP232 or a Waveshare in TCP-server mode. Set the "
                    "appliance's own line settings on the box itself: 19200 baud, "
                    "even parity, 1 stop bit out of the factory."
                ),
                "data": {"host": "Host", "port": "Port", "unit_id": "Unit id"},
                "data_description": {
                    "host": "The serial server's address on the network.",
                    "port": "The port it listens on, often 502 or 8899.",
                    "unit_id": (
                        "The appliance's slave address, step 14.2 on its display."
                    ),
                },
            },
            "gateway": {
                "title": "Modbus gateway",
                "description": (
                    "A box that speaks Modbus TCP on the network and converts to "
                    "Modbus RTU on the serial side, such as a Moxa MGate or a "
                    "Waveshare in Modbus-gateway mode. If you are not sure which "
                    "of the two kinds you have, try this one and the serial "
                    "server; nothing on the network says which a box is doing."
                ),
                "data": {"host": "Host", "port": "Port", "unit_id": "Unit id"},
                "data_description": {
                    "host": "The gateway's address on the network.",
                    "port": "Its Modbus TCP port, usually 502.",
                    "unit_id": (
                        "The appliance's slave address, step 14.2 on its display."
                    ),
                },
            },
        },
        "error": {
            "cannot_connect": (
                "The appliance did not answer. Check the wiring, the unit id and "
                "the link settings, and that step 14.1 on its display says Modbus."
            ),
            "link_conflict": (
                "Something already uses this connection with different link "
                "settings. One connection cannot serve both."
            ),
        },
        "abort": {"already_configured": "This appliance is already configured"},
    },
    "entity": {
        "binary_sensor": BINARY_SENSORS,
        "button": {
            "reset_filter_warning": {"name": "Reset filter warning"},
            "appliance_reset": {"name": "Restart appliance"},
        },
        "number": {"flow_rate": {"name": "Modbus flow rate"}},
        "select": SELECTS,
        "sensor": SENSORS,
    },
    "exceptions": {
        "write_failed": {"message": "The appliance did not accept the write: {error}"}
    },
}


def main() -> None:
    """Write both files."""
    rendered = json.dumps(STRINGS, indent=2, ensure_ascii=False) + "\n"
    (COMPONENT / "strings.json").write_text(rendered)
    translations = COMPONENT / "translations"
    translations.mkdir(exist_ok=True)
    (translations / "en.json").write_text(rendered)
    print(f"Wrote {COMPONENT / 'strings.json'} and {translations / 'en.json'}")


if __name__ == "__main__":
    main()
