"""Data update coordinator for Lumen.

Owns the refresh cycle, holds the decoded register state, and pushes updates to
entities. In **client mode** it actively polls the dongle (sends READ_INPUT /
READ_HOLD requests in blocks and collects the responses); in **server mode** it
works off the frames the dongle pushes. It also exposes write methods for the
number and switch platforms. Framing, the register map and discovery all come
from the Home-Assistant-free ``luxmodbus`` library.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from luxmodbus import (
    FLAG_REGISTERS,
    DataFrame,
    DeviceFunction,
    DiscoveryStore,
    FlagDef,
    Frame,
    ProtocolError,
    RegisterBank,
    TcpFunction,
    Transport,
    TransportError,
    UnknownRegister,
    decode_flags,
    decode_holds,
    decode_inputs,
    decode_read_response,
    set_flag,
)

from .const import DEFAULT_SCAN_INTERVAL, DISCOVERY_SAVE_DELAY, DOMAIN, MANUFACTURER, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)

# Listener notified with the registers discovered in a single ingest.
type DiscoveryListener = Callable[[list[UnknownRegister]], None]

# (start, count) blocks covering the full mapped register space: input ends at
# 232 (smart_load_power), hold at 228 (ac_couple / bat_stop_charge), so both
# banks are polled across 0-239.
READ_BLOCKS_INPUT: tuple[tuple[int, int], ...] = ((0, 40), (40, 40), (80, 40), (120, 40), (160, 40), (200, 40))
READ_BLOCKS_HOLD: tuple[tuple[int, int], ...] = ((0, 40), (40, 40), (80, 40), (120, 40), (160, 40), (200, 40))
RESPONSE_TIMEOUT = 10.0
# A discovery sweep reads well past the known map; unsupported ranges simply
# time out, so use a short per-block timeout to keep the whole sweep snappy.
SWEEP_TIMEOUT = 3.0
SWEEP_BLOCK = 40

_BANK_FOR: dict[int, RegisterBank] = {
    DeviceFunction.READ_INPUT: RegisterBank.INPUT,
    DeviceFunction.READ_HOLD: RegisterBank.HOLD,
}
_FUNCTION_FOR: dict[RegisterBank, DeviceFunction] = {
    RegisterBank.INPUT: DeviceFunction.READ_INPUT,
    RegisterBank.HOLD: DeviceFunction.READ_HOLD,
}

type LumenData = dict[str, float | int | bool | str]


class LumenCoordinator(DataUpdateCoordinator[LumenData]):
    """Polls (or receives) inverter data, decodes it, and writes settings."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        transport: Transport,
        *,
        client_mode: bool,
        dongle_serial: bytes,
        inverter_serial: bytes,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL) if client_mode else None,
        )
        self._transport = transport
        self._client_mode = client_mode
        self._dongle = dongle_serial
        self._serial = inverter_serial
        self._raw: dict[RegisterBank, dict[int, int]] = {RegisterBank.INPUT: {}, RegisterBank.HOLD: {}}
        self._pending: set[tuple[int, int]] = set()
        self._received = asyncio.Event()
        self.discovery = DiscoveryStore.from_registers()
        self.serial_id = dongle_serial.decode("ascii", "replace")
        self.inverter_id = inverter_serial.decode("ascii", "replace")
        self._discovery_store: Store[dict] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{self.serial_id}.discovery")
        self._discovery_listeners: list[DiscoveryListener] = []
        # The dongle is the communication gateway; the inverter hangs off it via
        # via_device, so Home Assistant shows a Dongle -> Inverter hierarchy.
        self.dongle_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.serial_id)},
            name=f"{entry.title} Dongle",
            manufacturer=MANUFACTURER,
            model="Datalogger Dongle",
            serial_number=self.serial_id,
        )
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, self.inverter_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model="LuxPower Inverter",
            serial_number=self.inverter_id,
            via_device=(DOMAIN, self.serial_id),
        )
        self._unsubscribe = transport.on_frame(self._on_frame)

    async def async_setup(self) -> None:
        """Load persisted discovery state and establish the transport connection."""
        stored = await self._discovery_store.async_load()
        if stored is not None:
            self.discovery.load(stored)
        await self._transport.connect()

    @callback
    def add_discovery_listener(self, listener: DiscoveryListener) -> Callable[[], None]:
        """Register ``listener`` for newly-discovered registers; returns an unsubscribe."""
        self._discovery_listeners.append(listener)

        def _unsubscribe() -> None:
            """Remove the listener."""
            self._discovery_listeners.remove(listener)

        return _unsubscribe

    async def async_shutdown(self) -> None:
        """Tear down the transport and stop updates."""
        self._unsubscribe()
        await self._transport.close()
        await super().async_shutdown()

    def _decode(self) -> LumenData:
        """Build the merged {key: value} map from inputs, holds and flag bits."""
        data: LumenData = {}
        data.update(decode_inputs(self._raw[RegisterBank.INPUT]))
        hold = self._raw[RegisterBank.HOLD]
        data.update(decode_holds(hold))
        for flag_register in FLAG_REGISTERS:
            if flag_register.address in hold:
                data.update(decode_flags(hold[flag_register.address], flag_register))
        return data

    def _wrap(self, data_frame: DataFrame) -> bytes:
        """Wrap an inner data frame in the dongle's TCP envelope and encode it."""
        return Frame(
            tcp_function=TcpFunction.TRANSLATED_DATA, dongle_serial=self._dongle, data=data_frame.encode()
        ).encode()

    def _read_frame(self, function: DeviceFunction, start: int, count: int) -> bytes:
        """Build an encoded read request for ``count`` registers from ``start``."""
        builder = DataFrame.read_input if function == DeviceFunction.READ_INPUT else DataFrame.read_hold
        return self._wrap(builder(self._serial, start, count))

    def _write_frame(self, register: int, value: int) -> bytes:
        """Build an encoded WRITE_SINGLE request for one hold register."""
        return self._wrap(DataFrame.write_single(self._serial, register, value))

    def _parse_data_frame(self, raw: bytes) -> DataFrame | None:
        """Decode a raw frame to its inner data frame, or None if undecodable or not data."""
        try:
            frame = Frame.decode(raw)
        except ProtocolError as err:
            _LOGGER.debug("ignoring undecodable frame: %s", err)
            return None
        if frame.tcp_function != TcpFunction.TRANSLATED_DATA:
            return None
        try:
            return frame.data_frame()
        except ProtocolError as err:
            _LOGGER.debug("ignoring undecodable data frame: %s", err)
            return None

    def _on_frame(self, raw: bytes) -> None:
        """Decode an incoming frame and ingest any read response."""
        data_frame = self._parse_data_frame(raw)
        if data_frame is None:
            return
        bank = _BANK_FOR.get(data_frame.device_function)
        if bank is None:
            return
        self._ingest(bank, data_frame)
        if not self._client_mode and self._raw[RegisterBank.INPUT]:
            self.async_set_updated_data(self._decode())

    def _ingest(self, bank: RegisterBank, data_frame: DataFrame) -> None:
        """Merge a read response into the raw store for ``bank`` and feed discovery."""
        store = self._raw[bank]
        values = decode_read_response(data_frame)
        store.update(values)
        discovered = self.discovery.observe_many(bank, values)
        if discovered:
            self._discovery_store.async_delay_save(self.discovery.to_dict, DISCOVERY_SAVE_DELAY)
            for listener in list(self._discovery_listeners):
                listener(discovered)
        self._pending.discard((data_frame.device_function, data_frame.register))
        if not self._pending:
            self._received.set()

    async def _async_update_data(self) -> LumenData:
        """Poll the inverter (client mode) or return the latest pushed state."""
        if not self._client_mode:
            return self._decode()

        if not self._transport.is_connected:
            raise UpdateFailed("transport is not connected")

        requests = [(DeviceFunction.READ_INPUT, start, count) for start, count in READ_BLOCKS_INPUT]
        requests += [(DeviceFunction.READ_HOLD, start, count) for start, count in READ_BLOCKS_HOLD]
        self._pending = {(function, start) for function, start, _ in requests}
        self._received.clear()
        try:
            for function, start, count in requests:
                await self._transport.send(self._read_frame(function, start, count))
        except TransportError as err:
            raise UpdateFailed(f"failed to send read request: {err}") from err

        try:
            async with asyncio.timeout(RESPONSE_TIMEOUT):
                await self._received.wait()
        except TimeoutError:
            if not self._raw[RegisterBank.INPUT] and not self._raw[RegisterBank.HOLD]:
                raise UpdateFailed("no response from inverter") from None
            _LOGGER.debug("partial response; missing blocks: %s", self._pending)

        return self._decode()

    def raw_hold(self, address: int) -> int | None:
        """Return the latest raw value of hold register ``address``, or None if unread."""
        return self._raw[RegisterBank.HOLD].get(address)

    async def _request_and_wait(
        self, function: DeviceFunction, start: int, count: int, *, timeout: float
    ) -> dict[int, int] | None:
        """Send one read and return the responded ``{address: value}`` block, or None on timeout.

        A short-lived frame listener resolves as soon as the matching response
        arrives, so it does not disturb the polling state machine. The response
        is also seen by the main frame handler, so discovery is fed as a side
        effect.
        """
        if not self._transport.is_connected:
            raise HomeAssistantError("inverter is not connected")
        bank = _BANK_FOR[function]
        future: asyncio.Future[dict[int, int]] = self.hass.loop.create_future()

        def _await_response(raw: bytes) -> None:
            """Resolve the future when the response covering ``start`` arrives."""
            data_frame = self._parse_data_frame(raw)
            if data_frame is None or _BANK_FOR.get(data_frame.device_function) is not bank:
                return
            words = len(data_frame.value) // 2
            if data_frame.register <= start < data_frame.register + words and not future.done():
                future.set_result(decode_read_response(data_frame))

        unsubscribe = self._transport.on_frame(_await_response)
        try:
            await self._transport.send(self._read_frame(function, start, count))
            async with asyncio.timeout(timeout):
                return await future
        except TransportError as err:
            raise HomeAssistantError(f"failed to read register {start}: {err}") from err
        except TimeoutError:
            return None
        finally:
            unsubscribe()

    async def async_read_register(self, bank: RegisterBank, address: int) -> int | None:
        """Read one register on demand, returning its raw value or None on timeout.

        Used by the ``read_register`` service to probe a register (e.g. one
        surfaced by discovery) without waiting for the next poll.
        """
        values = await self._request_and_wait(_FUNCTION_FOR[bank], address, 1, timeout=RESPONSE_TIMEOUT)
        return None if values is None else values.get(address)

    async def async_sweep(self, *, input_end: int = 256, hold_end: int = 256) -> int:
        """Read input and hold registers across a wide range to feed discovery.

        Reads beyond the regularly polled blocks so the discovery store learns
        about registers Lumen does not normally read. Reads are passive; each
        response is ingested by the main frame handler, which records unmapped
        registers and fires the discovery event. Returns the resulting count of
        distinct unknown registers.
        """
        if not self._transport.is_connected:
            raise HomeAssistantError("inverter is not connected")
        plan = [(DeviceFunction.READ_INPUT, start) for start in range(0, input_end, SWEEP_BLOCK)]
        plan += [(DeviceFunction.READ_HOLD, start) for start in range(0, hold_end, SWEEP_BLOCK)]
        for function, start in plan:
            await self._request_and_wait(function, start, SWEEP_BLOCK, timeout=SWEEP_TIMEOUT)
        return self.discovery.count()

    async def async_write_register(self, register: int, value: int) -> None:
        """Write a single hold register, then optimistically reflect the change."""
        if not self._transport.is_connected:
            raise HomeAssistantError("inverter is not connected")
        try:
            await self._transport.send(self._write_frame(register, value))
        except TransportError as err:
            raise HomeAssistantError(f"failed to write register {register}: {err}") from err
        self._raw[RegisterBank.HOLD][register] = value & 0xFFFF
        self.async_set_updated_data(self._decode())

    async def async_set_flag(self, address: int, flag: FlagDef, on: bool) -> None:
        """Set or clear one bit of a flag register via read-modify-write."""
        current = self._raw[RegisterBank.HOLD].get(address, 0)
        await self.async_write_register(address, set_flag(current, flag, on))
