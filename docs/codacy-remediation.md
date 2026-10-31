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

The current PR #6 head `45288411cb63d82e12ddf9251ddefd97720dd5c7` completed Windows quality workflow [run 41188227669](https://github.com/uniquecasper/DeskTranslate/actions/runs/41188227669) successfully on 2026-10-31.

- Pre-deployment validation: 615 pytest cases passed with zero failures, errors or skips.
- Dependency audit: 76 dependency entries inspected; zero reported vulnerabilities.
- Portable build and frozen executable startup/runtime checks: passed. The packaged OCR, Qt assets, loopback provider and credential lifecycle checks all reported true.
- Privacy scan: passed with no findings across the tracked tree, reachable history and built artifacts.
- Codacy annotation collection: the workflow step completed and recorded an available, successful check-run result with no annotation entries.
- Artifact outputs: `desktranslate-windows` (214,492,702 bytes; SHA-256 `ef747b7b7c0e7db7883b46cbaeb604d0feafaead33e99b3c686a662e18ce3af4`) and `desktranslate-quality-reports` (15,110 bytes; SHA-256 `b99ad5b20c2025cda01495b7a18b839f2deb10f19ef924cc841a4722d6bfb0ba`).

The packaged instance report was built from the 2.0.0 base because PR #6 is a security-remediation branch based on current `main`; it does not qualify the separate 2.0.1 candidate. Native physical-display/consumer-PC checks remain outside this hosted offscreen CI evidence. Codacy/CodeRabbit review threads are currently resolved; this remediation does not claim that every historical finding across all ten analyzed branches has been eliminated.
