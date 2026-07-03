#!/usr/bin/env python3
"""Example: Secwave transmitter/receiver workflow with the codec layer.

Demonstrates:
1. Listen for Secwave telegrams (SEC_RCV + parse_sec_rcv_result)
2. Learn a transmitter (SEC_LEARN + parse_sec_learn_result)
3. Query storage entries (SEC_STAT)
4. Send commands (encode_sec_send_cmd_tel_params)
5. Reply to bidirectional queries (encode_sec_reply_query_params)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from easywave_home_control import RX11Device, RX11ErrorCode, secwave

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
_LOGGER = logging.getLogger(__name__)


def _print_telegram(telegram: secwave.SecCommandTelegram) -> None:
    cmd = telegram.fixed_command
    cmd_label = cmd.name if cmd else f"flexible (0x{telegram.command:04X})"
    print(f"  Storage index: {telegram.storage_index}")
    print(f"  Command:       {cmd_label}")
    print(f"  User data:     0x{telegram.user_data:08X}")
    print(f"  Flags:         mobile={telegram.flags.mobile}, low_bat={telegram.flags.low_battery}")
    print(f"  Query:         reply={telegram.query.wants_reply}, reply_only={telegram.query.reply_only}")
    print(f"  Learn kind:    {telegram.learn_kind}")


async def secwave_listen() -> None:
    """Listen for Secwave telegrams and decode them."""
    print("\n" + "=" * 80)
    print("RX11: Secwave Listener (parse_sec_rcv_result)")
    print("=" * 80 + "\n")

    device: Optional[RX11Device] = None
    try:
        device = await RX11Device.create(port="/dev/ttyUSB0", timeout=5.0)
        print("Listening for Secwave telegrams (Ctrl+C to stop)...\n")

        while True:
            raw = await device.sec_rcv_request(timeout=None)
            error_code, telegram = secwave.parse_sec_rcv_result(raw)
            if error_code != RX11ErrorCode.SUCCESS or telegram is None:
                print(f"Receive error: {error_code}")
                continue

            print("Secwave telegram received:")
            _print_telegram(telegram)

            if telegram.query.wants_reply and not telegram.query.reply_only:
                reply = secwave.SecwaveReplyState(
                    primary=secwave.SecwavePrimaryState(
                        position=secwave.SecwavePosition.END_CLOSED,
                        opening=False,
                        movement=secwave.SecwaveMovement.STOPPED,
                        vacation_mode_off=True,
                    )
                )
                primary, secondary = secwave.encode_reply_state(reply)
                print(f"  Sending reply: primary=0x{primary:04X}, secondary=0x{secondary:04X}")
                result = await device.sec_reply_query_request(primary, secondary, timeout=5.0)
                if result != RX11ErrorCode.SUCCESS:
                    print(f"  Reply failed: {result}")
            print()

    except KeyboardInterrupt:
        print("\nListener stopped")

    finally:
        if device:
            await device.disconnect()


async def secwave_learn_and_query() -> None:
    """Learn a transmitter and inspect storage via codec."""
    print("\n" + "=" * 80)
    print("RX11: Secwave Learn + Storage Query")
    print("=" * 80 + "\n")

    device: Optional[RX11Device] = None
    try:
        device = await RX11Device.create(port="/dev/ttyUSB0", timeout=5.0)

        user_data = 0x00000001
        print(f"Starting learn mode (user_data=0x{user_data:08X})...")
        print(">> Press learn button on Secwave transmitter <<\n")

        raw = await device.sec_learn_request(user_data=user_data, timeout=30.0)
        error_code, telegram = secwave.parse_sec_learn_result(raw)
        if error_code != RX11ErrorCode.SUCCESS or telegram is None:
            print(f"Learn failed: error {error_code}")
            return

        print("Learn result:")
        _print_telegram(telegram)

        if telegram.learn_kind == secwave.SecLearnTelegramKind.NEW_LEARN_IN_PROGRESS:
            index = telegram.storage_index
            stat_raw = await device.sec_stat_request(stor_index=index, timeout=5.0)
            _, entry = secwave.parse_sec_stat_result_with_index(index, stat_raw)
            if entry:
                print(
                    f"\nStorage slot {entry.storage_index}: "
                    f"used={entry.is_used}, user_data=0x{entry.user_data:08X}"
                )

    finally:
        if device:
            await device.disconnect()


async def secwave_send_command() -> None:
    """Send a Secwave command telegram using encoded IRP params."""
    print("\n" + "=" * 80)
    print("RX11: Secwave Send Command (encode_sec_send_cmd_tel_params)")
    print("=" * 80 + "\n")

    device: Optional[RX11Device] = None
    try:
        device = await RX11Device.create(port="/dev/ttyUSB0", timeout=5.0)

        request = secwave.SecSendCmdTelRequest(
            button_number=0,
            query=secwave.SecQuery(wants_reply=True, reply_only=False),
            command=int(secwave.SecwaveCommand.OPEN),
            flags=secwave.SecTransmitterFlags(low_battery=False, mobile=False),
        )
        params = secwave.encode_sec_send_cmd_tel_params(request)
        print(f"Encoded SEC_SEND_CMD_TEL params: {params.hex()}\n")

        result, primary, secondary = await device.sec_send_cmd_tel_request(params, timeout=5.0)
        if result != RX11ErrorCode.SUCCESS:
            print(f"Send failed: {result}")
            return

        response = secwave.parse_sec_send_response(
            primary, secondary, queried_reply=request.query.wants_reply
        )
        if response.reply:
            print(f"Receiver reply: position={response.reply.primary.position}")
        else:
            print("No reply from receiver (or query bit was clear)")

    finally:
        if device:
            await device.disconnect()


async def main() -> None:
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║          SECWAVE CODEC EXAMPLES                                            ║
║                                                                            ║
║ Listen, learn, query storage, send commands, and encode replies            ║
╚════════════════════════════════════════════════════════════════════════════╝
""")

    await secwave_listen()
    # await secwave_learn_and_query()
    # await secwave_send_command()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted.\n")
