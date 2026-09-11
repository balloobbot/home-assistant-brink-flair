"""The Brink Flair integration.

The appliance is reached over a unit handed out by Home Assistant's ``modbus``
integration, so several integrations on one RS-485 line or one gateway share
a single connection and serialize their requests behind it.
"""

from __future__ import annotations

from homeassistant.components.modbus import async_get_unit
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError

from .brink_flair_modbus import BrinkFlair
from .connection import connection_params
from .const import READINGS_INTERVAL, SETTINGS_INTERVAL
from .coordinator import BrinkFlairConfigEntry, BrinkFlairCoordinator, BrinkFlairData

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.FAN,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: BrinkFlairConfigEntry) -> bool:
    """Set up a Brink appliance from a config entry."""
    params, unit_id = connection_params(entry.data)
    try:
        unit = async_get_unit(hass, entry, params, unit_id)
    except HomeAssistantError as err:
        # Another entry already holds this endpoint on different link
        # settings, which one connection cannot serve.
        raise ConfigEntryNotReady(str(err)) from err

    device = BrinkFlair(unit)
    data = BrinkFlairData(
        device,
        BrinkFlairCoordinator(
            hass,
            entry,
            device,
            device.async_update_readings,
            READINGS_INTERVAL,
            "readings",
        ),
        BrinkFlairCoordinator(
            hass,
            entry,
            device,
            device.async_update_settings,
            SETTINGS_INTERVAL,
            "settings",
        ),
    )

    # The readings poll runs setup, so it goes first: it is what probes for
    # the optional hardware and turns an unreachable appliance into a retry.
    await data.readings.async_config_entry_first_refresh()
    await data.settings.async_config_entry_first_refresh()

    entry.runtime_data = data
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BrinkFlairConfigEntry) -> bool:
    """Unload a config entry.

    The connection belongs to ``modbus``, which closes it behind the last
    entry holding a unit on it.
    """
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
