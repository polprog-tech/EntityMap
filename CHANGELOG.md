# Changelog

All notable changes to EntityMap will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-06-16

### Added

- Graph export service `entitymap.export`, returning the full graph, fragility findings, and last-scan metadata as a response.
- Graph panel: node sizing by importance, search-match highlighting, focus mode (double-click a node to isolate its neighborhood), area and domain filters, path-finding between two nodes, an on-canvas minimap, zoom controls (in / out / fit / reset), PNG export, a "showing N of M nodes" notice for capped graphs, and a performance mode that simplifies very large graphs.
- Graph panel accessibility and theming: full keyboard navigation, a screen-reader live region, dark-mode polish, a colorblind-safe palette toggle, and a compact density toggle (both remembered).
- Curved routing for parallel edges and direction arrowheads.
- `Last scan` sensor attributes: `status`, `duration_seconds`, and `adapter_errors`.
- Summary sensors restore their last value across restarts.
- Test coverage for the automation, script, scene, and template adapters, plus the hierarchy builder, sensors, and graph builder.

### Changed

- Template entities that referenced other entities no longer appear unconnected: the template adapter now resolves references from each helper's own config entry.
- The first scan runs immediately when the integration is added while Home Assistant is already running (previously it waited for a start event that had already fired).
- Registry-change rescans are debounced so a burst of changes collapses into a single scan.
- Fragility findings are computed once per scan and reused by the sensors, panel, and repairs.
- The panel is served as a static module directory and split into ES-module mixins; its assets are sent with `Cache-Control: no-store` so updates apply without cache issues.
- Internal cleanup: WebSocket API moved to `websocket.py`, the hierarchy builder to `hierarchy.py`, shared adapter parsers to `adapters/_config_parse.py`.
- Shortened the summary-sensor display names (Nodes, Dependencies, Issues, Last scan).

### Fixed

- Detail drawer no longer stays open and empty when switching tabs or changing filters.
- Type filters now apply consistently in the Issues view and are hidden in the structural Hierarchy view.

## [1.0.1] - 2026-06-15

### Fixed

- Sidebar panel failing to open with "Unable to load custom panel" and repeated invalid authentication entries in the HTTP ban log. The view serving the panel JavaScript no longer requires authentication, so the browser can import it as a module ([#1](https://github.com/polprog-tech/EntityMap/issues/1)).

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
