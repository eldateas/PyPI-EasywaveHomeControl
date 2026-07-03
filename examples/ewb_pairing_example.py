#!/usr/bin/env python3
"""Example: Easywave Bidi device pairing, state control, and monitoring.

Demonstrates the EWB workflow with the codec layer:
1. Get gateway serial number (EWB_GET_FD_SERIAL)
2. Add filter (EWB_ADD_NFILTER)
3. Join a new neo receiver (EWB_JOIN_DEVICE)
4. Query and change state via parse_ewb_state / encode_ewb_state
5. Listen for spontaneous state changes via parse_ewb_rcv
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from easywave_home_control import (
    RX11Device,
    RX11ErrorCode,
    encode_ewb_state,
    parse_ewb_rcv,
    parse_ewb_state,
)
from easywave_home_control.codec import (
    StateDirection,
    SwitchChangeCommand,
    SwitchDesiredAction,
    SwitchOnOffState,
)
from easywave_home_control.codec.events import (
    ButtonPushEvent,
    EwbRcvEvent,
    EwbStateChangeEvent,
    TransmitterLearnSuccessEvent,
)
from easywave_home_control.protocols.rx11_rx2x.protocol import DeviceType, InfoType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
_LOGGER = logging.getLogger(__name__)


@dataclass
class LearnedEwbDevice:
    """A paired Easywave neo receiver known to the host application."""

    name: str
    gateway_serial: bytes
    receiver_serial: bytes
    device_type: DeviceType


def _format_state(device_type: DeviceType, mode: int, state) -> str:
    if isinstance(state, SwitchOnOffState):
        return f"switch {state.position.name} (counter={state.pulse_counter})"
    return f"{type(state).__name__}(mode={mode}, device=0x{int(device_type):02x})"


def _handle_ewb_event(event: EwbRcvEvent, known_devices: dict[bytes, LearnedEwbDevice]) -> None:
    if isinstance(event, EwbStateChangeEvent):
        device = known_devices.get(event.receiver_serial)
        label = device.name if device else event.receiver_serial.hex()
        print(f"  State change on {label}: {_format_state(device.device_type if device else DeviceType.EWB_DT_SWITCH, event.mode, event.state)}")
        return

    if isinstance(event, ButtonPushEvent):
        print(f"  Button push from {event.transmitter_serial.hex()}: {event.button.name} ({event.function.name})")
        return

    if isinstance(event, TransmitterLearnSuccessEvent):
        print(f"  Transmitter learned on {event.receiver_serial.hex()}")
        return

    print(f"  EWB event: {type(event).__name__}")


async def ewb_pair_and_learn_device() -> Optional[LearnedEwbDevice]:
    """Learn a new EWB receiver and query its initial state."""
    print("\n" + "=" * 80)
    print("RX11: Easywave Bidi Device Learning with Gateway Serial")
    print("=" * 80 + "\n")

    device: Optional[RX11Device] = None
    learned: Optional[LearnedEwbDevice] = None
    try:
        print("Creating RX11 USB Transceiver...")
        device = await RX11Device.create(port="/dev/ttyUSB0", timeout=5.0)
        print("Device connected\n")

        print("Step 1: Loading gateway serial number...")
        result, gateway_serial = await device.ewb_get_fd_serial_request(index=0, timeout=2.0)  # type: ignore[attr-defined]

        if result != RX11ErrorCode.SUCCESS or gateway_serial == b"\x00" * 16:
            print("No gateway found or error loading serial")
            return None

        print(f"Gateway serial: {gateway_serial.hex()}\n")

        print("Step 2: Setting up filter with gateway serial...")
        result = await device.ewb_add_nfilter_request(gateway=gateway_serial, timeout=5.0)  # type: ignore[attr-defined]
        if result != RX11ErrorCode.SUCCESS:
            print(f"Filter setup failed: error {result}")
            return None
        print("Filter configured\n")

        print("Step 3: Learning new device (30 seconds)...")
        print("   >> Put device in learning mode NOW <<\n")

        result, device_type_value, receiver_serial = await device.ewb_join_device_request(  # type: ignore[attr-defined]
            gateway=gateway_serial, timeout=30.0
        )

        if result != RX11ErrorCode.SUCCESS:
            print(f"Device learning failed: error {result}")
            return None

        device_type = DeviceType(device_type_value)
        learned = LearnedEwbDevice(
            name="neo-receiver",
            gateway_serial=gateway_serial,
            receiver_serial=receiver_serial,
            device_type=device_type,
        )
        print("Device learned successfully!")
        print(f"  Device Type:     0x{device_type_value:02X} ({device_type.name})")
        print(f"  Receiver Serial: {receiver_serial.hex()}\n")

        print("Step 4: Querying initial state (codec parse_ewb_state)...")
        result, mode, raw_state = await device.ewb_query_state_request(  # type: ignore[attr-defined]
            gateway=gateway_serial,
            receiver=receiver_serial,
            desired_mode=0,
            timeout=5.0,
        )
        if result == RX11ErrorCode.SUCCESS:
            parsed = parse_ewb_state(device_type, mode, raw_state)
            print(f"  Parsed state: {_format_state(device_type, mode, parsed)}\n")
        else:
            print(f"  State query failed: error {result}\n")

    except Exception as exc:
        _LOGGER.error("Error: %s", exc)
        print(f"Error: {exc}\n")

    finally:
        if device:
            print("Disconnecting...")
            await device.disconnect()
            print("Disconnected\n")

    return learned


async def ewb_change_device_state(learned: LearnedEwbDevice) -> None:
    """Turn a learned switch on using encode_ewb_state."""
    if learned.device_type != DeviceType.EWB_DT_SWITCH:
        print(f"Skipping change-state demo for device type {learned.device_type.name}")
        return

    print("\n" + "=" * 80)
    print("RX11: Change Device State (encode_ewb_state)")
    print("=" * 80 + "\n")

    device: Optional[RX11Device] = None
    try:
        device = await RX11Device.create(port="/dev/ttyUSB0", timeout=5.0)

        desired = SwitchChangeCommand(action=SwitchDesiredAction.ON)
        raw_state = encode_ewb_state(
            learned.device_type,
            0,
            desired,
            direction=StateDirection.TO_DEVICE,
        )

        print(f"Sending ON command to {learned.receiver_serial.hex()}...")
        result, mode, response_state = await device.ewb_change_state_request(  # type: ignore[attr-defined]
            gateway=learned.gateway_serial,
            receiver=learned.receiver_serial,
            desired_mode=0,
            desired_state=raw_state,
            timeout=5.0,
        )

        if result != RX11ErrorCode.SUCCESS:
            print(f"Change state failed: error {result}")
            return

        parsed = parse_ewb_state(learned.device_type, mode, response_state)
        print(f"Device confirmed: {_format_state(learned.device_type, mode, parsed)}\n")

    finally:
        if device:
            await device.disconnect()


async def ewb_listen_state_changes(known_devices: list[LearnedEwbDevice]) -> None:
    """Listen for EWB telegrams and decode them with parse_ewb_rcv."""
    print("\n" + "=" * 80)
    print("RX11: EWB Listener (parse_ewb_rcv)")
    print("=" * 80 + "\n")

    lookup = {item.receiver_serial: item for item in known_devices}
    device: Optional[RX11Device] = None

    try:
        device = await RX11Device.create(port="/dev/ttyUSB0", timeout=5.0)
        print("Listening for EWB telegrams (Ctrl+C to stop)...\n")

        while True:
            result, info_type, serial, info_data = await device.ewb_rcv_request(timeout=None)  # type: ignore[attr-defined]
            if result != RX11ErrorCode.SUCCESS:
                print(f"Receive error: {result}")
                continue

            device_type = None
            if info_type == InfoType.TM_IT_EWBIDI_STATE:
                known = lookup.get(serial)
                device_type = known.device_type if known else DeviceType.EWB_DT_SWITCH

            event = parse_ewb_rcv(info_type, serial, info_data, device_type=device_type)
            _handle_ewb_event(event, lookup)

    except KeyboardInterrupt:
        print("\nListener stopped")

    finally:
        if device:
            await device.disconnect()


async def main() -> None:
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║          EASYWAVE BIDI + CODEC EXAMPLES                                    ║
║                                                                            ║
║ 1. Pair a neo receiver                                                     ║
║ 2. Query state with parse_ewb_state                                        ║
║ 3. Change state with encode_ewb_state                                      ║
║ 4. Listen with parse_ewb_rcv                                               ║
╚════════════════════════════════════════════════════════════════════════════╝
""")

    learned = await ewb_pair_and_learn_device()
    if learned:
        await ewb_change_device_state(learned)
        # Uncomment to run the listener after pairing:
        # await ewb_listen_state_changes([learned])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted.\n")
