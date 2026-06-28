"""Tests for the Lumen coordinator."""

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant
from luxmodbus import DeviceFunction
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lumen.const import (
    CONF_DONGLE_SERIAL,
    CONF_MODE,
    CONF_SERIAL,
    DOMAIN,
    MODE_CLIENT,
    MODE_SERVER,
)
from custom_components.lumen.coordinator import LumenCoordinator

from .fake_transport import FakeTransport, build_read_response

DONGLE = b"BA12345678"
SERIAL = b"1234567890"


def _entry(hass: HomeAssistant, mode: str = MODE_CLIENT) -> MockConfigEntry:
    """Add and return a config entry for the coordinator under test."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Lumen",
        unique_id=DONGLE.decode(),
        data={
            CONF_NAME: "Lumen",
            CONF_HOST: "1.2.3.4",
            CONF_PORT: 8000,
            CONF_MODE: mode,
            CONF_DONGLE_SERIAL: DONGLE.decode(),
            CONF_SERIAL: SERIAL.decode(),
        },
    )
    entry.add_to_hass(hass)
    return entry


async def test_client_mode_polls_and_decodes(hass: HomeAssistant) -> None:
    """Client mode sends read requests and decodes the responses."""
    entry = _entry(hass)
    transport = FakeTransport()
    coordinator = LumenCoordinator(
        hass, entry, transport, client_mode=True, dongle_serial=DONGLE, inverter_serial=SERIAL
    )
    await coordinator.async_setup()
    await coordinator.async_refresh()

    # FakeTransport returns each register's address as its raw value.
    assert coordinator.data["pv1_voltage"] == 0.1  # input addr 1 * 0.1
    assert coordinator.data["battery_voltage"] == 0.4  # input addr 4 * 0.1
    assert coordinator.data["grid_frequency"] == 0.15  # input addr 15 * 0.01
    assert coordinator.data["system_charge_rate"] == 64  # hold addr 64
    assert coordinator.data["eps_enable"] is True  # reg 21 == 0b10101 -> bit 0 set
    assert coordinator.data["ac_charge_enable"] is False  # reg 21 bit 7 clear
    # Five input blocks + three hold blocks.
    assert len(transport.sent) == 8

    await coordinator.async_shutdown()


async def test_discovery_records_unmapped(hass: HomeAssistant) -> None:
    """Addresses polled but absent from the map are recorded for discovery."""
    entry = _entry(hass)
    coordinator = LumenCoordinator(
        hass, entry, FakeTransport(), client_mode=True, dongle_serial=DONGLE, inverter_serial=SERIAL
    )
    await coordinator.async_setup()
    await coordinator.async_refresh()

    assert coordinator.discovery.count() > 0
    await coordinator.async_shutdown()


async def test_server_mode_push(hass: HomeAssistant) -> None:
    """Server mode decodes frames pushed by the dongle."""
    entry = _entry(hass, mode=MODE_SERVER)
    transport = FakeTransport()
    coordinator = LumenCoordinator(
        hass, entry, transport, client_mode=False, dongle_serial=DONGLE, inverter_serial=SERIAL
    )
    await coordinator.async_setup()
    await coordinator.async_refresh()  # no data yet
    assert coordinator.data == {}

    transport._emit_frame(build_read_response(DONGLE, SERIAL, DeviceFunction.READ_INPUT, 0, [0, 25, 0, 0, 53]))
    assert coordinator.data["battery_voltage"] == 5.3  # addr 4 = 53 * 0.1

    await coordinator.async_shutdown()


async def test_serial_number_decodes_as_string(hass: HomeAssistant) -> None:
    """The ASCII serial register (115-119) decodes to a string in coordinator data."""
    entry = _entry(hass, mode=MODE_SERVER)
    transport = FakeTransport()
    coordinator = LumenCoordinator(
        hass, entry, transport, client_mode=False, dongle_serial=DONGLE, inverter_serial=SERIAL
    )
    await coordinator.async_setup()
    await coordinator.async_refresh()

    serial_words = [0x3033, 0x3233, 0x3533, 0x3130, 0x3730]
    transport._emit_frame(build_read_response(DONGLE, SERIAL, DeviceFunction.READ_INPUT, 115, serial_words))
    assert coordinator.data["serial_number"] == "3032350107"

    await coordinator.async_shutdown()
