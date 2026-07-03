#!/usr/bin/env python3
"""Example: Easywave send/receive with codec-decoded telegrams.

Demonstrates EW Basic workflows for RX11:
1. Discover gateways (EW_GET_FD_SERIAL)
2. Send a command (EW_SEND_CMD)
3. Receive and decode button/sensor telegrams via parse_ewb_rcv
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from easywave_home_control import RX11Device, RX11ErrorCode, parse_ewb_rcv
from easywave_home_control.codec.events import ButtonPushEvent, SensorTelegramEvent
from easywave_home_control.codec.sensors import SensorLearnPayload, SensorMeasurementPayload
from easywave_home_control.protocols.rx11_rx2x.protocol import InfoType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
_LOGGER = logging.getLogger(__name__)


def _print_decoded_event(info_type: int, serial: bytes, info_data: bytes) -> None:
    event = parse_ewb_rcv(info_type, serial, info_data)

    if isinstance(event, ButtonPushEvent):
        if event.should_ignore:
            print("  (Remote-learn telegram ignored by spec)")
            return
        print(f"  Button: {event.button.name}, function: {event.function.name}")
        return

    if isinstance(event, SensorTelegramEvent):
        payload = event.payload
        if isinstance(payload, SensorLearnPayload):
            caps = []
            if payload.measures_temperature:
                caps.append("temperature")
            if payload.measures_humidity:
                caps.append("humidity")
            print(f"  Sensor learn telegram, capabilities: {', '.join(caps) or 'none'}")
            return
        if isinstance(payload, SensorMeasurementPayload):
            if payload.temperature_celsius is not None:
                print(f"  Temperature: {payload.temperature_celsius:.1f} °C")
            if payload.humidity_percent is not None:
                print(f"  Humidity: {payload.humidity_percent:.1f} %")
            return

    print(f"  Decoded event: {type(event).__name__}")


async def ew_send_receive_rx11() -> None:
    """RX11 send/receive with codec decoding."""
    print("\n" + "=" * 80)
    print("RX11: Easywave Send & Receive (with codec)")
    print("=" * 80 + "\n")

    device: Optional[RX11Device] = None
    try:
        print("Creating RX11 USB Transceiver...")
        device = await RX11Device.create(port="/dev/ttyUSB0", timeout=5.0)
        print("Device connected\n")

        print("Step 1: Discovering Easywave gateways...")
        gateways: list[bytes] = []
        for index in range(10):
            result, gateway = await device.ew_get_fd_serial_request(index=index, timeout=2.0)  # type: ignore[attr-defined]
            if result == RX11ErrorCode.SUCCESS and gateway != b"\x00" * 16:
                gateways.append(gateway)
                print(f"   Gateway {index + 1}: {gateway.hex()}")
            else:
                break

        if not gateways:
            print("   No gateways found")
            return

        target_gateway = gateways[0]
        print(f"\nUsing gateway: {target_gateway.hex()}\n")

        print("Step 2: Sending command to gateway...")
        button = 0
        result = await device.ew_send_cmd_request(gateway=target_gateway, button=button, timeout=5.0)  # type: ignore[attr-defined]
        if result == RX11ErrorCode.SUCCESS:
            print(f"Command sent (Button {chr(65 + button)})\n")
        else:
            print(f"Send failed: error {result}\n")

        print("Step 3: Waiting for telegram (30 seconds, EW_RCV_EX for sensor support)...")
        try:
            result, info_type, serial, info_data = await device.ew_rcv_ex_request(timeout=30.0)  # type: ignore[attr-defined]

            if result == RX11ErrorCode.SUCCESS:
                print("Telegram received!")
                print(f"  Info Type:   0x{info_type:02X} ({InfoType(info_type).name if info_type in InfoType._value2member_map_ else 'unknown'})")
                print(f"  Serial:      {serial.hex()}")
                print(f"  Info Data:   {info_data.hex()}")
                _print_decoded_event(info_type, serial, info_data)
            else:
                print(f"Receive failed: error {result}")

        except asyncio.TimeoutError:
            print("Timeout waiting for response")

    except Exception as exc:
        _LOGGER.error("Error: %s", exc)
        print(f"Error: {exc}")

    finally:
        if device:
            print("\nDisconnecting...")
            await device.disconnect()
            print("Disconnected\n")


async def main() -> None:
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║              EASYWAVE SEND & RECEIVE (CODEC)                               ║
║                                                                            ║
║ Discover gateways, send commands, decode responses with parse_ewb_rcv      ║
╚════════════════════════════════════════════════════════════════════════════╝
""")

    await ew_send_receive_rx11()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted.\n")
