# Android companion app — architecture and implementation plan

**Updated:** 2026-10-31  
**Status:** planning only. This document does not mean an Android app or APK exists.

## Goal

Add a native Android companion to DeskTranslate. The Windows/PySide6 application remains independent and unchanged. Android is a separate Gradle/Kotlin application because the desktop UI, Windows capture backend and native dependency stack cannot be packaged directly as an Android APK.

The first target is a sideloadable APK for current Android devices, including Android 16 (API 36). Proposed baseline: Kotlin, Jetpack Compose, a single Android app module, minSdk 26, and the latest stable compile/target SDK supported by the verified build toolchain. Confirm currently compatible stable Android Gradle Plugin, Kotlin, Compose and dependency versions before pinning them; do not use preview dependencies.

## Product scope

### Phase A — screen translation MVP

1. User selects source and target languages.
2. User starts a one-shot or live translation session from the visible app UI.
3. The app requests Android's system screen-capture approval and shows a persistent foreground-service notification while capturing.
4. User chooses a screen region. The app crops frames in memory and runs local OCR.
5. The selected translation adapter receives recognized text and returns a translation.
6. A user-enabled floating result overlay displays the translation; the user can move, hide, pause and stop it.
7. The main activity retains the latest source and translated text with explicit copy/retry controls.

MVP must support Latin and Japanese OCR. Prefer bundled ML Kit Text Recognition v2 models for these scripts so OCR is available immediately and does not depend on a first-use Google Play Services model download. Evaluate Korean and Chinese bundled models as the next script expansion. Do not describe OCR as universal or claim accuracy beyond measured fixtures.

### Phase B — vocabulary learning

Port the Windows feature's explicit-save behavior:
- User selects a source term and its displayed translation, reviews/edits both, then explicitly saves.
- Store only the approved term, translation, language-pair metadata and creation time in a separate local Room database.
- Provide language-pair filters, bounded search/paging, empty/error states and confirmed deletion.
- Keep learned vocabulary separate from the approved glossary. Never auto-save OCR/dialogue, upload the collection or silently add entries to a glossary.

### Phase C — provider and settings parity

Inspect the current desktop provider contracts before implementation. Use a Kotlin provider interface and bounded HTTP clients; preserve explicit provider selection, request deadlines, response-size limits, safe error states and no automatic cloud fallback.

Do not hardcode service credentials. Store user-supplied API keys using Android Keystore-backed encryption. Do not store keys in ordinary DataStore/JSON, SQLite, logs or exported profiles. Port providers in a staged way and document the exact provider set actually supported by the Android app. Existing desktop adapters are not automatically Android-compatible.

Support the existing product concepts where practical: source/target languages, provider/model/endpoint selection, approved glossary, title/profile settings and overlay appearance. Keep an honest parity table; do not mark a feature complete because a settings screen exists without working behavior.

## Android platform constraints (mandatory)

### Screen capture

- Use MediaProjectionManager and the Android system consent flow. Never use root, hidden APIs, accessibility scraping or another bypass to capture content.
- Android 14+ requires a fresh user approval for every capture session. Treat each MediaProjection token as single-use; create one virtual display per token. Register MediaProjection.Callback and release the display, surface, reader and worker on stop/revocation.
- Declare the mediaProjection foreground-service type and its required foreground-service permissions. Follow the documented ordering: request capture consent before starting the media-projection foreground service, then obtain the projection inside that service.
- Start capture only from a visible, explicit user action. Do not auto-start capture after boot or silently restart after the user stops it.
- Handle rotation and display-size changes through the documented virtual-display resize/surface path; do not re-use a consumed projection token.
- Respect Android's secure-window behavior. If another app marks content secure, accept that it cannot be captured; do not attempt to bypass it.
- Use bounded frame sampling and a latest-frame mailbox rather than an unbounded queue. OCR, translation and image processing must not run on the main thread. Reject stale results after pause/stop, region changes or newer source text.

### Floating overlay

- Request SYSTEM_ALERT_WINDOW only when the user enables the floating overlay and explain why it is needed. Check Settings.canDrawOverlays() and send the user to the official permission screen.
- Use TYPE_APPLICATION_OVERLAY; handle revocation, app stop, rotation and configuration changes safely.
- Keep the overlay small, movable, readable and dismissible. Do not claim guaranteed click-through behavior unless it is implemented and tested on supported Android versions.
- Provide an in-app result view as a fallback when the overlay permission is declined.

### OCR and privacy

