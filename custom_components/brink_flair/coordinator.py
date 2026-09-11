"""Coordinators for the Brink Flair integration.

The library polls the readings and the settings apart, so there is one
coordinator per poll. Both hold the same device object and both hand their
entities an ``UpdateReport``, which names the sub-systems that refreshed —
that is what an entity checks to decide whether it is available.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta
from functools import cached_property

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import ModbusError

from .brink_flair_modbus import MANUFACTURER, BrinkFlair, UpdateReport
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def describe(err: ModbusError) -> str:
    """One Modbus failure in words.

    Several of these carry no message of their own — a timeout is the fact
    that nothing came back — so the class name is what says what happened.
    """
    return f"{type(err).__name__}: {err}" if str(err) else type(err).__name__


type BrinkFlairConfigEntry = ConfigEntry[BrinkFlairData]


class BrinkFlairCoordinator(DataUpdateCoordinator[UpdateReport]):
    """Run one of the appliance's update methods on its own interval."""

    config_entry: BrinkFlairConfigEntry
    _failed: frozenset[str] = frozenset()

    def __init__(
        self,
        hass: HomeAssistant,
        entry: BrinkFlairConfigEntry,
        device: BrinkFlair,
        poll: Callable[[], Awaitable[UpdateReport]],
        interval: timedelta,
        name: str,
    ) -> None:
        """Set up a coordinator around one of the device's poll methods."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{entry.title} {name}",
            update_interval=interval,
        )
        self.device = device
        self._poll = poll

    async def _async_update_data(self) -> UpdateReport:
        """Poll, and fail the update only when nothing at all answered."""
        try:
            report = await self._poll()
        except ModbusError as err:
            raise UpdateFailed(describe(err)) from err

        if not report.updated:
            errors = list(report.failed.values())
            raise UpdateFailed(f"no sub-system answered: {describe(errors[0])}") from (
                ExceptionGroup("every sub-system failed", errors)
            )

        for name in sorted(report.failed.keys() - self._failed):
            _LOGGER.warning("Failed to fetch %s: %s", name, report.failed[name])
        self._failed = frozenset(report.failed)
        return report

    @cached_property
    def device_info(self) -> DeviceInfo:
        """Describe the appliance to the registry."""
        identity = self.device.identity
        return DeviceInfo(
            identifiers={(DOMAIN, self.config_entry.unique_id or "")},
            # Named after the product rather than after the entry, so entity
            # ids stay short whatever the entry is titled.
            name=f"{MANUFACTURER} {self.device.model}",
            manufacturer=MANUFACTURER,
            model=self.device.model,
            sw_version=identity.software_version,
            hw_version=identity.hardware_version,
            serial_number=identity.serial_number,
        )


class BrinkFlairData:
    """The two coordinators an entry runs, and the device they share."""

    def __init__(
        self,
        device: BrinkFlair,
        readings: BrinkFlairCoordinator,
        settings: BrinkFlairCoordinator,
    ) -> None:
        """Hold the appliance and its two polls."""
        self.device = device
        self.readings = readings
        self.settings = settings
