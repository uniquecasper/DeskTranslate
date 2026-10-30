# Vocabulary Learning — Design and Verification Plan

Status: design/QA plan for the vocabulary-storage foundation. This document does **not** claim that vocabulary learning is integrated into the released desktop application.

## Scope

Add an optional learning workflow to DeskTranslate: the user explicitly saves a source term and its displayed translation, can review and delete saved entries, and may later use those entries as contextual learning aids. Existing approved glossary, recent dialogue context, and translation cache remain distinct systems.

## Data and privacy contract

- Storage is local to the current user's DeskTranslate data directory in a dedicated SQLite file; do not store the collection in settings JSON or title profiles by default.
- Only persist fields the user intentionally saves: source term, translation, source language, target language, and creation timestamp.
- Never persist screenshots, OCR frames, full dialogue/session transcripts, provider responses beyond the chosen term, API keys, endpoint credentials, or diagnostic logs in the vocabulary database.
- Saving must result from an explicit user action. No automatic learning from all OCR or translation events.
- Do not send the collection to a translation provider, import terms into the approved glossary, or export vocabulary as part of profiles without separate explicit product decisions.
- Filter by source/target language pair to avoid mixing learning sets. Imported/shared data needs a separate format and validation review before it is added.

## Expected user journey

1. A translation result is visible.
2. User selects the source term and corresponding translated term (the selection behavior must be designed around the current overlay/UI; never guess word alignment).
3. User explicitly chooses Save word.
4. The app validates both terms and the active language pair, then saves locally.
5. A learning panel lists entries with language-pair filters and bounded paging.
6. User can search/review and explicitly delete a selected entry.
7. Any contextual lookup only proposes saved entries relevant to the current term/context; it does not rewrite or mutate the official glossary automatically.

## Review points for the storage implementation

- The caller must pass a dedicated path such as `data_dir() / "vocabulary.sqlite3"`; the store must not be created in constructors that run on every app launch until integration and lifecycle decisions are made.
- Confirm the actual schema against both a fresh database and a pre-existing/malformed database. Newer schema versions must fail without destructive reset.
- Concurrency: check whether simultaneous calls can exceed the 10,000-entry limit or surface SQLite busy/locked errors; decide whether an immediate write transaction/retry policy is needed.
- Check runtime support for `datetime.UTC` against the project's supported interpreter range (Python 3.12+).
- Preserve the existing app test boundaries: temporary directories, offscreen Qt, fake credential vault, and loopback/mock-only network.

## Required verification matrix

| Area | Minimum check | Expected outcome |
|---|---|---|
| Persistence | Add, reload, count, delete | Data round-trips and only the selected entry is deleted |
| Unicode | Japanese, Korean, Turkish and accented Latin text | Exact text is preserved |
| Duplicate rows | Save same source/translation pair twice | One stable row is returned |
| Alternate translations | Same source with another translation | Both remain reviewable |
| Language pairs | Same term in different source/target pairs | Results stay isolated under pair filters |
| Input bounds | Empty/control characters, overly long terms, invalid languages | Clear validation error, no row saved |
| Query bounds | Invalid limit/offset and invalid language filters | Validation error; no unbounded result set |
| Database migration | Fresh, current, newer, malformed schemas | Safe initialization or explicit error; no silent reset |
| Concurrency | Overlapping writes near the collection limit | Unique constraints hold; cap is never exceeded; errors are handled |
| Privacy | Inspect the database and logs after save | Only approved vocabulary fields exist; no secrets, frames, or transcripts |
| Regression | Existing glossary/profile/context/settings tests | No behavior changes to existing features |
| Integration | Save from result, list/review, delete via UI | Complete journey works without blocking the Qt event loop |
| Packaging | Installed and portable app data paths | Database stored under the expected user/portable data directory |

## Quality gates

The repository's Windows CI workflow on pull requests runs the prescribed pre-deployment checks, portable build, frozen startup/runtime checks and artifact privacy scan. A draft PR may be used solely to run those existing gates without merging to `main`.

Locally, run `python -m pytest -q tests/test_vocabulary.py`, then `python tools/validate.py --predeploy` and the checks in `CONTRIBUTING.md`. Report actual results only. A successful persistence test alone is not proof of UI integration, Windows qualification, or feature completeness.

## Definition of done

- Explicit save, list/search/review and delete actions exist in the app.
- Data remains local and language-pair-aware, with bounded storage and safe failure behavior.
- No auto-save, silent glossary mutation, secret persistence, or unexpected provider upload.
- Focused and whole-suite tests pass; documented privacy behavior matches the implementation.
- User reviews the proposed change before any merge to `main`.
