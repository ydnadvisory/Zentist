# Zentist RPA

Python RPA foundation for the Zentist Part 1 design. The project is structured to keep shared orchestration, connectors, resilience, and portal-specific automation boundaries separate while staying small enough for the take-home scope.

## Tooling

- Python 3.11+
- `uv` for dependency and environment management
- Playwright for browser automation
- Pytest with coverage for tests
- Ruff for linting and formatting
- Ty for type checking

## Local Setup

```bash
uv sync --all-groups
uv run playwright install
```

Copy `.env.example` to `.env` for local runs and set the recipient placeholder:

```bash
ZENTIST_RPA_REPORT_RECIPIENT=ops@example.com
```

Do not put real portal credentials, tokens, salary data, or sensitive screenshots in committed files.

## Useful Commands

```bash
uv run zentist-rpa structure
uv run zentist-rpa check-config
uv run ruff format --check .
uv run ruff check .
uv run ty check src
uv run pytest
uv build
```

The `check-config` command validates runtime configuration before any browser side effects.

## Project Layout

```text
src/zentist_rpa/
  core/                 runner contracts, run context, outcomes, exceptions
  connectors/           settings, secrets, SQLite persistence, reports, email
  resilience/           bounded retry and timeout helpers
  portals/orangehrm/    OrangeHRM page objects and workflow code
  portals/saucedemo/    Sauce Demo page objects and workflow code
  cli.py                command entrypoint
tests/                  focused tests for shared behavior
```

## Adding A Portal

1. Create a new package under `src/zentist_rpa/portals/<portal_name>/`.
2. Implement a runner that satisfies `zentist_rpa.core.runner.PortalRunner`.
3. Keep page objects and selectors inside the portal package.
4. Persist per-item outcomes through `SQLiteResultStore` or another `ResultStore` implementation.
5. Add tests for validation, per-item outcome classification, idempotency, and runner orchestration.

Existing portal packages should not need edits when another portal is added.
