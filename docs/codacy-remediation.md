# Codacy remediation notes

This branch addresses findings exported from the ten analyzed branches. The export contains repeated branch instances of the same issue IDs; it is not a count of unique vulnerabilities.

## Changes in this remediation

- Replaced interpolated SQLite statements with fixed SQL text and parameter-bound values. The vocabulary table and its schema identifiers are module-owned constants; no user text is used as SQL syntax.
- Replaced runtime and qualification `assert` statements with explicit errors so checks remain active under `python -O`.
- Kept the CSV formula-prefix rejection and documented why standard CSV quoting is appropriate after that validation.
- Clarified the deterministic test PRNG, the empty pagination sentinel, and the HTTP handler parameter name.
- Documented the reviewed trust boundary around reading marshalled code objects from a locally built, digest-matched PyInstaller vendor archive.
- Documented GitHub's `id-token: write` workflow permission as OIDC attestation permission, not a hard-coded credential.

## Findings requiring analyzer re-check

Subprocess calls in this project are invoked with argument arrays and without `shell=True`. Their executable and argument sources differ by use case: Python's own interpreter for tests and probes, a resolved Tesseract binary for OCR, verified installer/signing tool paths for packaging, and Git for repository provenance/privacy scanning. Static warnings still require line-by-line review; no blanket rule disablement is intended.

The Agentlinter report claiming that `CLAUDE_HANDOFF.md` is missing is inconsistent with the repository tree: the file is present beside `CLAUDE.md`. Treat this as an analyzer/workspace false positive unless a fresh scan proves otherwise.

## Validation status

This document does not claim tests have passed. Focused tests, full repository validation, Codacy re-analysis, and Windows-only qualification must run against this branch before the remediation is considered complete.
