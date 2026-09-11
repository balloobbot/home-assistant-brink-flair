"""Constants for the Brink Flair integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "brink_flair"

CONF_TRANSPORT: Final = "transport"
CONF_DEVICE: Final = "device"
CONF_BAUDRATE: Final = "baudrate"
CONF_PARITY: Final = "parity"
CONF_STOPBITS: Final = "stopbits"

TRANSPORT_SERIAL: Final = "serial"
TRANSPORT_TCP: Final = "tcp"

# The appliance's factory link settings, from the spec's step 14.1-14.4 table.
DEFAULT_UNIT_ID: Final = 20
DEFAULT_BAUDRATE: Final = 19200
DEFAULT_PARITY: Final = "E"
DEFAULT_STOPBITS: Final = 1
DEFAULT_PORT: Final = 502

BAUDRATES: Final = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]
PARITIES: Final = ["N", "E", "O"]

# A readings poll is 19 requests on a 19200-baud line, well under a second.
READINGS_INTERVAL: Final = timedelta(seconds=30)

# The settings cost 17 more, and change only when something writes them.
SETTINGS_INTERVAL: Final = timedelta(minutes=15)

# The largest flow the number entity offers. The spec makes the real bounds
# depend on the appliance and gives no register to read them from, so this is
# a bound on the slider rather than one the appliance stated.
MAX_FLOW_RATE: Final = 500
FLOW_RATE_STEP: Final = 5
