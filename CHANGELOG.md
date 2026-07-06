# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
