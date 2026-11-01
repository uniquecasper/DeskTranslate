# DeskTranslate 2.1.0

DeskTranslate 2.1 adds dictionary-backed word learning, safer translation around source code and spaced-repetition review.

## What's new

- Double-click a recognized source word to open its dictionary details.
- Prefer an exact saved vocabulary translation for the active language pair; otherwise request a translation for only the selected word or phrase.
- Optionally enrich English words with parts of speech, definitions and examples from the Free Dictionary API. Dictionary failures do not stop normal screen translation.
- Protect fenced code, inline code and high-confidence code-shaped lines from translation. Protected text is restored exactly, and malformed provider responses are rejected.
- Save approved words locally and review due entries with Again, Hard, Good and Easy scheduling.
- Keep vocabulary and review scheduling separate from screenshots, OCR transcripts, provider credentials and translation history.

## Windows release and verification

The release contains the Windows x64 installer, portable ZIP, matching library source archive, SBOMs, build provenance, SHA-256 manifest, Sigstore signature bundles and GitHub build attestations. The release pipeline runs the pinned Windows pre-deployment suite, packaged-runtime and installer checks, artifact privacy scan, two-hour steady endurance and thirty-minute fault endurance before publishing.

The executables are not Authenticode publisher-signed because no trusted publisher certificate is configured. Sigstore signatures and GitHub attestations provide verifiable build identity/provenance, but do not replace Windows publisher reputation; Windows may display an unknown-publisher or SmartScreen warning.

Physical interaction on the user's Windows device is not claimed by hosted CI.