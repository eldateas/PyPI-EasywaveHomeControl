"""Tests for EasywaveGateway (mocked device layer)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from easywave_home_control.codec import SwitchPosition
from easywave_home_control.codec.common import encode_state_word
from easywave_home_control.gateway import (
    EasywaveGateway,
    GatewayCallbacks,
    GatewayConfig,
    GatewayConnectionState,
    RxModuleGateway,
)
from easywave_home_control.protocols.rx11_rx2x.protocol import ErrorCode


@pytest.fixture
def mock_device() -> MagicMock:
    device = MagicMock()
    device.connect = AsyncMock(return_value=True)
    device.disconnect = AsyncMock()
    device.ping_request = AsyncMock(return_value=True)
    device.query_hw_version = AsyncMock(return_value=(ErrorCode.SUCCESS, "RX11"))
    device.query_fw_version = AsyncMock(return_value=(ErrorCode.SUCCESS, "1.0"))
    device.set_disconnect_callback = MagicMock()
    device.set_reconnect_callback = MagicMock()
    device.ew_get_fd_serial_request = AsyncMock(return_value=(ErrorCode.SUCCESS, b"\x01" * 16))
    device.ew_send_cmd_request = AsyncMock(return_value=ErrorCode.SUCCESS)
    device.ew_rcv_ex_request = AsyncMock(side_effect=TimeoutError)
    switch_state = encode_state_word((3 << 27) | (int(SwitchPosition.ON) << 24))
    device.ewb_change_state_request = AsyncMock(
        return_value=(ErrorCode.SUCCESS, 0, switch_state)
    )
    device.sec_rcv_request = AsyncMock(return_value=(ErrorCode.SUCCESS, 0, 0, 0, 0, 0, 0))
    device.cancel_all_io_requests = AsyncMock()
    return device


def test_connect_sets_connected_state(mock_device: MagicMock) -> None:
    async def run() -> None:
        gateway = EasywaveGateway(GatewayConfig(port="/dev/ttyUSB0", settle_seconds=0))
        with patch(
            "easywave_home_control.gateway.gateway.create_rx_device",
            return_value=mock_device,
        ):
            assert await gateway.connect() is True
        assert gateway.is_connected
        assert gateway.state == GatewayConnectionState.CONNECTED
        assert gateway.hw_version == "RX11"
        assert gateway.transceiver_id == "RX11"
        await gateway.stop()

    asyncio.run(run())


def test_rx22_transceiver_id(mock_device: MagicMock) -> None:
    async def run() -> None:
        gateway = RxModuleGateway(
            GatewayConfig(transceiver_id="RX22", port="/dev/ttyAMA0", settle_seconds=0)
        )
        with patch(
            "easywave_home_control.gateway.gateway.create_rx_device",
            return_value=mock_device,
        ) as create:
            await gateway.connect()
            create.assert_called_once_with("RX22", "/dev/ttyAMA0")
        await gateway.stop()

    asyncio.run(run())


def test_start_invokes_on_connected_callback(mock_device: MagicMock) -> None:
    async def run() -> None:
        connected: list[str] = []

        async def on_connected(info) -> None:
            connected.append(info.device_path)

        gateway = EasywaveGateway(
            GatewayConfig(port="/dev/ttyUSB0", settle_seconds=0, auto_reconnect=False),
            callbacks=GatewayCallbacks(on_connected=on_connected),
        )
        with patch(
            "easywave_home_control.gateway.gateway.create_rx_device",
            return_value=mock_device,
        ):
            await gateway.start()
        assert connected == ["/dev/ttyUSB0"]
        await gateway.stop()

    asyncio.run(run())


def test_health_check_disconnects_after_failures(mock_device: MagicMock) -> None:
    async def run() -> None:
        mock_device.ping_request = AsyncMock(return_value=False)
        disconnected = asyncio.Event()

        gateway = EasywaveGateway(
            GatewayConfig(
                port="/dev/ttyUSB0",
                settle_seconds=0,
                health_check_interval=0.05,
                health_check_max_failures=2,
                auto_reconnect=False,
            ),
            callbacks=GatewayCallbacks(on_disconnected=disconnected.set),
        )
        with patch(
            "easywave_home_control.gateway.gateway.create_rx_device",
            return_value=mock_device,
        ):
            await gateway.start()
            await asyncio.wait_for(disconnected.wait(), timeout=2.0)
        assert gateway.state == GatewayConnectionState.DISCONNECTED
        await gateway.stop()

    asyncio.run(run())


def test_ew_send_command_facade(mock_device: MagicMock) -> None:
    async def run() -> None:
        gateway = EasywaveGateway(GatewayConfig(port="/dev/ttyUSB0", settle_seconds=0))
        with patch(
            "easywave_home_control.gateway.gateway.create_rx_device",
            return_value=mock_device,
        ):
            await gateway.connect()
            assert await gateway.ew.send_command(b"\x00" * 16, 0) is True
        await gateway.stop()

    asyncio.run(run())


def test_ewb_change_state_facade(mock_device: MagicMock) -> None:
    async def run() -> None:
        from easywave_home_control.codec import SwitchChangeCommand, SwitchDesiredAction
        from easywave_home_control.protocols.rx11_rx2x.protocol import DeviceType

        gateway = EasywaveGateway(GatewayConfig(port="/dev/ttyUSB0", settle_seconds=0))
        with patch(
            "easywave_home_control.gateway.gateway.create_rx_device",
            return_value=mock_device,
        ):
            await gateway.connect()
            result = await gateway.ewb.change_state(
                b"\x01" * 16,
                b"\x02" * 16,
                DeviceType.EWB_DT_SWITCH,
                0,
                SwitchChangeCommand(action=SwitchDesiredAction.ON),
            )
        assert result is not None
        assert result[0] == ErrorCode.SUCCESS
        await gateway.stop()

    asyncio.run(run())


def test_sec_receive_facade(mock_device: MagicMock) -> None:
    async def run() -> None:
        gateway = EasywaveGateway(GatewayConfig(port="/dev/ttyUSB0", settle_seconds=0))
        with patch(
            "easywave_home_control.gateway.gateway.create_rx_device",
            return_value=mock_device,
        ):
            await gateway.connect()
            result = await gateway.sec.receive(timeout=0.01)
        assert result is not None
        assert result[0] == ErrorCode.SUCCESS
        assert result[1] is not None
        await gateway.stop()

    asyncio.run(run())
