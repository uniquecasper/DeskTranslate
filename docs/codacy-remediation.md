# Codacy remediation notes

This branch addresses findings exported from the ten analyzed branches. The export contains repeated branch instances of the same issue IDs; it is not a count of unique vulnerabilities.

## Changes in this remediation

- Replaced interpolated SQLite statements with fixed SQL text and parameter-bound values. The vocabulary table and its schema identifiers are module-owned constants; no user text is used as SQL syntax.
- Replaced runtime `assert` checks and selected qualification-helper assertions with explicit errors. The OCR model checks and steady/chaos endurance gates in `.github/workflows/release.yml` also use `require_release_condition`, so those acceptance checks remain active under Python optimization.
- Kept the CSV formula-prefix rejection and documented why standard CSV quoting is appropriate after that validation.
- Clarified the deterministic test PRNG, the empty pagination sentinel, and the HTTP handler parameter name.
- Restricted marshalled frozen-code inspection to an explicitly trusted local build. Externally supplied `--artifact-root` content is treated as untrusted and is never passed to `marshal.loads`; the local-build trust decision is explicit in CI.
- Documented GitHub's `id-token: write` workflow permission as OIDC attestation permission, not a hard-coded credential.

## Findings requiring analyzer re-check

Subprocess calls in this project are invoked with argument arrays and without `shell=True`. Their executable and argument sources differ by use case: Python's own interpreter for tests and probes, a resolved Tesseract binary for OCR, verified installer/signing tool paths for packaging, and Git for repository provenance/privacy scanning. Static warnings still require line-by-line review; no blanket rule disablement is intended.

The Agentlinter report claiming that `CLAUDE_HANDOFF.md` is missing is inconsistent with the repository tree: the file is present beside `CLAUDE.md`. Treat this as an analyzer/workspace false positive unless a fresh scan proves otherwise.

## Validation status

The pre-deployment validation step on commit `6968ed244ee469a9307f3a1e35a4a4b19775dd4e` completed successfully: 615 pytest cases passed with zero failures/errors/skips, and `pip-audit` found zero vulnerabilities across 76 dependency entries. The source/history privacy scan passed with no findings. That run was cancelled during the portable-app build after a newer commit superseded it, so it does not establish a completed packaged-runtime check on that head. Codacy reported zero PR annotations on that same head. The latest documentation-only commit has its own fresh CI run in progress. These are incremental pull-request checks; they do not establish that every historical finding on `main` has been eliminated.
