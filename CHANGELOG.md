# Changelog

All notable changes to EntityMap will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-03-13

### Added

- Initial release of EntityMap
- Full dependency graph generation from HA registries, automations, scripts, scenes, groups, helpers, and template entities
- Interactive force-directed graph visualization panel with D3.js
- Node type filtering, search, zoom/pan, and neighborhood highlighting
- Impact analysis engine with risk scoring and severity classification
- Fragility detection for missing references, device_id usage, disabled/unavailable entities, tight coupling, and hidden dependencies
- Migration guidance with step-by-step recommendations for device/entity replacement
- Summary sensors: total nodes, total dependencies, fragility issues, last scan timestamp
- Rescan button entity
- Services: `entitymap.scan`, `entitymap.analyze_impact`, `entitymap.get_dependencies`
- WebSocket API for frontend: `entitymap/graph`, `entitymap/impact`, `entitymap/neighborhood`, `entitymap/scan`, `entitymap/findings`, `entitymap/migration`
- Repair issues for fragile device_id usage and missing entity references
- Diagnostics support with redacted output
- Config flow with options for scan-on-startup, auto-refresh, scan interval, template/group inclusion
- Options flow for runtime configuration changes
- Full test suite with pytest
- CI workflow with linting (ruff), type checking (mypy), testing, and HACS validation
- Comprehensive documentation: README, architecture, dependency model, contributing guide
