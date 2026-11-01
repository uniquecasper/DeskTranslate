# DeskTranslate Android

This is a separate native Android application. It does not package or modify the Windows Python/PySide6 application.

## Current implementation scope

- Kotlin + Jetpack Compose application shell.
- Android MediaProjection capture with the system consent flow and a media-projection foreground service.
- Bounded latest-frame processing (one in-flight OCR job; later frames are dropped).
- Bundled ML Kit Text Recognition v2 models for Latin and Japanese scripts.
- Explicit provider selection for OpenAI Chat Completions, Ollama chat, Anthropic Messages and Gemini generateContent.
- HTTPS-only remote endpoints; plain HTTP is accepted only for loopback.
- No redirects, bounded response reads, finite connection/read deadlines and source-text prompt-injection boundary.
- API credentials encrypted with AES-GCM using an Android Keystore key.
- Explicitly approved local vocabulary saved to a separate SQLite database.

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
- OCR is on-device. The current capture implementation recognizes the full captured display; region selection and a floating translation overlay are not implemented yet.
- Translation is online unless a user configures an on-device/loopback provider. Offline OCR does not mean offline translation.
- The current Android provider adapters are OpenAI, Ollama, Anthropic and Gemini. DeepL, Google quick translation, LibreTranslate, OpenRouter, LM Studio and arbitrary OpenAI-compatible endpoint configuration still require implementation/verification.
- Showing a completed translation in a scrollable system overlay is supported after the user grants Android's Display over other apps permission.
- The overlay currently displays the translated result in a floating panel; translation is not yet mapped back onto each original OCR text rectangle.
- Device-specific MediaProjection and overlay behavior still require physical-device qualification, including Android 14+ and Android 16.

## Privacy

Captured frames are copied into memory, processed locally and released. The app does not create a screenshot gallery or persist recognized dialogue automatically. Only text the user explicitly submits is sent to the selected translation provider. Vocabulary is saved only when the user presses the explicit save button. Credentials are encrypted using an Android Keystore AES key and are not stored in ordinary settings or vocabulary rows.

## Release status

This is an initial implementation milestone, not a release-qualified APK. CI must compile, test and upload the debug APK. A physical-device test and a maintainer-controlled signing process are still required before release.
