"""Timed-out receives must not keep occupying request slots."""

from __future__ import annotations

import asyncio

import pytest

from easywave_home_control.protocols.rx11_rx2x.protocol import ErrorCode, RxModule


def _accept_as_pending(module: RxModule) -> None:
    """Move a just-sent request into ``_req_pending``, as an IPP would."""
    original = module._place_request

    def place(req) -> None:
        original(req)
        if module._tx_req_sent_size == 0:
            return
        sent = module._dequeue_sent()
        assert sent is not None
        sent.handle = 0x10 + len(module._req_pending)
        module._req_pending[sent.handle] = sent

    module._place_request = place  # type: ignore[method-assign]


def test_ew_rcv_ex_timeout_releases_pending_slot() -> None:
    async def run() -> None:
        module = RxModule(port="/dev/ttyUSB_fake")
        module._write_wakeup = asyncio.Event()
        _accept_as_pending(module)

        result, _info_type, _serial, _data = await module.ew_rcv_ex_request(timeout=0.01)

        assert result == ErrorCode.ERR_RF_TIMEOUT
        assert module._req_pending == {}
        assert module._tx_req_sent_size == 0
        assert module._tx_req_queued_size == 0
        assert module._write_queue, "timed-out listen must be cancelled on the module"

    asyncio.run(run())


def test_cancelled_ew_rcv_ex_releases_pending_slot() -> None:
    async def run() -> None:
        module = RxModule(port="/dev/ttyUSB_fake")
        module._write_wakeup = asyncio.Event()
        _accept_as_pending(module)

        task = asyncio.create_task(module.ew_rcv_ex_request())
        for _ in range(50):
            if module._req_pending:
                break
            await asyncio.sleep(0.01)
        assert module._req_pending

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert module._req_pending == {}
        assert module._tx_req_sent_size == 0
        assert module._write_queue, "cancelled listen must be cancelled on the module"

    asyncio.run(run())


def test_cancelled_ew_rcv_ex_marks_unacknowledged_request() -> None:
    """Without an IPP handle, cancel stays armed until the module assigns one."""

    async def run() -> None:
        module = RxModule(port="/dev/ttyUSB_fake")
        module._write_wakeup = asyncio.Event()

        task = asyncio.create_task(module.ew_rcv_ex_request())
        for _ in range(50):
            if module._tx_req_sent_size:
                break
            await asyncio.sleep(0.01)
        assert module._tx_req_sent_size == 1

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert module._tx_req_sent_size == 1
        pending = module._tx_req_sent[module._tx_req_sent_front]
        assert pending is not None
        assert pending.cancel
        assert pending.icp.result == ErrorCode.ERR_CANCELED

    asyncio.run(run())


def test_cancelled_ping_on_dead_link_does_not_write_or_read() -> None:
    """A failed transport must not get CANCEL_IO or another read."""

    async def run() -> None:
        module = RxModule(port="/dev/ttyUSB_fake")
        module._write_wakeup = asyncio.Event()
        _accept_as_pending(module)

        task = asyncio.create_task(module.ping(timeout=5.0))
        for _ in range(50):
            if module._req_pending:
                break
            await asyncio.sleep(0.01)
        assert module._req_pending
        module._write_queue.clear()
        module._hardware_error = True
        module._connected = False

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert module._req_pending == {}
        assert list(module._write_queue) == []

        read_calls = 0

        class _DeadPort:
            is_open = True

            async def read(self, _n: int = -1) -> bytes:
                nonlocal read_calls
                read_calls += 1
                return b""

            async def write(self, _data: bytes) -> None:
                raise AssertionError("write on dead link")

            async def close(self) -> None:
                self.is_open = False

        module._serial = _DeadPort()  # type: ignore[assignment]
        await module.dispose()
        assert read_calls == 0

    asyncio.run(run())


def test_dispose_on_dead_link_does_not_wait_for_close() -> None:
    async def run() -> None:
        module = RxModule(port="/dev/ttyUSB_fake")
        module._hardware_error = True
        module._write_wakeup = asyncio.Event()

        class _HangingPort:
            is_open = True
            aborted = False

            def abort(self) -> None:
                self.aborted = True

            async def close(self) -> None:
                await asyncio.Event().wait()

            async def read(self, _n: int = -1) -> bytes:
                raise AssertionError("read on dead link")

            async def write(self, _data: bytes) -> None:
                raise AssertionError("write on dead link")

        port = _HangingPort()
        module._serial = port  # type: ignore[assignment]
        await asyncio.wait_for(module.dispose(), timeout=2.0)
        assert port.aborted
        assert module._serial is None

    asyncio.run(run())


def test_repeated_ew_rcv_ex_timeouts_do_not_fill_request_slots() -> None:
    async def run() -> None:
        module = RxModule(port="/dev/ttyUSB_fake")
        module._write_wakeup = asyncio.Event()
        _accept_as_pending(module)

        for _ in range(module.MAX_REQUEST_COUNT + 2):
            result, *_rest = await module.ew_rcv_ex_request(timeout=0.01)
            assert result == ErrorCode.ERR_RF_TIMEOUT
            assert not module._req_pending
            assert module._tx_req_sent_size == 0

    asyncio.run(run())
