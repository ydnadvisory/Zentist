schema-ref: zentist-r7

<div align="center">

# Zentist RPA

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/Status-In_Development-FFA500)
![Type Checker](https://img.shields.io/badge/Type--Check-Enabled-4A90E2)
![Tests](https://img.shields.io/badge/Tests-Pytest-0A9EDC)

A **portal-agnostic** Python RPA foundation for the Zentist Part 1 scope, with shared runner contracts, connectors, persistence, reporting, and resilient automation flows.

[Portal A (OrangeHRM)](#running-orangehrm) · [Contributing](#adding-a-portal) · [Project Layout](#project-layout)

</div>

The current focus is Portal A, **OrangeHRM**. Sauce Demo remains as a second portal shape, so shared code should stay portal-neutral.

## Tooling

- Python 3.11+
- `uv` for dependencies and local environments
- Playwright for browser automation
- Pytest with coverage
- Ruff for linting and formatting
- Ty for type checking

## Local Setup

Install dependencies and browser binaries:

```bash
uv sync --all-groups
uv run playwright install
```

Copy `.env.example` to `.env`, then set local values:

```bash
ZENTIST_RPA_REPORT_RECIPIENT=ops@example.com
ZENTIST_RPA_ORANGEHRM_USERNAME_SECRET=<orangehrm-username>
ZENTIST_RPA_ORANGEHRM_PASSWORD_SECRET=<orangehrm-password>
```

Do not commit real portal credentials, tokens, salary data, sensitive screenshots, or generated secrets.

## Useful Commands

```bash
uv run zentist-rpa structure
uv run zentist-rpa check-config
uv run zentist-rpa run --portal orangehrm --employee-json employees.json
uv run zentist-rpa run --portal orangehrm --employee-json employees.json --headed
uv run ruff format --check .
uv run ruff check .
uv run ty check src
uv run pytest
uv build
```

`check-config` validates required runtime settings before any browser side effects happen.

## Running OrangeHRM

Create a local employee input file outside version control:

```json
[
  {
    "employee_key": "emp001",
    "first_name": "Jane",
    "last_name": "Smith",
    "job_title": "Account Assistant",
    "employment_status": "Full-Time Permanent",
    "annual_salary": "90000"
  }
]
```

Run Portal A headlessly:

```bash
uv run zentist-rpa run --portal orangehrm --employee-json employees.json
```

Use `--headed` when you need to watch the browser:

```bash
uv run zentist-rpa run --portal orangehrm --employee-json employees.json --headed
```

Each run creates a run id, persists outcomes to `ZENTIST_RPA_DATABASE_PATH`, writes a summary report under `ZENTIST_RPA_REPORT_OUTPUT_DIR`, and writes the local email message under `ZENTIST_RPA_EMAIL_OUTPUT_DIR`.

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

1. Create `src/zentist_rpa/portals/<portal_name>/`.
2. Implement a runner that satisfies `zentist_rpa.core.runner.PortalRunner`.
3. Keep selectors, page objects, and portal workflow inside that package.
4. Persist per-item outcomes through `SQLiteResultStore` or another `ResultStore` implementation.
5. Add focused tests for input validation, outcome classification, idempotency, and runner orchestration.

Adding a portal should not require edits to existing portal runners.
