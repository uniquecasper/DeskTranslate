# Security and Manual Review Record

Review date: 2026-10-31  
Repository: `uniquecasper/DeskTranslate`  
Scope: Pull request #6, branch `fix/codacy-security-remediation`  
Current reviewed head at the time of this record: `6968ed244ee469a9307f3a1e35a4a4b19775dd4e`

## Executive status

This record separates automated analyzer results, code changes inspected in this pull request, and release/manual qualification that is still outstanding. A successful incremental pull-request check is not evidence that every historical issue reported against `main` has been re-scanned or removed.

| Control | Result | Evidence / limitation |
|---|---|---|
| Codacy PR check | Passed; 0 annotations | Latest check run on the head above completed successfully at 2026-10-31 09:16 UTC and reported “Codacy found no issues in your code”. This is the PR check result, not a full historical baseline re-scan. |
| Snyk GitHub status | Passed | `security/snyk (uniquecasper)` reported success for the head above. The detailed Snyk dashboard report was not independently accessible from this review session. |
| Dependency audit | Previous completed run: 76 packages, 0 known vulnerabilities | The report came from an earlier successful CI head, not the current head. Reconfirm from the latest CI artifact before treating it as current evidence. |
| Source/artifact privacy scan | Previous completed run passed with no findings | Earlier scan covered source tree, Git history, packaged members and frozen modules. Reconfirm from the latest CI artifact. |
| Windows CI | In progress at record creation | Latest run: https://github.com/uniquecasper/DeskTranslate/actions/runs/41187847542 |
| CodeRabbit full review | In progress | Latest review was triggered on 2026-10-31 09:14 UTC. Do not treat this as completed until its check run finishes and any new comments are read. |
| Human desktop / installer qualification | Not completed | Requires a reserved Windows desktop and/or clean consumer Windows environment. Not covered by headless CI. |
| Long-duration qualification | Not completed | Two-hour steady soak and 30-minute chaos soak have not been run in this task. |
| Release signing / installer promotion | Not performed | No tag, release, stable promotion or signed installer was created. |

## Historical Codacy baseline

The supplied Codacy export in the companion `uniquecasper/-ssue` repository contained ten analyzed branch snapshots. The `main` snapshot contained 130 unique issue IDs; across all ten branch snapshots there were 1,212 repeated issue instances. The repeated instances must not be counted as 1,212 unique vulnerabilities.

The main-branch pattern distribution was:

| Pattern | Instances | Manual disposition |
|---|---:|---|
| Bandit B101 (assert statements) | 27 | Runtime / qualification assertions in the reviewed source paths were replaced with explicit failures. Remaining Python `assert` statements in test code are test assertions, not production authorization checks. Release workflow assertions identified by CodeRabbit were also replaced. |
| Bandit B603 (subprocess calls) | 23 | Calls were reviewed by use case. The affected flows use fixed argument arrays, no shell, and constrained/validated executables or repository-controlled scripts. Targeted suppressions document the boundary; they are not a blanket suppression. |
| Semgrep dangerous subprocess use | 18 | Reviewed with B603 findings. Tainted command construction was constrained; no shell expansion is used in the reviewed paths. |
| Bandit B404 (subprocess import) | 11 | Import warning follows use of Python's subprocess API. It is not itself proof of an exploitable process launch; call sites were reviewed separately. |
| Semgrep raw SQL execution | 11 | Vocabulary queries use static SQL and bound parameters; schema/table identifiers are module-owned constants. |
| Semgrep tainted subprocess args | 9 | Reviewed with process-launch paths; executable validation and argument boundaries are documented in code. |
| Bandit B608 (formatted SQL) | 6 | Vocabulary SQL formatting based on fixed module-owned identifiers was removed or converted to static SQL; user values are bound parameters. |
| Bandit B607 (partial executable path) | 6 | Git/SignTool paths and fixed scripts were reviewed; residual environment/PATH trust is a manual review point for release tooling. |
| Semgrep formatted SQL query | 5 | Addressed with static SQL and parameter binding. |
| Bandit B105 (secret-looking constants) | 3 | Empty token sentinel changed to `None`; test fixtures were changed to non-secret-looking generic values. |
| Other SQL expression findings | 3 | Static SQL / bound-value treatment applied to vocabulary persistence. |
| Pylint W0622 | 1 | HTTP handler override keeps the required `format` parameter name with a narrowly scoped lint suppression. |
| Agentlinter referenced file | 1 | Reported missing handoff file was a workspace false positive; the referenced file exists in the repository tree. |
| Marshal / unsafe deserialization | 3 combined analyzer IDs | Frozen marshal inspection is allowed only for an explicitly trusted local build. External `--artifact-root` inputs cannot be combined with that trust option; untrusted frozen bytes are not passed to `marshal.loads`. |
| Bandit B311 | 1 | Deterministic `random.Random(seed)` is used only for test simulation, not cryptography. |
| Defused CSV recommendation | 1 | CSV export rejects formula-prefixed values before using the standard CSV writer; user text is not emitted as executable spreadsheet formulas. |
| Hard-coded token YAML rule | 1 | `id-token: write` is GitHub OIDC provenance permission, not a stored secret/token. The workflow comment and narrow analyzer suppression explain this distinction. |

