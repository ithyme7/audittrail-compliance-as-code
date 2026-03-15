# CONTRIBUTING.md - AuditTrail

Thanks for contributing to AuditTrail. This guide describes the expected workflow and quality checks for changes.

## 1. Scope
This repo focuses on the Python SDK, demos, and compliance reporting artifacts.

## 2. Development Setup

- Use Python 3.9 through 3.12 to match CI.
- From the SDK root (`/audittrail/sdk-python`), install in editable mode with test and demo extras:
  - `pip install -e ".[test,demo]"`
- Run tests:
  - `pytest -v`

## 3. Running Demos
From `/audittrail/demo/` you can run:

- `python fraud_detection_demo.py`
- `python dashboard.py`
- `python benchmark.py`
- `python pdf_exporter.py`

## 4. Change Guidelines

- Keep the SDK API stable where possible.
- If you add log fields, ensure they are included in reporting and demo outputs.
- Preserve hash-chain integrity and async logging behavior.
- Ensure fairness metrics remain consistent and documented.

## 5. Pull Request Checklist

- Tests pass locally.
- CI-compatible Python versions verified.
- Documentation updated if public behavior changes.
- Demo scripts still run if affected.

For a full architectural overview and engineering rules, see `AGENTS.md`.
