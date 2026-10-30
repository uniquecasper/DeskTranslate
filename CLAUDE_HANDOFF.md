# Claude Handoff — Android companion app

Updated: 2026-10-31

## Repository and branch state

- Repository: uniquecasper/DeskTranslate.
- Windows desktop application remains on main; the vocabulary-learning work (PRs #1–#4) is already integrated there.
- Windows 2.0.1 packaging candidate is a separate open draft PR #5 on claude/windows-installer-2-0-1. Keep it separate; do not merge, rewrite, or use it as the Android feature branch.
- Android planning branch: claude/android-port-plan, based on main.
- The branch currently contains planning/handoff documentation only. No Android Gradle project or APK existed on main when this plan was prepared.

## Responsibility split and stage gate

- ChatGPT (coordination, non-coding): owns scope, product requirements, platform architecture, privacy/acceptance criteria, non-code documentation, branch/PR/check tracking and review of diffs/results. It must not author or edit application implementation code or test code.
- Claude Code (implementation): owns Android application code, Android tests, Gradle configuration, code-level fixes and implementation-specific validation. Read CLAUDE.md, this file, docs/architecture.md, docs/testing.md, docs/privacy.md and docs/android-port-plan.md before starting.
- User/maintainer: decides whether to hand the implementation task to Claude Code and whether to review/merge changes. Never merge to main automatically.

## Current task

Implement the first native Android milestone on claude/android-port-plan, using docs/android-port-plan.md as the requirements and acceptance baseline. The immediate deliverable is a working Android project shell plus a tested screen-capture lifecycle proof; do not claim the full screen translator or APK release is complete at that point.

### First implementation milestone

1. Establish a Kotlin/Jetpack Compose Gradle app using current stable, mutually compatible toolchain/dependency versions. Verify SDK 36 support before pinning; avoid preview versions.
2. Add app navigation/theme and a minimal setup/translation shell.
3. Implement the explicit MediaProjection consent and foreground-service lifecycle correctly for Android 14+ and current Android versions.
4. Add a safe stop/pause/revocation path and an in-memory, bounded frame pipeline. Do not persist frames.
5. Add domain/interface boundaries for OCR and translation without pretending they are already functional.
6. Add unit/instrumented tests for consent denial, revoke, stop, repeated sessions, orientation changes and stale-work invalidation.
7. Add Android CI for lint, tests and assembleDebug; upload a debug APK artifact only after all jobs pass.
8. Update product/privacy docs to identify implemented vs planned features precisely.

### Task constraints

- Work only on claude/android-port-plan; do not touch main or the Windows candidate PR #5.
- Do not add Android code to the Python/PySide6 package or attempt to package Windows binaries into an APK.
- Do not use AccessibilityService, root, hidden APIs or any secure-window bypass for capture.
- Do not add external requests to tests; mock providers and use authored synthetic screenshots.
- Never commit API keys, signing keystores, private dialogue or captured screenshots.
- Do not create or commit a release signing key. A local debug APK may be built; a release-signed APK requires a maintainer-controlled key and explicit approval.
- Report the exact commands, SDK/toolchain versions, test results and untested device conditions. Do not claim physical-device verification unless it was actually performed.

## After the first milestone

Continue in order: OCR (bundled Latin/Japanese models), translation-provider adapter, optional movable overlay, local explicit-save vocabulary-learning, then provider/settings parity. Keep each milestone separately testable. Update this handoff after each accepted stage. Do not call the Android port feature-complete until the agreed provider and feature parity table is satisfied and a physical Android device passes the manual acceptance checks.

## Key product intent

Android is an independent native companion to DeskTranslate, not a direct binary conversion of the Windows application. Screen capture must be user-authorized and visibly active; OCR is local; only recognized text may be sent to a user-selected translation provider. The vocabulary-learning feature is explicit-save, local-only and separate from the approved glossary.
