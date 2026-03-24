# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
