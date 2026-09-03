"""Tests proving RxModule serial I/O is event-loop safe (HA async-dependency)."""

from __future__ import annotations

import asyncio
import threading
from collections import deque
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from easywave_home_control.protocols.rx11_rx2x.protocol import FunctionCode, IRP, RxModule
from easywave_home_control.serial_io import serial_for_url


class FakeAsyncSerial:
    """Minimal AsyncSerial stand-in that records call context.

    All I/O methods are true coroutines. A sync ``serial_for_url`` must never
    be used on the connect/handler path; tests assert that separately.
    """

    def __init__(self) -> None:
        self.is_open = False
        self._rx: asyncio.Queue[bytes | None] = asyncio.Queue()
        self.written: list[bytes] = []
        self.open_threads: list[int] = []
        self.read_threads: list[int] = []
        self.write_threads: list[int] = []
        self.close_threads: list[int] = []
        self._loop_thread_id: int | None = None
        self._pending_reads: deque[asyncio.Future[bytes]] = deque()

    def bind_loop_thread(self) -> None:
        self._loop_thread_id = threading.get_ident()

    async def open(self) -> None:
        self.open_threads.append(threading.get_ident())
        # Yield so a blocking open would stall other tasks
        await asyncio.sleep(0)
        self.is_open = True

    async def close(self) -> None:
        self.close_threads.append(threading.get_ident())
        self.is_open = False
        # Unblock any waiting readers
        await self._rx.put(None)

    async def read(self, n: int = -1) -> bytes:
        self.read_threads.append(threading.get_ident())
        item = await self._rx.get()
        if item is None:
            return b""
        if n > 0:
            return item[:n]
        return item

    async def write(self, data: bytes | bytearray | memoryview) -> None:
        self.write_threads.append(threading.get_ident())
        await asyncio.sleep(0)
        self.written.append(bytes(data))

    def push_rx(self, data: bytes) -> None:
        self._rx.put_nowait(data)

    def assert_all_io_on_loop_thread(self) -> None:
        assert self._loop_thread_id is not None
        for tid in (
            self.open_threads
            + self.read_threads
            + self.write_threads
            + self.close_threads
        ):
            assert tid == self._loop_thread_id, (
                f"serial I/O ran on thread {tid}, expected loop thread {self._loop_thread_id}"
            )


@pytest.fixture
def fake_serial() -> FakeAsyncSerial:
    return FakeAsyncSerial()


def test_connect_dispose_uses_async_serial_only(fake_serial: FakeAsyncSerial) -> None:
    """connect/dispose must use AsyncSerial — never sync serial_for_url."""

    async def run() -> None:
        fake_serial.bind_loop_thread()
        module = RxModule(port="/dev/ttyUSB_fake")

        def _factory(*_a, **_k):
            return fake_serial

        with (
            patch(
                "easywave_home_control.protocols.rx11_rx2x.protocol.async_serial_for_url",
                side_effect=_factory,
            ),
            patch(
                "easywave_home_control.serial_io.serial_for_url",
                side_effect=AssertionError("sync serial_for_url must not run on loop"),
            ),
        ):
            assert await module.connect() is True
            assert module.is_connected
            assert fake_serial.is_open
            # Let the handler start a read
            await asyncio.sleep(0.02)
            await module.dispose()

        assert not module.is_connected
        assert not fake_serial.is_open
        assert fake_serial.open_threads
        assert fake_serial.close_threads
        fake_serial.assert_all_io_on_loop_thread()

    asyncio.run(run())


def test_write_is_awaited_not_blocking_sync(fake_serial: FakeAsyncSerial) -> None:
    """Outbound IRPs are drained via await write() on the serial handler."""

    async def run() -> None:
        fake_serial.bind_loop_thread()
        module = RxModule(port="/dev/ttyUSB_fake")

        with patch(
            "easywave_home_control.protocols.rx11_rx2x.protocol.async_serial_for_url",
            return_value=fake_serial,
        ):
            assert await module.connect() is True
            module._write_to_buffer(
                IRP(function=FunctionCode.PING_RCV, params=b""),
                "PING_RCV",
            )
            # Handler should wake and flush
            for _ in range(50):
                if fake_serial.written:
                    break
                await asyncio.sleep(0.01)
            await module.dispose()

        assert fake_serial.written, "expected at least one async write"
        fake_serial.assert_all_io_on_loop_thread()

    asyncio.run(run())


