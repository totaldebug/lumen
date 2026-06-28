"""Constants for the Lumen integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "lumen"

# Config entry keys (HA's CONF_HOST/CONF_PORT/CONF_NAME are reused for the rest).
CONF_MODE: Final = "mode"
CONF_DONGLE_SERIAL: Final = "dongle_serial"
CONF_SERIAL: Final = "serial"

# Connection modes (see the transport abstraction in the project plan).
MODE_CLIENT: Final = "client"  # Home Assistant dials the dongle (default)
MODE_SERVER: Final = "server"  # the dongle dials Home Assistant

DEFAULT_NAME: Final = "Lumen"
DEFAULT_PORT: Final = 8000
DEFAULT_MODE: Final = MODE_CLIENT

CONNECT_TIMEOUT: Final = 5.0

# Serials are ten-digit ASCII codes (see the LuxPower Modbus spec).
SERIAL_LENGTH: Final = 10

MANUFACTURER: Final = "LuxPower"
DEFAULT_SCAN_INTERVAL: Final = 30

# Persisted discovery state (DiscoveryStore.to_dict) via HA's Store helper.
STORAGE_VERSION: Final = 1
DISCOVERY_SAVE_DELAY: Final = 30.0
