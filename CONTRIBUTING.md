# Contributing to EntityMap

Thank you for your interest in contributing to EntityMap! This guide covers everything you need to get started.

## Development Setup

```bash
git clone https://github.com/polprog-tech/EntityMap.git
cd EntityMap

python3 -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

pip install -r requirements_test.txt
pip install ruff mypy homeassistant
```

### Pre-commit hook

```bash
cp scripts/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
```

The hook runs `ruff check --fix`, `ruff format --check`, and the full test suite on every commit.

## Running Tests

```bash
pytest                                                  # all tests
pytest -v                                               # verbose
pytest tests/components/entitymap/test_models.py        # specific file
pytest tests/components/entitymap/test_models.py::TestGraphNodeCreation  # specific class
pytest --cov=custom_components/entitymap                # with coverage
```

Tests follow the **GIVEN/WHEN/THEN** docstring convention (see existing tests for examples).

## Code Quality

```bash
ruff check .
ruff format --check .
mypy custom_components/entitymap --ignore-missing-imports
```

## How to Contribute

### Reporting Bugs

Include: expected vs actual behavior, Home Assistant version, Python version, EntityMap version, steps to reproduce, and a redacted diagnostics download if relevant.

### Pull Requests

1. Branch from `main` (`feature/...` or `fix/...`)
2. Make changes + add tests
3. Run `pytest` and `ruff check .`
4. Open a PR with a clear description

## Architecture Guidelines

### Adding a New Graph Source (Adapter)

1. Create a new file in `custom_components/entitymap/adapters/` (e.g., `blueprint.py`)
2. Extend `SourceAdapter` from `adapters/base.py`
3. Implement `async_populate(self, graph: DependencyGraph) -> None`
4. Wire the adapter into `GraphBuilder._build()` in `graph.py`
5. Add a configuration option if the adapter is optional
6. Write tests in `tests/components/entitymap/`

### Adding a New Finding Type

1. Add the type to `FragilityType` in `const.py`
2. Add a detection function in `fragility.py`
3. Call it from `detect_fragility()`
4. Add a translation key in `strings.json` if it generates repair issues
5. Write tests

### Key Principles

- **Prefer supported/public Home Assistant APIs** over internal implementation details
- **Isolate fragile access** behind adapters with clear compatibility notes
- **Separate "cannot determine" from "no dependency found"** - always track confidence levels
- **Keep entities thin** - they project backend state, they do not contain business logic
- **Async-first** - never block the event loop
- **Test everything** - aim for 95%+ coverage on core logic

## Commit Convention

[Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.

## License

See [LICENSE](LICENSE).
