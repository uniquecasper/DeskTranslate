# DeskTranslate Android

This is a separate native Android application. It does not package or modify the Windows Python/PySide6 application.

## Current implementation scope

- Kotlin + Jetpack Compose application shell.
- Android MediaProjection capture with explicit system consent and a media-projection foreground service.
- Bounded latest-frame processing; at most one OCR operation runs at a time.
- On-device ML Kit OCR with Latin, Japanese, Chinese and Korean recognizers.
- OCR lines retain their text, bounding boxes, confidence, background color and text color.
- A small number of low-confidence lines can be retried from focused context crops.
- Screen lines are sent to the selected provider together in one ordered JSON request, rather than issuing a separate HTTP request for every line.
- Translations are mapped back onto the original OCR bounding boxes and drawn in a touch-through overlay.
- A separate draggable floating "DT" control hides/shows the in-place translation layer.
- Explicit provider selection for OpenAI Chat Completions, Ollama chat, Anthropic Messages and Gemini generateContent.
- HTTPS-only remote endpoints; plain HTTP is accepted only for loopback.
- No redirects, bounded response reads, finite connection/read deadlines and source-text prompt-injection boundary.
- API credentials encrypted with AES-GCM using an Android Keystore key.
- Explicitly approved local vocabulary saved to a separate SQLite database.

## Architecture references

- TextGrab (MIT): word/line OCR structure, confidence-aware recognition and translation-engine separation; word-level tap selection remains future work.
- ALSTMobile (MIT): MediaProjection lifecycle, coordinate-aligned translation blocks and draggable overlay-control design.
- AidanPark/screen-translator: focused crop retry and stable-target concepts, referenced only from Apache-2.0 commit `8717cf0`; no source from later PolyForm Noncommercial revisions is used.

DeskTranslate's code is implemented separately and retains its own API-key storage, endpoint validation, bounded requests and translation-provider adapters. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Build

Open the android/ directory in Android Studio with a compatible Android SDK, or install Gradle 9.5.0 and run:

    gradle -p android clean testDebugUnitTest lintDebug assembleDebug

The debug APK is written to:

    android/app/build/outputs/apk/debug/app-debug.apk

GitHub Actions runs the same checks and uploads the debug APK as a workflow artifact.

## Platform requirements

- minSdk 26; compileSdk/targetSdk 36.
- Screen capture requires explicit Android system approval for each session.
- The app shows an ongoing foreground-service notification while capturing.
- Android's "Display over other apps" permission is required for the floating control and in-place translation overlay.
- OCR is on-device; only recognized text submitted for translation is sent to the selected provider.
- Translation uses the configured online provider. Offline OCR does not mean offline translation.
- Device-specific MediaProjection coordinate mapping and overlay behavior still require physical-device qualification, including Android 16 / OriginOS.

## Privacy

Captured frames and OCR regions are processed in memory. The app does not create a screenshot gallery or persist recognized dialogue automatically. Only text submitted to the selected provider is sent over the network. Vocabulary is saved only when the user presses the explicit save button. Credentials are encrypted using Android Keystore and are not stored in ordinary settings or vocabulary rows.

## Release status

This is a development milestone, not a release-qualified APK. CI compilation and unit tests are necessary but not sufficient; a physical-device test and a maintainer-controlled signing process are still required before release.
