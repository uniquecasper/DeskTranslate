# Vocabulary Learning — Implementation and Verification

Status: the base vocabulary store, read-only contextual lookup and Learning page are already on `main`. Spaced-repetition review is staged on `feature/desktranslate-2-1-srs-final`; it is not shipped until the stacked PR passes Windows CI, review and release qualification.

## User workflow

1. A translation result is visible.
2. The user selects a source term and the corresponding displayed translation.
3. The user chooses Save word and reviews or edits both values in a confirmation dialog.
4. The app saves the approved pair locally with its source and target language metadata.
5. The Learning page lists saved entries and supports language-pair filters, case-insensitive search, bounded paging and confirmed deletion.
6. The contextual lookup may find saved terms in current text or the two most recent source lines. It is read-only and does not mutate the approved glossary.

When the source language is configured as automatic detection, the save dialog requires the user to select the actual source language before enabling Save.

## Data and privacy contract

- Storage is local to the current user's DeskTranslate data directory in a dedicated SQLite file named `vocabulary.sqlite3`; it is separate from settings JSON and title profiles.
- Only fields the user intentionally saves are persisted: source term, translation, source language, target language and creation timestamp.
- Never persist screenshots, OCR frames, full dialogue/session transcripts, provider responses beyond the chosen term, API keys, endpoint credentials or diagnostic logs in the vocabulary database.
- Saving requires an explicit user action and review. No automatic learning from OCR or translation events occurs.
- The collection is not uploaded to a translation provider, imported into the approved glossary or included in profile exports.
- Language-pair filters keep separate learning sets isolated.
- Deletion requires confirmation.

## Implementation map

| Component | Responsibility |
|---|---|
| `src/desktranslate/vocabulary.py` | Bounded SQLite persistence and validation |
| `src/desktranslate/vocabulary_lookup.py` | Read-only matching against current and recent source text |
| `src/desktranslate/vocabulary_review.py` | Local review queue, due dates and interval scheduling |
| `src/desktranslate/ui/learning.py` | Learning page, explicit save dialog, filters, search, paging and delete |
| `src/desktranslate/ui/window.py` | Connects the Learning page to the main window and selected translation |
| `tests/test_vocabulary.py` | Storage, validation, Unicode and database behavior |
| `tests/test_vocabulary_lookup.py` | Language isolation, ranking, bounds and context matching |
| `tests/test_vocabulary_review.py` | Review scheduling, due queue, safe table creation and persistence |
| `tests/test_learning.py` | UI workflow and selection behavior |

## Verification matrix

| Area | Minimum check | Expected outcome |
|---|---|---|
| Persistence | Add, reload, count, delete | Data round-trips and only the selected entry is deleted |
| Unicode | Japanese, Korean, Turkish and accented Latin text | Exact text is preserved |
| Duplicate rows | Save the same source/translation pair twice | One stable row is returned |
| Alternate translations | Same source with another translation | Both remain reviewable |
| Language pairs | Same term in different source/target pairs | Results stay isolated under pair filters |
| Input bounds | Empty/control characters, overly long terms, invalid languages | Clear validation error, no row saved |
| Query bounds | Invalid limit/offset and invalid language filters | Validation error; no unbounded result set |
| Database migration | Fresh, current, newer, malformed schemas | Safe initialization or explicit error; no silent reset |
| Concurrency | Overlapping writes near the collection limit | Unique constraints hold; cap is never exceeded; errors are handled |
| Privacy | Inspect the database and logs after save | Only approved vocabulary fields exist; no secrets, frames or transcripts |
| Spaced repetition | Again, Hard, Good and Easy ratings | Due dates progress as specified; lapse count and ease factor update predictably |
| Legacy data | Open a version-1 vocabulary DB with existing saved entries | New review table is added without changing old vocabulary rows or schema version |
| Integration | Save from result, list/review, filter/search and delete via UI | Complete journey works without blocking the Qt event loop |
| Packaging | Installed and portable app data paths | Database stored under the expected user/portable data directory |

## Quality gates

The Windows CI workflow on pull requests runs the prescribed pre-deployment checks, portable build, frozen startup/runtime checks and artifact privacy scan. A successful persistence test alone is not proof of a complete UI workflow or native qualification on every Windows configuration.

Run focused tests with `python -m pytest -q tests/test_vocabulary.py tests/test_vocabulary_lookup.py tests/test_learning.py`, then run `python tools/validate.py --predeploy`. Report actual results only.

## Remaining qualification

The automated Windows CI covers the repository's pinned Windows runner and packaging gates. Native manual interaction on other Windows machines, screen scales and display configurations remains separate from CI qualification.
