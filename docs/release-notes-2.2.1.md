# DeskTranslate 2.2.1

DeskTranslate 2.2.1 builds on the 2.2.0 release with reliability, configurable pipeline pacing and local-model setup improvements.

## What's new

- Recover live translation after stale OCR failures so a transient recognition failure does not leave the live session permanently stalled.
- Configure capture cadence and idle cadence independently, with separate capture, OCR-worker and provider timeouts. OCR worker timeout handling retires and replaces a stuck isolated worker within the documented recovery limits.
- Test a selected Ollama or LM Studio model with a short bundled sample using the selected source and target languages. The probe sends no screenshot or recognized screen text; it verifies generation only, not translation quality.
- Preserve existing configured local-server endpoints and keep model probing limited to providers that explicitly support local model discovery.
- Retain the 2.2.0 capture-efficiency, repeated-subtitle handling and stage-timing diagnostics, alongside the vocabulary, code-protection and spaced-repetition features from 2.1.

## Windows release and verification

The release contains the Windows x64 installer, portable ZIP, matching library source archive, SBOMs, build provenance, SHA-256 manifest, Sigstore signature bundles and GitHub build attestations. The release pipeline runs the pinned Windows pre-deployment suite, packaged-runtime and installer-upgrade checks, artifact privacy scan, two-hour steady endurance and thirty-minute fault endurance before publishing.

The executables are not Authenticode publisher-signed because no trusted publisher certificate is configured. Sigstore signatures and GitHub attestations provide verifiable build identity/provenance, but do not replace Windows publisher reputation; Windows may display an unknown-publisher or SmartScreen warning.

Physical interaction on the user's Windows device is not claimed by hosted CI.
