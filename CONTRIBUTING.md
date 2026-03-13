# Contributing to EntityMap

Thank you for your interest in contributing! EntityMap is a community-driven project and welcomes contributions of all kinds.

## Development Setup

### Prerequisites

- Python 3.12+
- Home Assistant development environment (or a running HA instance for manual testing)
- Git

### Local Setup

```bash
# Clone the repository
git clone https://github.com/polprog-tech/EntityMap.git
cd EntityMap

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install development dependencies
pip install homeassistant voluptuous aiohttp pytest pytest-asyncio pytest-cov ruff mypy
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=custom_components/entitymap --cov-report=term-missing

# Run a specific test file
pytest tests/components/entitymap/test_models.py -v
```

### Linting & Formatting

```bash
# Check for lint errors
ruff check .

# Auto-fix lint errors
ruff check --fix .

# Format code
ruff format .

# Type checking
mypy custom_components/entitymap --ignore-missing-imports
```

## Project Structure

```
custom_components/entitymap/
├── __init__.py          # Integration setup, event wiring, WebSocket API
├── config_flow.py       # Config and options flow
├── const.py             # Constants, enums (NodeType, DependencyKind, etc.)
├── models.py            # Domain model (GraphNode, GraphEdge, DependencyGraph, etc.)
├── graph.py             # Graph builder orchestration
├── analysis.py          # Impact analysis engine
├── fragility.py         # Fragility detection engine
├── migration.py         # Migration suggestion engine
├── sensor.py            # Summary sensor entities
├── button.py            # Rescan button entity
├── services.py          # Service handlers
├── diagnostics.py       # Diagnostics support
├── repairs.py           # Repair flows
├── panel.py             # HTTP handler for frontend JS
├── adapters/
│   ├── base.py          # SourceAdapter abstract base class
│   ├── registry.py      # Entity/device/area registry adapter
│   ├── automation.py    # Automation config parser
│   ├── script.py        # Script config parser
│   ├── scene.py         # Scene config parser
│   ├── group.py         # Group state parser
│   └── template.py      # Template entity reference extractor
├── frontend/
│   └── entitymap-panel.js  # LitElement + D3.js frontend panel
├── manifest.json
├── services.yaml
├── strings.json
└── translations/
    └── en.json
```

## Architecture Guidelines

### Adding a New Graph Source (Adapter)

1. Create a new file in `adapters/` (e.g., `blueprint.py`)
2. Extend `SourceAdapter` from `adapters/base.py`
3. Implement `async_populate(self, graph: DependencyGraph) -> None`
4. Add the adapter to the `GraphBuilder._build()` method in `graph.py`
5. Add configuration option if the adapter is optional
6. Write tests in `tests/components/entitymap/`

```python
from .base import SourceAdapter

class BlueprintAdapter(SourceAdapter):
    async def async_populate(self, graph: DependencyGraph) -> None:
        # Your logic here
        pass
```

### Adding a New Finding Type

1. Add the type to `FragilityType` enum in `const.py`
2. Add a detection function in `fragility.py`
3. Call it from `detect_fragility()`
4. Add a translation key in `strings.json` if it generates repair issues
5. Write tests

### Key Principles

- **Prefer supported/public Home Assistant APIs** over internal implementation details
- **Isolate fragile access** behind adapters with clear compatibility notes
- **Separate "cannot determine" from "no dependency found"** — always track confidence levels
- **Keep entities thin** — they project backend state, don't contain business logic
- **Async-first** — never block the event loop
- **Test everything** — aim for 95%+ coverage on core logic

## Branching & PR Guidance

- **main** — stable release branch
- Feature branches: `feature/description`
- Bug fixes: `fix/description`
- PRs should include tests and pass all CI checks
- Keep commits atomic and well-described

## Commit Messages

Use conventional commits:

```
feat: add blueprint dependency scanning
fix: handle missing automation store gracefully
test: add tests for device_id fragility detection
docs: update architecture diagram
```

## Testing Philosophy

EntityMap uses **scenario-oriented Given/When/Then (GWT) style tests** for readability and maintainability.

### Structure

Every test follows a clear three-part structure:

1. **Given** — Set up preconditions (create a graph, add nodes/edges, configure mocks)
2. **When** — Perform the action under test (run a function, call a service, submit a flow)
3. **Then** — Assert the expected outcome (check return values, verify state changes)

### In Practice

- Test classes are organized by **feature/scenario**, not by module. For example, `TestImpactOnEntityWithDependents` rather than `TestAnalysis`.
- Test method names describe the scenario: `test_reports_high_severity_when_many_dependents`.
- Each test uses inline `# Given`, `# When`, `# Then` comments to mark sections.
- We include **happy-path**, **edge-case**, and **failure-path** scenarios for every feature.

### Example

```python
class TestImpactOnIsolatedNode:
    """Given a node with no dependents."""

    def test_reports_zero_risk(self):
        # Given — a graph with one isolated node
        graph = DependencyGraph()
        graph.add_node(GraphNode(node_id="light.solo", node_type=NodeType.ENTITY, title="Solo"))

        # When — impact is analyzed
        report = analyze_impact(graph, "light.solo")

        # Then — risk is zero, severity is info
        assert report.risk_score == 0.0
        assert report.severity == "info"
```

### Guidelines

- Prefer **many small test classes** (one scenario each) over large test classes with mixed scenarios.
- Use descriptive class docstrings that read as "Given ..." to set context.
- Aim for **95%+ coverage** on core logic (models, analysis, fragility, migration).
- Test both the happy path and meaningful edge cases (empty inputs, cycles, missing nodes).

---

## Avoiding Reliance on Unstable HA Internals

Home Assistant's internal APIs can change without notice. When accessing non-public APIs:

1. **Isolate** the access in a dedicated adapter method
2. **Wrap** in try/except with graceful fallback
3. **Document** which HA version the API was tested against
4. **Log** a clear warning if the API shape changes
5. **Test** the fallback path
