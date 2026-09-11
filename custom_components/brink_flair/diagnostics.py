"""Diagnostics: the appliance's raw register map.

The most useful thing an issue report can carry for a Modbus device is every
register the integration reads with its raw value, undecoded. The dump also
loads straight back into modbus-connection's mock, so a report can become a
regression test with no hardware.

The serial number is dropped: it identifies the appliance, and nothing in a
decode depends on it.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from modbus_connection import ModbusError

from .brink_flair_modbus.identity import SERIAL_NUMBER, SERIAL_NUMBER_WORDS
from .coordinator import BrinkFlairConfigEntry, describe


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: BrinkFlairConfigEntry
) -> dict[str, Any]:
    """Read the appliance fresh and return what it answered."""
    data = entry.runtime_data
    device = data.device

    registers: dict[str, dict[int, int | bool]] | None = None
    read_error: str | None = None
    try:
        registers = await device.async_read_raw()
    except ModbusError as err:
        # Better a payload saying the appliance stopped answering than a
        # download that fails with nothing in it.
        read_error = describe(err)
    else:
        for address in range(SERIAL_NUMBER, SERIAL_NUMBER + SERIAL_NUMBER_WORDS):
            registers["input"].pop(address, None)

    return {
        "sub_systems": {
            "geo_heat_exchanger": device.geo_heat_exchanger is not None,
            "co2_sensors": device.co2_sensors is not None,
            "user_interface": device.user_interface is not None,
            "extension": device.extension is not None,
        },
        "readings": _report(data.readings.data),
        "settings": _report(data.settings.data),
        "registers": registers,
        "read_error": read_error,
    }


def _report(report: Any) -> dict[str, Any]:
    """One coordinator's last update report, made serializable."""
    if report is None:
        return {}
    return {
        "updated": report.updated,
        "failed": {name: describe(err) for name, err in report.failed.items()},
    }
