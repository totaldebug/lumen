"""A fake luxmodbus transport for tests — answers READ_INPUT requests."""

from __future__ import annotations

import struct

from luxmodbus import DataFrame, DeviceFunction, Frame, TcpFunction, Transport

_BLOCK = 40


def build_read_response(dongle: bytes, serial: bytes, function: int, start: int, raw_values: list[int]) -> bytes:
    """Build an encoded read response frame carrying ``raw_values``."""
    values = b"".join(struct.pack("<H", value & 0xFFFF) for value in raw_values)
    data = DataFrame(
        action=1,
        device_function=function,
        inverter_serial=serial,
        register=start,
        value=values,
        has_length_byte=True,
    ).encode()
    return Frame(tcp_function=TcpFunction.TRANSLATED_DATA, dongle_serial=dongle, data=data).encode()


class FakeTransport(Transport):
    """Echoes each READ_INPUT request with values equal to the register address."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__()
        self._connected = False
        self.sent: list[bytes] = []

    async def connect(self) -> None:
        self._connected = True

    async def close(self) -> None:
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def send(self, frame: bytes) -> None:
        self.sent.append(frame)
        request = Frame.decode(frame)
        # A read request has no length byte, so parse its inner fields directly
        # rather than via DataFrame.decode (which assumes the response form).
        inner = request.data
        function = inner[1]
        if function not in (DeviceFunction.READ_INPUT, DeviceFunction.READ_HOLD):
            return  # ignore writes and anything else
        serial = inner[2:12]
        start = int.from_bytes(inner[12:14], "little")
        raw_values = [start + offset for offset in range(_BLOCK)]
        self._emit_frame(build_read_response(request.dongle_serial, serial, function, start, raw_values))
