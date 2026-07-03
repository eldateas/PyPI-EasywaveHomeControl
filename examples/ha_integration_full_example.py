#!/usr/bin/env python3
"""Example: Home Assistant integration pattern with the EWB codec layer.

Demonstrates how a HA DataUpdateCoordinator would use this library:
- Persist known neo receivers in config (simulated here)
- Restore state on startup via ewb_query_state_request + parse_ewb_state
- Background EWB_RCV loop with parse_ewb_rcv
- Entity actions via encode_ewb_state + ewb_change_state_request
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

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
)
from easywave_home_control.codec.events import ButtonPushEvent, EwbRcvEvent, EwbStateChangeEvent
from easywave_home_control.protocols.rx11_rx2x.protocol import DeviceType, InfoType

_LOGGER = logging.getLogger(__name__)


@dataclass
class EwbDeviceConfig:
    """Serializable device entry (maps to HA config_entry / Store)."""

    name: str
    gateway_serial: str
    receiver_serial: str
    device_type: int


@dataclass
class EwbDeviceRuntime:
    """In-memory device state managed by the coordinator."""

    config: EwbDeviceConfig
    last_mode: int = 0
    last_state_hex: str = "00000000"
    parsed_state: Any = None
    available: bool = True


@dataclass
class EasywaveCoordinator:
    """Minimal coordinator showing HA integration patterns with the codec."""

    port: str
    devices: list[EwbDeviceConfig]
    device: Optional[RX11Device] = None
    runtime: dict[str, EwbDeviceRuntime] = field(default_factory=dict)
    event_callback: Optional[Callable[[EwbRcvEvent, EwbDeviceRuntime | None], None]] = None
    _listening: bool = False
    _listen_task: Optional[asyncio.Task[None]] = None

    def __post_init__(self) -> None:
        for entry in self.devices:
            self.runtime[entry.receiver_serial] = EwbDeviceRuntime(config=entry)

    async def async_setup(self) -> bool:
        try:
            self.device = await RX11Device.create(port=self.port, timeout=10.0)
            await self.async_restore_states()
            return True
        except Exception as exc:
            _LOGGER.error("Setup failed: %s", exc)
            return False

    async def async_restore_states(self) -> None:
        """Query all known devices after HA restart (coordinator _async_update_data pattern)."""
        if not self.device:
            return

        for entry in self.devices:
            runtime = self.runtime[entry.receiver_serial]
            gateway = bytes.fromhex(entry.gateway_serial)
            receiver = bytes.fromhex(entry.receiver_serial)

            result, mode, raw = await self.device.ewb_query_state_request(  # type: ignore[attr-defined]
                gateway=gateway,
                receiver=receiver,
                desired_mode=0,
                timeout=5.0,
            )

            if result == RX11ErrorCode.SUCCESS:
                runtime.last_mode = mode
                runtime.last_state_hex = raw.hex()
                runtime.parsed_state = parse_ewb_state(entry.device_type, mode, raw)
                runtime.available = True
                _LOGGER.info("Restored %s: %s", entry.name, runtime.parsed_state)
            else:
                runtime.available = False
                if runtime.last_state_hex != "00000000":
                    raw = bytes.fromhex(runtime.last_state_hex)
                    runtime.parsed_state = parse_ewb_state(
                        entry.device_type, runtime.last_mode, raw
                    )
                _LOGGER.warning("Restore failed for %s, keeping cached state", entry.name)

    async def async_turn_on(self, receiver_serial: str) -> None:
        """Entity turn_on → encode + ewb_change_state_request."""
        if not self.device:
            return

        runtime = self.runtime[receiver_serial]
        entry = runtime.config
        if entry.device_type != DeviceType.EWB_DT_SWITCH:
            _LOGGER.warning("turn_on demo only implemented for switches")
            return

        raw = encode_ewb_state(
            entry.device_type,
            0,
            SwitchChangeCommand(action=SwitchDesiredAction.ON),
            direction=StateDirection.TO_DEVICE,
        )

        result, mode, response = await self.device.ewb_change_state_request(  # type: ignore[attr-defined]
            gateway=bytes.fromhex(entry.gateway_serial),
            receiver=bytes.fromhex(entry.receiver_serial),
            desired_mode=0,
            desired_state=raw,
            timeout=5.0,
        )

        if result == RX11ErrorCode.SUCCESS:
            runtime.last_mode = mode
            runtime.last_state_hex = response.hex()
            runtime.parsed_state = parse_ewb_state(entry.device_type, mode, response)
            runtime.available = True

    async def start_listening(self) -> None:
        if self._listening or not self.device:
            return
        self._listening = True
        self._listen_task = asyncio.create_task(self._listen_loop())

    async def stop_listening(self) -> None:
        self._listening = False
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None

    async def async_shutdown(self) -> None:
        await self.stop_listening()
        if self.device:
            await self.device.disconnect()
            self.device = None

    async def _listen_loop(self) -> None:
        assert self.device is not None
        receiver_lookup = {
            bytes.fromhex(entry.receiver_serial): self.runtime[entry.receiver_serial]
            for entry in self.devices
        }

        while self._listening:
            try:
                result, info_type, serial, info_data = await self.device.ewb_rcv_request(timeout=None)  # type: ignore[attr-defined]
                if result != RX11ErrorCode.SUCCESS:
                    continue

                runtime = receiver_lookup.get(serial)
                device_type = runtime.config.device_type if runtime else None
                if info_type == InfoType.TM_IT_EWBIDI_STATE and device_type is None:
                    device_type = DeviceType.EWB_DT_SWITCH

                event = parse_ewb_rcv(info_type, serial, info_data, device_type=device_type)

                if isinstance(event, EwbStateChangeEvent) and runtime:
                    runtime.last_mode = event.mode
                    runtime.last_state_hex = info_data[1:5].hex()
                    runtime.parsed_state = event.state
                    runtime.available = True

                if self.event_callback:
                    self.event_callback(event, runtime)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                _LOGGER.error("Listen loop error: %s", exc)
                await asyncio.sleep(5)


def _on_coordinator_event(event: EwbRcvEvent, runtime: EwbDeviceRuntime | None) -> None:
    if isinstance(event, ButtonPushEvent):
        _LOGGER.info("Button %s from %s", event.button.name, event.transmitter_serial.hex())
        return

    if isinstance(event, EwbStateChangeEvent):
        name = runtime.config.name if runtime else event.receiver_serial.hex()
        _LOGGER.info("State update for %s: %s", name, event.state)
        return

    _LOGGER.info("EWB event: %s", type(event).__name__)


async def example_coordinator_lifecycle() -> None:
    """Simulates HA setup → restore → listen → entity action → shutdown."""
    print("\n" + "=" * 80)
    print("Home Assistant Pattern: EasywaveCoordinator + Codec")
    print("=" * 80 + "\n")

    # Simulated config_entry.data — in HA this comes from persistent storage
    config = [
        EwbDeviceConfig(
            name="Living Room Switch",
            gateway_serial="0123456789abcdef0123456789abcdef",
            receiver_serial="fedcba9876543210fedcba9876543210",
            device_type=int(DeviceType.EWB_DT_SWITCH),
        ),
    ]

    coordinator = EasywaveCoordinator(
        port="/dev/ttyUSB0",
        devices=config,
        event_callback=_on_coordinator_event,
    )

    if not await coordinator.async_setup():
        print("Could not connect to RX11 (expected without hardware)")
        print("\nCoordinator pattern code is ready for HA — replace serials with real values.")
        return

    await coordinator.start_listening()
    print("Coordinator listening (30 seconds)...")
    print("Toggle a neo device or press a transmitter button.\n")

    try:
        await asyncio.sleep(5)
        await coordinator.async_turn_on(config[0].receiver_serial)
        await asyncio.sleep(25)
    finally:
        await coordinator.async_shutdown()
        print("Coordinator shut down")


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║      HOME ASSISTANT + CODEC EXAMPLE                                        ║
║                                                                            ║
║ - Restore: parse_ewb_state after ewb_query_state_request                   ║
║ - Listen:  parse_ewb_rcv in EWB_RCV loop                                   ║
║ - Control: encode_ewb_state before ewb_change_state_request                ║
╚════════════════════════════════════════════════════════════════════════════╝
""")

    await example_coordinator_lifecycle()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted.\n")
