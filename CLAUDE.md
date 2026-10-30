# Claude Code Instructions

Read `CLAUDE_HANDOFF.md` before making changes. It records the current vocabulary-learning workstream, branch sequence, and known limits.

## Task ownership

Read `CLAUDE_HANDOFF.md` for the current stage and assigned task.
- Claude Code owns implementation changes: application code, tests, and code-level fixes.
- Do not begin the next feature branch until the current storage task has been reviewed and its focused/full validation results are reported.
- Keep each task on its assigned branch; never merge to `main` unless the maintainer explicitly approves.
- Do not claim to have run tests without actual command output.

## Project shape

- DeskTranslate is a Windows-first Python 3.12+ desktop application built with PySide6.
- Application code lives in `src/desktranslate/`; tests live in `tests/`; product/architecture documentation lives in `docs/`.
- Keep domain logic independent of Qt. Widgets should not perform provider network requests or OCR inference directly.
- Read `docs/architecture.md`, `CONTRIBUTING.md`, and `docs/testing.md` before changing the pipeline, persistent data, UI lifecycle, or tests.

## Commands

Run from the repository root when a local checkout is available:

- Routine validation: `python tools/validate.py`
- Pre-deployment checks: `python tools/validate.py --predeploy`
- Focused tests: `python -m pytest -q tests/test_vocabulary.py`
- Whole test suite: `python -m pytest -q`
- Lint: `python -m ruff check src tests tools`
- Formatting check: `python -m ruff format --check src tests tools`
- Types: `python -m mypy src`

Do not claim that checks passed unless they were actually executed. If a Windows/native check is unavailable, say so and keep it out of ordinary tests.

## Security and privacy boundaries

- Never commit API keys, credential data, private dialogue, screenshots, logs, machine-specific settings, or generated user data.
- API credentials belong in the existing OS credential-vault abstraction, not settings JSON or a new database.
- Vocabulary persistence must be explicit and local. Save only the source term, its translation, and required language metadata after an explicit caller action; do not save screenshots, full OCR frames, or recent dialogue automatically.
- Validate and bound all persisted/imported values. Use parameterized SQL. Never interpolate user input into SQL.
- Do not add automatic cloud fallback or send saved vocabulary/context to providers without a clearly documented, intentional feature flow.
- Routine tests must remain offscreen and must not control the real desktop, browser, global shortcuts, credential vault, or non-loopback network.
- Use isolated temporary directories in persistence tests. Add tests for malformed input, size limits, Unicode, and failure paths.

## Change discipline

- Work only on the requested branch; do not push feature work to `main`.
- Keep changes focused and preserve existing profile, glossary, settings, and translation behavior.
- Add regression tests for behavioral changes and update user-facing/privacy documentation when an implemented feature changes data handling.
- Do not mechanically split large controllers or change unrelated architecture to make a task appear complete.
- Do not treat a written plan as evidence that the feature is integrated or tested.
