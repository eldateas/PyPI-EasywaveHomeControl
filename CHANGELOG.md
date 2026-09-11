# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1] - 2026-09-11

### Fixed
- **Sensor payloads (Table 6 only)** — `EWB_RCV` / `EW_RCV_EX` `info_type` 0x02 uses RX
  Spec Table 6 for **all** RxModule gateways (RX11/RX21/RX22/RX25):
  - wire type **4 = temperature**, **5 = humidity**
  - temperature: `T = n/20` Kelvin → `temperature_celsius = n/20 − 273.15`
  - humidity: `φ = 100 · n / 4095` % (rounded to **1 decimal** place)
- Removes the incorrect NEO `/100` centi-unit path (and swapped type codes). Verified
  against live EasywavePlus `SENSOR_DATA` telegrams (e.g. raw `5947` → `24.20 °C`,
  raw `2609` → `63.7 %`). Ported from 0.3.4/0.3.5 onto the 0.4.x (serialx) line.

### Added
- `SensorPayloadFormat.TABLE6`; `NEO` / `LEGACY_RX21` remain as deprecated aliases
  (same Table 6 behavior).
- `SensorMeasurementPayload.temperature_kelvin`.

## [0.4.0] - 2026-09-03

### Changed
- **Event-loop-safe serial I/O (HA `async-dependency`)** — replaced blocking
  `pyserial` (`serial.Serial` open/read/write/`in_waiting` on an asyncio Task)
  with [serialx](https://github.com/puddly/serialx) native async APIs
  (`async_serial_for_url`). The RX/TX handler awaits `read()`/`write()` and no
  longer busy-polls the serial port on the Home Assistant event loop.
- **USB discovery** — uses `serialx` port listing (`async_list_serial_ports` /
  `list_serial_ports`); brief sync port probes run only in an executor.
- Dependency: `pyserial` → **`serialx>=1.2.2`**.

### Added
- `easywave_home_control.serial_io` — shared serialx helpers and exception types.
- Unit tests proving connect/read/write/close stay non-blocking and never call
  sync `serial_for_url` on the protocol path (`tests/protocol/test_async_serial_io.py`).

## [0.3.1] - 2026-08-03

### Fixed
- **Dual/quad motor summary (mode 0)** — the shared 7-bit channel field carries either a
  current position (`0–100`) or an activity code (`≥117`). Parsing previously treated every
  value as `activity`, so idle position reports were lost. `MotorSummaryChannelState` now
  exposes optional `position`; values `0–100` set `position` and `activity=STOPPED`.

### Changed
- Encoding `MultiMotorSummaryState` prefers `position` when set (`≤100`), otherwise writes
  `activity` into the same field.

## [0.3.0] - 2026-07-08

### Added
- **`RxModuleGateway`** (`EasywaveGateway` alias) — universal gateway for RX11/RX21/RX22/RX25 with connection lifecycle.
- **`Rx09Gateway`** — ASCII Easywave Basic gateway (prepared; `gateway.ew` only).
- **`EntityKind`** — explicit device categories (`easywave_transmitter`, `easywave_receiver`, `easywave_neo_*`, `secwave_transmitter`, `secwave_receiver`).
- **`TransceiverProfile`** registry — protocols, EWB device types, USB IDs; `register_transceiver_profile()` for successors.
- **`create_gateway()`** factory — picks RxModule vs RX09 gateway from profile.
- **Protocol facades** — `gateway.ew`, `gateway.ewb`, `gateway.sec` with capability checks.

### Changed
- **`GatewayConfig.transceiver_id`** replaces the former `device_type` field (no migration shim).
- **`supports_entity_kind()`** accepts `EntityKind` only — legacy string aliases removed.

## [0.2.1] - 2026-07-06

### Fixed
- **EWneo sensor payloads (STH01)** — corrected measurement type mapping (wire type 4 = humidity, 5 = temperature) and value scaling (`/100` centi-units instead of `/10`).

### Added
- `SensorPayloadFormat` — `NEO` (default) vs. `LEGACY_RX21` (Table 6: type 4 = temperature, 5 = humidity, `/10`).
- `BatteryLevel`, `wire_measurement_type`, `should_ignore`, reference-value helpers, and learn-capability properties on sensor payloads.
- Unit tests for STH01 measurement bytes, learn capabilities, legacy format, and edge flags (`tests/codec/test_sensors.py`).

## [0.1.2] - 2026-07-03

### Changed
- `query_hw_version()` now returns `tuple[int, str]` instead of `tuple[int, bytes]`.
  The null-terminator scan, ASCII decode, and `.strip()` are handled inside the
  library; callers receive a ready-to-use version string (empty string on failure).
- `query_fw_version()` now returns `tuple[int, str]` instead of
  `tuple[int, int, int, bool]`. The version is formatted as `"major.minor"` with
  `" (incomplete)"` appended when the firmware image is incomplete. Callers no
  longer need to format the version string themselves.

## [0.1.1] - 2026-03-24

### Changed
- Simplified public API: removed `BaseProtocol`, `RX09Protocol` and `ErrorCode` alias from top-level exports
- Replaced `RX11Device.ErrorCode` / `RX09Device.ErrorCode` with dedicated `RX11ErrorCode` / `RX09ErrorCode` exports for cleaner import ergonomics
- Fixed `__version__` (was incorrectly set to `3.0.0-async`)
- Updated README and examples to reflect new import style

## [0.1.0] - 2026-03-20

### Added
- Initial release of easywave-home-control library
- Pure Python implementation of RxModule protocol for EASYWAVE RX11 transceivers
- Full packet encoding/decoding with byte stuffing
- Request/response handling with proper synchronization
- Hardware and firmware version queries
- Health monitoring and automatic error recovery
- Connection state tracking and callbacks
- Comprehensive error handling
- Support for thread-safe serial communication
- Full documentation and examples
- Apache 2.0 license

### Features
- RxModule class for device communication
- Async-compatible threading design
- Health checks and connection monitoring
- Disconnect callbacks for state changes
- Support for multiple function codes (version queries, ping, etc.)
- Error codes and comprehensive error reporting
- Platform-independent (Windows, Linux, macOS)
- Python 3.9+ support
