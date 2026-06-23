# Changelog

## [0.1.0] - 2026-06-20

### Added
- Initial MQTT connector: `mqtt://broker/topic/command/publish` and
  `device://device-01/led/command/set`, built on the urirun connector SDK.
- Dry-run default (returns the publish plan); `dry_run=false` publishes via the
  optional `paho-mqtt` dependency.
- CLI, connector manifest, pytest suite (paho mocked), smoke target, CI and the
  `urirun.bindings` entry point.