**Baseline limitation:** The export is a historical snapshot and may have stale line numbers or results. The latest Codacy PR check reports zero findings on the PR diff, but a complete new Codacy scan of all 130 historical main-branch issue IDs has not been independently verified. Do not mark the historical baseline globally cleared based only on the PR check.

## CodeRabbit findings reviewed

The initial CodeRabbit full review posted seven actionable comments. Their review threads are currently marked resolved in GitHub:

1. Run Codacy evidence capture/upload even if an earlier validation step fails. The CI step now runs unless cancelled, initializes the evidence directory, and the evidence upload uses an unconditional status condition.
2. Treat GitHub API failures as unavailable evidence instead of failing the Windows job. The PowerShell capture block catches failures and records a concise failure reason.
3. Select the newest Codacy check run before testing completion. The workflow sorts matching check runs by descending run ID rather than `completed_at`.
4. Retrieve all Codacy annotation pages. The workflow requests subsequent pages until fewer than 100 annotations are returned.
5. Narrow the documentation claim about optimization-safe assertions. The text was narrowed to the paths actually changed; additionally, the OCR and endurance gates in the release workflow now use explicit runtime failures instead of Python `assert`.
6. Enforce the frozen-code marshal trust boundary. Only the explicit trusted-local-build path may deserialize; externally supplied artifact roots are excluded. A test verifies untrusted bytes do not reach the marshal loader.
7. Launch the exact executable that passed validation. `run_bounded_probe` now passes the resolved executable path to `Popen`, preserving the remaining arguments.

The above resolves the *original seven comments*. A newer CodeRabbit full review on head `6968ed244ee469a9307f3a1e35a4a4b19775dd4e` was started at 09:14 UTC on 2026-10-31 and was still running when this file was authored. Its result must be appended after completion.

## Additional regressions addressed during this review

- Fixed a Windows-only test failure caused by the checkout being on drive D: while pytest temporary files were on drive C:. The test changes to the temporary directory before computing a relative executable path.
- Removed direct test-side `marshal.dumps` usage. The trusted-code test now stubs the scanner's marshal loader with a compiled expected code object while the separate untrusted-input test still proves the loader is not reached.
- Added `require_release_condition` and a regression test, then replaced four release workflow assertions (Japanese OCR, English OCR, two-hour soak acceptance, and chaos-soak acceptance). These checks now fail explicitly even when Python optimization is enabled.

## Human review checklist — still required

The reviewer should inspect and record the following before considering a stable release:

- [ ] Review subprocess suppressions one by one, especially the release SignTool and PowerShell verification paths. Confirm executable discovery is acceptable for the intended build environment.
- [ ] Inspect the final CodeRabbit full-review result on the latest PR head and verify no new actionable comments remain.
- [ ] Download the latest CI artifact and confirm the current JUnit test totals, `pip-audit` report, Codacy annotation JSON, packaged runtime report, packaged instance report, and privacy-scan JSON.
- [ ] Confirm installer upgrade from the immediately previous published installer, including preservation of user data/settings.
- [ ] Test a clean consumer Windows environment with no developer Python/toolchain and verify installation, startup, shutdown, update/uninstall behavior.
- [ ] Run the documented two-hour steady workload and 30-minute chaos/fault soak on the source-matched release runtime; inspect child-process cleanup and resource reports.
- [ ] Manually test foreground focus/restore, native screen capture, selection interaction, multi-monitor behavior, and OCR performance on an ordinary desktop session.
- [ ] Verify publisher certificate identity and trusted timestamp only if signing is configured. No certificate or signing secret should be added to this report.

## Repository / release boundary

This work is confined to the draft pull request branch. The pull request has not been merged. The `main` branch has not been modified by this remediation work. No release tag, public release, stable promotion, or signed installer was created.