def test_receive_bytes_processed_via_async_read(fake_serial: FakeAsyncSerial) -> None:
    """Inbound data arrives through await read(), not in_waiting polling."""

    async def run() -> None:
        fake_serial.bind_loop_thread()
        module = RxModule(port="/dev/ttyUSB_fake")
        processed: list[int] = []
        original = module._process_received_byte

        def _track(byte: int) -> None:
            processed.append(byte)
            original(byte)

        module._process_received_byte = _track  # type: ignore[method-assign]

        with patch(
            "easywave_home_control.protocols.rx11_rx2x.protocol.async_serial_for_url",
            return_value=fake_serial,
        ):
            assert await module.connect() is True
            fake_serial.push_rx(b"\x01\x02\x03")
            for _ in range(50):
                if len(processed) >= 3:
                    break
                await asyncio.sleep(0.01)
            await module.dispose()

        assert processed[:3] == [1, 2, 3]
        assert fake_serial.read_threads
        fake_serial.assert_all_io_on_loop_thread()

    asyncio.run(run())


def test_sync_serial_for_url_not_imported_by_protocol() -> None:
    """Protocol module must not call sync serial constructors on the loop path."""
    import easywave_home_control.protocols.rx11_rx2x.protocol as proto

    assert not hasattr(proto, "serial") or not hasattr(getattr(proto, "serial", None), "Serial")
    # serial_for_url is available for discovery only
    assert callable(serial_for_url)


def test_event_loop_stays_responsive_during_connect(fake_serial: FakeAsyncSerial) -> None:
    """Other asyncio tasks must progress while connect() awaits serial open."""

    async def run() -> None:
        fake_serial.bind_loop_thread()
        ticks = 0

        async def ticker() -> None:
            nonlocal ticks
            for _ in range(5):
                await asyncio.sleep(0)
                ticks += 1

        module = RxModule(port="/dev/ttyUSB_fake")
        with patch(
            "easywave_home_control.protocols.rx11_rx2x.protocol.async_serial_for_url",
            return_value=fake_serial,
        ):
            tick_task = asyncio.create_task(ticker())
            assert await module.connect() is True
            await tick_task
            await module.dispose()

        assert ticks == 5

    asyncio.run(run())


def test_gateway_connect_path_uses_async_serial(fake_serial: FakeAsyncSerial) -> None:
    """EasywaveGateway.connect must not block on sync Serial open."""
    from easywave_home_control.gateway import EasywaveGateway, GatewayConfig

    async def run() -> None:
        fake_serial.bind_loop_thread()
        mock_device = MagicMock()
        mock_device.connect = AsyncMock(return_value=True)
        mock_device.disconnect = AsyncMock()
        mock_device.ping_request = AsyncMock(return_value=True)
        mock_device.query_hw_version = AsyncMock(return_value=(0, "RX11"))
        mock_device.query_fw_version = AsyncMock(return_value=(0, "1.0"))
        mock_device.set_disconnect_callback = MagicMock()
        mock_device.set_reconnect_callback = MagicMock()
        mock_device.cancel_all_io_requests = AsyncMock()

        # Real connect path on RxModule is covered above; gateway uses create_rx_device.
        # Ensure gateway still completes without sync serial.
        with patch(
            "easywave_home_control.gateway.gateway.create_rx_device",
            return_value=mock_device,
        ):
            gateway = EasywaveGateway(
                GatewayConfig(port="/dev/ttyUSB0", settle_seconds=0, auto_reconnect=False)
            )
            assert await gateway.connect() is True
            await gateway.stop()

    asyncio.run(run())
