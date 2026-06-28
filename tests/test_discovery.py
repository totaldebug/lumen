"""Tests for the Lumen discovery entities and persistence."""

from homeassistant.const import EVENT_HOMEASSISTANT_FINAL_WRITE
from homeassistant.core import HomeAssistant
from luxmodbus import DeviceFunction
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.lumen.const import DOMAIN
from custom_components.lumen.coordinator import LumenCoordinator

from .test_coordinator import DONGLE, SERIAL, _entry
from .fake_transport import FakeTransport, build_read_response

UNDECODED_SENSOR = "sensor.lumen_undecoded_registers"
NEW_REGISTER_EVENT = "event.lumen_new_register_seen"
STORE_KEY = f"{DOMAIN}.BA12345678.discovery"


async def test_undecoded_sensor_counts_and_lists(hass: HomeAssistant, setup_lumen: MockConfigEntry) -> None:
    """The diagnostic sensor exposes the unmapped-register count and a listing."""
    state = hass.states.get(UNDECODED_SENSOR)
    assert state is not None
    count = int(state.state)
    assert count > 0

    registers = state.attributes["registers"]
    assert len(registers) == count
    sample = registers[0]
    assert set(sample) == {"bank", "address", "last_value", "times_seen"}
    assert sample["bank"] in ("input", "hold")


async def test_new_register_event_fires(hass: HomeAssistant, setup_lumen: MockConfigEntry) -> None:
    """A register that appears after setup triggers the discovery event entity."""
    # No event yet — nothing new has arrived since the entity subscribed.
    assert hass.states.get(NEW_REGISTER_EVENT).state == "unknown"

    # Push a frame carrying an address beyond the mapped range (map reaches 232).
    coordinator: LumenCoordinator = setup_lumen.runtime_data
    coordinator._transport._emit_frame(
        build_read_response(DONGLE, SERIAL, DeviceFunction.READ_INPUT, 300, [4242])
    )
    await hass.async_block_till_done()

    state = hass.states.get(NEW_REGISTER_EVENT)
    assert state.state != "unknown"
    assert state.attributes["event_type"] == "new_register"
    assert state.attributes["bank"] == "input"
    assert state.attributes["address"] == 300
    assert state.attributes["last_value"] == 4242


async def test_discovery_persists_across_restart(hass: HomeAssistant, hass_storage: dict) -> None:
    """Discovered registers survive a restart via the Store helper."""
    entry = _entry(hass)
    first = LumenCoordinator(
        hass, entry, FakeTransport(), client_mode=True, dongle_serial=DONGLE, inverter_serial=SERIAL
    )
    await first.async_setup()
    await first.async_refresh()
    count = first.discovery.count()
    assert count > 0

    # Flush the debounced save, then confirm it landed in storage.
    hass.bus.async_fire(EVENT_HOMEASSISTANT_FINAL_WRITE)
    await hass.async_block_till_done()
    assert len(hass_storage[STORE_KEY]["data"]["records"]) == count
    await first.async_shutdown()

    # A fresh coordinator for the same dongle restores the records on setup.
    second = LumenCoordinator(
        hass, entry, FakeTransport(), client_mode=True, dongle_serial=DONGLE, inverter_serial=SERIAL
    )
    await second.async_setup()
    assert second.discovery.count() == count
    await second.async_shutdown()
