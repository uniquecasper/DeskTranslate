# DeskTranslate 2.2+ roadmap

This is the implementation backlog for the complete feature expansion agreed for DeskTranslate after 2.1.0. Features are delivered through small, independently testable pull requests. The `main` branch remains protected from direct changes.

## Existing capabilities to preserve

The following are already part of the 2.1.0 baseline and should be extended rather than rebuilt:

- One-shot and live region translation, monitor capture, application-client-region following, pause/resume/stop/retry.
- Global shortcuts, editable overlay, click-through/edit mode, themes and subtitle presets.
- Profiles, language-pair glossaries, bounded dialogue context, translation styles, dynamic provider/model discovery.
- Local OCR; keyless Google quick translation; cloud and local providers; OS credential vault.
- Session transcript (opt-in, in-memory and bounded), diagnostics and export preview.
- Selected-word dictionary lookup, explicit vocabulary saving, source-code preservation and spaced repetition.

Architecture and privacy constraints are documented in [architecture](architecture.md), [privacy](privacy.md), and [provider setup](provider-setup.md).

## A. Reliability and speed — first

- [x] Instrument capture → OCR → stabilization → provider → overlay latency. Expose the latest stage timings in the translation status tooltip and rolling percentiles in user-requested diagnostics; never store screen text.
- [x] Reduce redundant OCR/provider work using existing bounded mailboxes and caches; preserve cancellation and stale-result rejection. Regression coverage confirms repeated OCR during background motion does not duplicate provider calls for unchanged subtitles, while genuinely changed text is still translated.
- [ ] Ensure accepted live translations appear automatically and recover cleanly after provider/OCR failures. Remove dead or misleading controls.
- [ ] Add configurable capture/translation pacing and per-stage timeouts with safe defaults.
- [ ] Add regressions for moving subtitles, static text, blank transitions, overlay self-capture, window movement/minimize/occlusion, pause/resume and provider failures.

## B. Translation quality and control

- [ ] Add explicit source-language auto-detection across installed/selected OCR packs, with confidence and a manual override. Do not claim universal detection.
- [ ] Improve OCR correction using user-confirmed corrections and bounded contextual checks. Never silently rewrite uncertain text.
- [ ] Add robust bidirectional language switching while preserving language-pair-specific glossaries.
- [ ] Expand translation modes: game dialogue, subtitles, technical/software, literal and natural; preview custom instructions.
- [ ] Improve context controls: bounded recent dialogue, per-profile terminology/story notes, reset/disable controls and cross-profile leakage tests.
- [ ] Add optional user-configured provider failover with an explicit allowlist and local/cloud policy. No implicit cloud fallback; never transmit to an unapproved provider.
- [ ] Improve model capability checks and provider error explanations; expose safe retry/refresh actions.

## C. Learning system

- [ ] Improve selected-word cards with pronunciation/phonetics, audio playback where a usable system voice exists, part of speech, definitions, examples and context-specific meanings.
- [ ] Allow users to correct/edit saved meanings and attach their own examples/notes.
- [ ] Add Anki-friendly import/export (CSV/TSV first; APKG only if dependency and format are justified); preserve language pairs and review metadata safely.
- [ ] Add learning filters, due/overdue views, statistics and reversible bulk operations.
- [ ] Keep review scheduling local. Do not send vocabulary/review data to providers unless the user explicitly selects a word for lookup.

## D. History, backup and privacy controls

- [ ] Add persistent translation history **OFF by default**, with explicit opt-in, bounded retention/size, search, delete-one/delete-all, pause and per-profile exclusion.
- [ ] Keep history local; never store screenshots or credentials. Provide clear retention/export disclosures and tests for deletion and bounds.
- [ ] Add settings/profile/glossary/vocabulary backup and restore with preview, schema/version validation and atomic rollback.
- [ ] Exclude API keys and OS credential-vault material from backups. Exclude capture identity/coordinates by default; require fresh local selection after restore.
- [ ] Add a privacy settings page explaining what stays local and what each selected provider receives.

## E. Provider and cost tools

- [ ] Show request counts, characters/tokens where reliably measurable, latency and provider-returned usage.
- [ ] Show estimated cost only when exact model pricing metadata is available and timestamped. Otherwise show usage as unavailable; never invent costs.
- [ ] Add configurable per-session/day budget warnings and optional hard stop, with local-only counters.
- [ ] Add provider connection diagnostics and a clear test matrix. API key values must never appear in logs or diagnostics.

## F. Product finish and distribution

- [ ] Review overlay customization, shortcuts, accessible contrast, high-DPI behavior and compact layouts.
- [ ] Add update notices and a safe update path only after signature/attestation verification is designed and qualified.
- [ ] Update user documentation, privacy policy, changelog, screenshots and acceptance matrix for every shipped feature.
- [ ] Qualify portable and installer builds, upgrade/rollback, privacy scan, dependency audit, source-matched provenance, signatures and endurance before a new stable release.

## Release gates

- Windows CI: lint, formatting, type checks, full tests, dependency audit and packaging.
- Targeted regression tests for every touched subsystem.
- No claims of universal OCR accuracy, provider availability, free API quotas or exact costs without evidence.
- Persistent content features require opt-in, retention controls, deletion tests and documentation.
- Stable releases are produced only from exact merged source after all configured qualification gates pass.

## Implementation order

1. Reliability/latency and live overlay behavior.
2. Translation quality, language detection, correction and provider control.
3. Learning cards, audio and Anki exchange.
4. Persistent history and backup/restore.
5. Usage/cost controls and distribution polish.

This roadmap is a delivery plan, not a claim that these features are already implemented.