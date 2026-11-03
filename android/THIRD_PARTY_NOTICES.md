# Android third-party references and license audit

DeskTranslate uses independently written implementations informed by three relevant open-source Android projects. Their repositories are not bundled as dependencies, and their Kotlin source files have not been copied into DeskTranslate.

## 1. TextGrab — OCR and selectable text concepts

- Repository: https://github.com/AhmetCanArslan/TextGrab
- License: MIT
- Upstream copyright notice: Noah (notune) and AhmetCanArslan; see the upstream LICENSE file.
- Relevant concepts: word/line OCR geometry, confidence-aware recognition, selectable text representation, and separation of OCR from translation engines.
- DeskTranslate implementation points:
  - `android/app/src/main/java/com/uniquecasper/desktranslate/ocr/OcrEngine.kt`
  - `android/app/src/main/java/com/uniquecasper/desktranslate/translation/ScreenTextFilter.kt`
- Current limit: DeskTranslate retains line-level boxes for in-place translation. Full word-level tap/selection and per-word dictionary cards are not implemented yet.

## 2. ALSTMobile — coordinate-aligned overlay

- Repository: https://github.com/navidseyedain/ALSTMobile
- License: MIT
- Upstream copyright notice: Navid Seyedain; see the upstream LICENSE file.
- Relevant concepts: MediaProjection lifecycle, normalized/screen-space translation blocks, an overlay control, and rendering translations at OCR coordinates.
- DeskTranslate implementation points:
  - `android/app/src/main/java/com/uniquecasper/desktranslate/capture/CaptureService.kt`
  - `android/app/src/main/java/com/uniquecasper/desktranslate/overlay/TranslatedRegion.kt`
  - `android/app/src/main/java/com/uniquecasper/desktranslate/overlay/TranslationOverlay.kt`
- Current limit: the overlay is line-aligned and uses sampled background/text colors; scene-specific perspective, animation, and complex game backgrounds still need physical-device tuning.

## 3. AidanPark/screen-translator — targeted recognition and fixed-area design

- Repository: https://github.com/AidanPark/screen-translator
- Referenced source snapshot: commit `8717cf0`, dated 2026-09-23.
- License at that snapshot: Apache License 2.0.
- License change: later upstream revisions use PolyForm Noncommercial 1.0.0 (the license change is recorded in upstream commit `6479d5c`, dated 2026-09-25). DeskTranslate does not use source from those later revisions.
- Relevant concepts: selecting a target region, retrying weak OCR in a context crop, and keeping a stable translation target.
- DeskTranslate implementation points:
  - `android/app/src/main/java/com/uniquecasper/desktranslate/ocr/RegionCropper.kt`
  - `android/app/src/main/java/com/uniquecasper/desktranslate/MainActivity.kt` (stable-text debounce and bounded repeat interval)
- Current limit: low-confidence crop retry and stable-screen translation are present. User-drawn fixed-area pinning is still a future feature.

## Reuse and license handling

This branch uses design concepts and independently written equivalents, not copied source files. Therefore it does not incorporate the upstream projects as build dependencies and does not redistribute their source. If future work copies or adapts any upstream source, the exact source commit, its LICENSE and NOTICE files, copyright holders, and all applicable third-party dependency/model licenses must be carried into the repository before that code is merged.

TextGrab also bundles references to Google ML Kit SDKs/models under Google's own terms; this repository uses ML Kit dependencies directly and does not copy TextGrab's bundled SDK or model files.
