# Windows 2.0.1 candidate qualification status

Updated: 2026-10-31

## Verdict

**INTERNAL QUALIFICATION CANDIDATE ONLY — NOT APPROVED AS A STABLE RELEASE.**

This record describes the hosted evidence for commit `0fbf6686d834cabcfbc3ddb24293e34334b8b95c` on
`claude/windows-installer-2-0-1`. It does not promote the candidate, authorize a tag,
or replace the maintainer's release decision.

- Pull request: [#5 — Prepare DeskTranslate 2.0.1 Windows installer candidate](https://github.com/uniquecasper/DeskTranslate/pull/5)
- Release-candidate workflow: [run 41140156640](https://github.com/uniquecasper/DeskTranslate/actions/runs/41140156640)
- Windows quality workflow: [run 41140170272](https://github.com/uniquecasper/DeskTranslate/actions/runs/41140170272)
- Candidate artifact: `desktranslate-release-candidate`, 299,066,709 bytes, hosted artifact SHA-256
  `d8965b4bd4a6a2deba0c929210b281acdf53ac848af55bab7c3c1a52e7b75ce9`.
- Hosted attestation: [attestation 61967555](https://github.com/uniquecasper/DeskTranslate/attestations/61967555).

## Evidence that passed

The hosted Windows candidate job completed successfully:

- Pre-deployment validation: 608 tests passed; the validation/lint checks and mypy check completed successfully.
- Release package compilation: portable application and Inno Setup installer compiled successfully.
- Packaged executable smoke test: passed.
- Frozen ownership/crash-recovery qualification: passed for the recorded offscreen, same-user scope.
- Portable runtime and installer lifecycle/metadata checks: the combined qualification step completed successfully.
- Installer report: install, startup, shortcuts, executable/uninstall metadata, reinstall, obsolete owned-runtime cleanup, uninstall, settings/model retention and final cleanup were recorded as passed.
- Artifact privacy scan: passed with no findings across the publishable tree, reachable history, extracted frozen files, seven release files and 411 release-archive members.

The installer report also explicitly records `previous_version_upgrade: false`. The current workflow does not pass a `PreviousInstaller` to `tools/qualify_installer.ps1`; therefore the successful reinstall/lifecycle checks must not be described as a verified 2.0.0-to-2.0.1 upgrade.

## Verified previous installer input

The official upstream GitHub release API for [v2.0.0](https://github.com/DeskTranslate/DeskTranslate/releases/tag/v2.0.0)
lists the previous setup asset with this identity:

- Asset: `DeskTranslate-2.0.0-Setup-x64.exe`
- Official download: https://github.com/DeskTranslate/DeskTranslate/releases/download/v2.0.0/DeskTranslate-2.0.0-Setup-x64.exe
- GitHub release-asset digest: `sha256:2c2aab018c7e34b38fe4b04f3ffb099c6707fbd63d14dbd21546effe43443fe5`

Use this exact file as `PreviousInstaller` input and verify the downloaded bytes against that digest before executing it. The asset listing establishes the expected release-asset digest; it does not mean the 2.0.1 upgrade has already been run.

## Gates not completed for 2.0.1

1. **Two-hour steady endurance:** skipped in run 41140156640 because the workflow's `endurance` input was false.
2. **Thirty-minute fault/chaos endurance:** skipped for the same reason.
3. **Previous-version upgrade:** not run; `previous_version_upgrade` is false.
4. **Stable evidence is stale:** `docs/manual-qualification.json`, `docs/soak-2h.json` and the recorded stable evidence describe version 2.0.0. The stable gate requires evidence matching the current package version, current source/assets, Python runtime and soak-harness hash. The 2.0.0 reports cannot qualify 2.0.1.
5. **Authenticode signing:** certificate import/signing was skipped. The candidate is unsigned and may trigger Windows SmartScreen. The existing unsigned approval text is explicitly for v2.0.0; do not silently treat it as a v2.0.1 approval.
6. **Physical consumer-PC checks:** hosted offscreen tests do not establish physical Windows 10/11 desktop, monitor/DPI, fullscreen, screen-reader or real-game/media qualification. Keep unavailable checks labelled NOT TESTED.

## Required work before stable promotion

- Run the 2.0.1 two-hour steady and thirty-minute fault workloads with `endurance=true`; verify both reports are complete and match the exact 2.0.1 source/assets, Python 3.12.15 and current `tools/soak.py` hash.
- Qualify an actual previous-installer upgrade by supplying a trusted, checksum-verified previous setup executable through the existing `PreviousInstaller` parameter. Confirm the real upgrade path and preservation of user data; do not infer this from a same-version reinstall.
- Update `docs/manual-qualification.json` only after each 2.0.1 gate has evidence. It must state version 2.0.1, preserve NOT TESTED limitations, and not copy forward 2.0.0 results as if they belonged to this candidate.
- Obtain an explicit maintainer decision for unsigned v2.0.1 distribution, or configure a real publisher certificate and run the signed qualification. Never self-sign or claim publisher identity without a trusted certificate.
- Re-run the stable gate against the final source and exact canonical `v2.0.1` tag, then independently verify final hashes, SBOM/notices, provenance and hosted attestations. Do not merge or publish automatically.

## Scope note

PR #5 changes only the release-workflow trigger and the application/manifest version from 2.0.0 to 2.0.1; it does not change application behavior. A green candidate workflow is useful packaging evidence, but it is not a substitute for the unrun 2.0.1 stable gates listed above.
