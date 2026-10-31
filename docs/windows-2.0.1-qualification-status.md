# Windows 2.0.1 candidate qualification status

Updated: 2026-10-31

## Verdict

**MERGED TO MAIN AS AN INTERNAL QUALIFICATION CANDIDATE — NOT APPROVED AS A STABLE RELEASE.**

PR #5 was merged to `main` after both final-candidate Windows workflows completed successfully on the exact tested candidate commit. This merge does not publish a stable release, create a tag, or authorize distribution as a signed/publisher-verified build.

## Exact candidate and merge

- Candidate branch: `claude/windows-installer-2-0-1`
- Tested candidate commit: `8cfc4e062097757387e5de6b0f0960e6c69edfec`
- Main merge commit: `e9f39607a403a34d1b41ac77be58a638347b49f7`
- PR #5: [Prepare DeskTranslate 2.0.1 Windows installer candidate](https://github.com/uniquecasper/DeskTranslate/pull/5)
- PR #6 security remediation is included in the merged source history. Do not merge a duplicate copy.
- PR #4 was already merged before this candidate.

## Final-candidate CI evidence

- Windows quality workflow: [run 41189425930](https://github.com/uniquecasper/DeskTranslate/actions/runs/41189425930) — **success**.
- Full release-candidate qualification: [run 41189423106](https://github.com/uniquecasper/DeskTranslate/actions/runs/41189423106) — **success**.
- Automated test suite: **615 passed**.
- Packaged frozen executable startup and offscreen frozen-instance ownership/recovery checks passed.
- Synthetic English and Japanese OCR model verification passed.
- Verified v2.0.0 installer fixture and v2.0.0-to-2.0.1 upgrade qualification passed; settings preservation was verified.
- Installer lifecycle, reinstall/uninstall cleanup, portable runtime checks, artifact privacy scan, checksums and hosted build provenance passed.
- Privacy scan reported no findings in its defined scan scope. This does not prove the absence of every possible secret.

## Endurance qualification

- Two-hour steady workload: completed in **7,200.38 seconds**, with **579 accepted** operations. Source remained unchanged; workers closed; no child processes remained.
- Thirty-minute fault/chaos workload: completed in **1,800.14 seconds**, with **254 accepted** operations. Injected loopback faults and controlled session recovery were part of the passing qualification; source remained unchanged; workers closed; no child processes remained.

Both endurance reports were checked against the exact candidate source/runtime and harness hashes by the workflow.

## Hosted candidate artifact

- Workflow artifact: [desktranslate-release-candidate](https://github.com/uniquecasper/DeskTranslate/actions/runs/41189423106/artifacts/13043216660)
- Artifact ID: `13043216660`
- Size: **299,099,300 bytes**
- SHA-256: `216e87b61dfb13de7f503bdf8589f9c4ebf99eb997a111687bc1e45162e6d760`
- Build provenance attestation: [attestation 62110154](https://github.com/uniquecasper/DeskTranslate/attestations/62110154)

The artifact is a hosted qualification candidate and is time-limited by GitHub Actions artifact retention. Preserve its checksum when downloading it.

## Remaining limitations and stable-release gates

- No target consumer Windows PC was available for hands-on verification. Real desktop interaction, display/DPI scaling, fullscreen/media behavior, screen-reader/accessibility behavior and hardware-specific compatibility remain **NOT TESTED**.
- The hosted build is **unsigned** because the trusted publisher-certificate import step was skipped. Do not claim publisher identity or Authenticode signing.
- Hosted offscreen checks are not a replacement for physical-device validation.
- No v2.0.1 stable tag or GitHub Release has been created by this merge.
- A stable release requires the remaining manual/physical checks, trusted signing where applicable, and a separate explicit release decision.

## Current decision

Keep v2.0.1 classified as an internal qualification candidate. The tested candidate and integrated security remediation are now in `main`; stable release publication remains blocked on the unperformed physical/manual checks and signing decision.
