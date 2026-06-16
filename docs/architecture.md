# EntityMap Architecture

## Design Goals

1. **Trustworthy analysis** - users should be able to rely on EntityMap's dependency and impact reports
2. **Minimal footprint** - avoid entity bloat, excessive logging, or recorder churn
3. **Maintainability** - clean module boundaries, typed models, testable adapters
4. **Extensibility** - adding new sources or finding types should be straightforward
5. **Native feel** - integrate naturally with Home Assistant's UI patterns

## Hybrid Event-Driven + On-Demand

EntityMap does **not** use `DataUpdateCoordinator`. Here's why:

| Approach | Pros | Cons | Verdict |
|---|---|---|---|
| DataUpdateCoordinator | Familiar HA pattern, automatic retry | Designed for polling external APIs; unnecessary overhead for local computation | ❌ Not appropriate |
| Pure event-driven | Responsive, no wasted computation | May miss changes not covered by events; complex to ensure completeness | ⚠️ Partial fit |
| Pure on-demand | User controls when scans run | Graph can be stale; poor UX for dashboard | ⚠️ Partial fit |
| **Hybrid** | Responsive + reliable + user-controllable | Slightly more complex setup | ✅ **Chosen** |

### How It Works

1. **Startup scan**: Runs immediately when Home Assistant is already running (e.g. the integration is added at runtime), otherwise on `EVENT_HOMEASSISTANT_STARTED` - via `homeassistant.helpers.start.async_at_started`
2. **Event-driven refresh**: Listens to `entity_registry_updated` and `device_registry_updated`; rebuilds are debounced so a burst of changes collapses into a single scan
3. **Periodic reconciliation**: Timer-based full rescan at configurable intervals (default: 6 hours)
4. **Manual rescan**: Button entity or `entitymap.scan` service

Each scan computes fragility findings once and caches them on the builder (reused by the sensors, panel, and repairs), and records the scan's status, duration, and adapter-error count (exposed as attributes on the **Last scan** sensor).

## Graph Model

```
DependencyGraph
├── nodes: dict[str, GraphNode]     # Keyed by node_id
├── edges: list[GraphEdge]          # All directed edges
├── _inbound: dict[str, list[Edge]] # Index: target → edges
└── _outbound: dict[str, list[Edge]]# Index: source → edges
```

### Node Identity

- Devices: `device.{device_id}`
- Entities: `{domain}.{object_id}` (the entity_id)
- Areas: `area.{area_id}`

### Edge Direction

Edges point from **dependent → dependency**:
- `automation.motion_light → light.living_room` means the automation depends on the light
- `light.living_room → device.abc123` means the entity belongs to the device

## Source Adapters

Each adapter implements `SourceAdapter.async_populate(graph)`:

```
RegistryAdapter     - devices, entities, areas (always runs first)
AutomationAdapter   - automation triggers, conditions, actions
ScriptAdapter       - script sequences and service calls
SceneAdapter        - scene entity membership
GroupAdapter        - group member entities
TemplateAdapter     - template entity Jinja2 references
```

Adapters run sequentially. `RegistryAdapter` must run first to establish base nodes; others add edges and placeholder nodes for missing references. The automation and script adapters share parsing helpers (`adapters/_config_parse.py`: list coercion, entity-id extraction, template-reference scanning, nested-action iteration). The WebSocket API lives in `websocket.py` and the area → device → entity tree builder in `hierarchy.py`.

## Fragility Analysis

The fragility engine runs synchronously on the in-memory graph. It detects patterns by iterating edges and comparing against node metadata:

- **Missing references**: Edge target doesn't exist in nodes
- **Device ID references**: Edge kind is `DEVICE_TRIGGER/CONDITION/ACTION`
- **Disabled/unavailable**: Target node is disabled or unavailable
- **Tight coupling**: Same automation has 3+ device_id refs to one device
- **Hidden dependencies**: Automation calls a script with 3+ sub-dependencies

Each finding gets a deterministic ID (MD5 hash of key fields) for stable tracking.

## Impact Analysis

Impact analysis combines:
1. **Direct dependents** - one-hop inbound edges
2. **Transitive dependents** - full BFS traversal of inbound graph
3. **Risk scoring** - weighted formula based on dependent count, type, and edge fragility
4. **Migration suggestions** - pattern-matched recommendations based on edge types

## Frontend

The panel is a native Web Component (`HTMLElement` + Shadow DOM), served as a **static ES-module directory** - `panel.py` registers `/entitymap_frontend/` via `StaticPathConfig`, and the sidebar panel's `module_url` points at `entitymap-panel.js`. The code is split into focused modules composed as mixins:

- `entitymap-panel.js` - core element: lifecycle, data loading, render/event wiring
- `layout.js` - shell markup, filter chips, legend
- `graph-view.js` / `graph-render.js` / `graph-interactions.js` - graph orchestration, D3 drawing primitives, and interactions (focus, path, scope filter, export, banner)
- `hierarchy-view.js` / `hierarchy-tree.js` - hierarchy list and D3 tree
- `findings-view.js`, `detail-view.js` - issues grid and detail drawer
- `constants.js` (config + palettes), `graph-data.js` (pure helpers: degree, domain, shortest path), `styles.js` (CSS)

Capabilities: D3 force layout, SVG rendering, node size by degree, curved parallel edges, type/area/domain filters, search highlighting, focus (neighborhood isolation) and shortest-path highlighting, minimap, zoom controls, PNG export, dark mode, a colorblind-safe palette, a compact density mode, keyboard navigation, and a screen-reader live region. Tunable layout values live in `constants.js` (`GRAPH`). D3.js is loaded from CDN on first panel load to keep the integration package small.

## Resource Usage

- **Memory**: Graph is stored in-memory; typical HA installation uses <10MB
- **CPU**: Full scan is async and completes in <2s for most installations
- **Storage**: No persistent storage beyond the config entry
- **Recorder**: Summary sensors update only on graph changes (not continuously)
- **Network**: Zero external network calls
