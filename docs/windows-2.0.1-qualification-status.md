# Windows 2.0.1 candidate qualification status

Updated: 2026-10-31

## Verdict

**INTERNAL QUALIFICATION CANDIDATE ONLY — NOT APPROVED AS A STABLE RELEASE.**

The previously recorded candidate run is historical evidence for an earlier commit only. It is not proof that the final integrated PR #5 + PR #6 candidate has passed.

## Historical 2.0.1 candidate evidence

- Pull request: [#5 — Prepare DeskTranslate 2.0.1 Windows installer candidate](https://github.com/uniquecasper/DeskTranslate/pull/5)
- Earlier release-candidate workflow: [run 41140156640](https://github.com/uniquecasper/DeskTranslate/actions/runs/41140156640), commit `0fbf6686d834cabcfbc3ddb24293e34334b8b95c`.
- Earlier candidate artifact: `desktranslate-release-candidate`, 299,066,709 bytes, SHA-256
  `d8965b4bd4a6a2deba0c929210b281acdf53ac848af55bab7c3c1a52e7b75ce9`.
- Earlier hosted attestation: [attestation 61967555](https://github.com/uniquecasper/DeskTranslate/attestations/61967555).

That earlier run passed packaging, packaged startup, offscreen frozen-instance checks, portable/installer lifecycle and artifact privacy checks. It did **not** qualify a real 2.0.0-to-2.0.1 upgrade, and both endurance workloads were skipped. It must not be used as final-candidate evidence.

## Verified previous installer fixture

The official upstream GitHub release record for [v2.0.0](https://github.com/DeskTranslate/DeskTranslate/releases/tag/v2.0.0) lists:

- Asset: `DeskTranslate-2.0.0-Setup-x64.exe`
- Download URL: https://github.com/DeskTranslate/DeskTranslate/releases/download/v2.0.0/DeskTranslate-2.0.0-Setup-x64.exe
- Expected SHA-256: `2c2aab018c7e34b38fe4b04f3ffb099c6707fbd63d14dbd21546effe43443fe5`

The combined candidate workflow downloads this exact file and verifies its digest before execution. The installer qualification script independently repeats the digest check and validates the installed product and uninstall metadata as version 2.0.0 before proceeding to 2.0.1.

## Required final-candidate evidence

The combined PR #5 + PR #6 candidate must complete the following on its exact final commit:

1. Windows quality workflow: full validation, packaged startup/OCR, offscreen frozen-instance checks, Codacy evidence capture and privacy scan.
2. Release-candidate workflow: portable and installer builds, previous-version upgrade, settings/model preservation, reinstall/uninstall lifecycle, SBOM, provenance, hashes and hosted attestation.
3. Two-hour steady endurance: at least 7,200 seconds; source/assets and `tools/soak.py` hashes unchanged; Python 3.12.15; workload, resource and continuous-worker qualification passed; no worker restarts or remaining children.
4. Thirty-minute fault/chaos endurance: at least 1,800 seconds; injected loopback faults observed; controlled restarts; source/harness/runtime hashes match; workload/resource qualification and cleanup passed.

Do not reuse any 2.0.0 soak or manual qualification report as 2.0.1 evidence. The stable gate is intentionally not invoked by this internal qualification workflow.

## Separate stable-release gates

- The current `docs/manual-qualification.json` and unsigned-release approval refer to v2.0.0. They do not authorize a v2.0.1 stable release.
- The 2.0.1 build is unsigned unless a trusted publisher certificate is configured. Never self-sign or claim publisher identity without a trusted certificate.
- Physical Windows 10/11 consumer-PC, mixed-DPI, fullscreen/media, screen-reader and hardware-specific checks remain NOT TESTED unless separately performed and documented.

## Current decision

Keep the candidate unpublished. Merge PR #5 only after both Windows quality and full release-candidate workflows pass on the final combined commit. Merging the PR does not create a tag or publish a release.