- Keep captured frames and OCR output in memory by default. Do not create a screenshot gallery or persistent capture history.
- Send only recognized text and the explicitly configured translation context to the selected remote provider. Never send screenshots to translation APIs.
- Provide bundled OCR model choices for offline recognition. Translation still requires the selected provider's network or a separately configured local endpoint/model; do not advertise offline translation unless actually implemented.
- Keep diagnostic logs metadata-only. No OCR source text, translations, screenshots, tokens, API keys or authorization headers in logs.
- Make the capture state visible and provide an immediate Stop action.

## Architecture proposal

Keep platform and domain boundaries separate:

- capture/: MediaProjection lifecycle, ImageReader/Surface handling, region crop, frame throttling and generation stamps.
- ocr/: recognizer interface and ML Kit implementation(s), script selection and result normalization.
- translation/: provider interface, bounded HTTP client, adapters and typed errors.
- overlay/: permission flow, WindowManager overlay lifecycle and rendering.
- learning/: Room schema/DAO/repository and explicit-save workflow.
- settings/: DataStore preferences, provider/model/language configuration and encrypted credential storage boundary.
- profiles/: later parity for import/export with secrets and active capture identity excluded.
- ui/: Compose screens for setup, translation, providers, learning and diagnostics.

Prefer pure Kotlin domain classes and injected interfaces so unit tests do not require Android framework objects. Do not copy the Windows Python implementation mechanically.

## Milestones and gates

1. Android shell: Gradle project, app launch, Compose navigation, theme, language selection, CI build and unit-test baseline.
2. Capture proof: visible start flow, per-session consent, foreground service, single-use MediaProjection lifecycle, bounded in-memory frames, region picker/crop, pause/stop/revocation tests.
3. OCR proof: bundled Latin/Japanese recognizers, authored image fixtures, result ordering/geometry, repeatable offline recognition and measured performance on a physical Android device.
4. Translation MVP: provider interface, at least one deliberately selected working provider, timeout/cancel/stale-result tests, explicit network error and retry.
5. Overlay: optional permission flow, movable result overlay, fallback main screen, lifecycle/revocation and orientation tests.
6. Learning: explicit save/review/edit, language-pair isolation, search/paging, confirmed delete, migration and privacy tests.
7. Parity/release: port remaining agreed providers/settings, update feature parity and privacy documentation, run Android CI, produce a debug APK artifact, then a user-installable release APK. Do not create or commit a signing key; release signing is controlled by the maintainer.

## Verification and acceptance

- assembleDebug, Android lint, unit tests and instrumented tests pass on a pinned stable toolchain.
- Capture tests cover consent denied, revoked projection, repeated start/stop, rotation, screen-size changes, pause/stop during OCR, and rapid content changes. Tests verify no stale translation appears after a newer result or Stop.
- OCR fixtures include Latin and Japanese text, vertical/layout variation where supported, short text, punctuation and false-positive backgrounds. Report exact fixture scope and physical-device performance; do not overgeneralize.
- Translation tests cover provider errors, no network, invalid credentials, timeout, cancellation, Unicode and request/response bounds. No paid API call is made by routine tests.
- Learning tests cover explicit approval, duplicate entries, alternate translations, language-pair isolation, bounds, malformed database state, migration, deletion confirmation and no implicit provider upload.
- Privacy checks verify that no image, recognized dialogue, translation, credential or authorization header is persisted or logged.
- Manually verify on a real Android 14+ device and Android 16 device: consent flow, foreground notification, overlay permission, game/app switching, rotation, battery/background behavior and Stop. Emulator success is not a substitute for a physical-device check.
- CI uploads an APK artifact for inspection. The APK is not considered release-ready until a physical-device acceptance pass and truthful release notes exist.

## Explicit non-goals for the first Android milestone

- No root access, protected/secure-window bypass, hidden APIs or AccessibilityService-based screen scraping.
- No automatic capture at boot or without a visible user action.
- No automatic screenshot or full-dialogue persistence.
- No claim that every game, video, script or language is supported.
- No promise of offline translation; offline OCR and offline translation are separate capabilities.
- No silent cloud fallback or hidden upload of saved vocabulary.

## Authoritative platform references

- Android MediaProjection guide: https://developer.android.com/media/grow/media-projection
- Android 14 behavior changes — MediaProjection consent: https://developer.android.com/about/versions/14/behavior-changes-14
- Android foreground-service types: https://developer.android.com/develop/background-work/services/fgs/service-types
- Android SYSTEM_ALERT_WINDOW permission: https://developer.android.com/reference/android/Manifest.permission#SYSTEM_ALERT_WINDOW
- ML Kit Text Recognition v2 for Android: https://developers.google.com/ml-kit/vision/text-recognition/v2/android
- ML Kit Text Recognition v2 supported scripts/languages: https://developers.google.com/ml-kit/vision/text-recognition/v2/languages
