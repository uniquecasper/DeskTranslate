# Claude Handoff — Vocabulary Learning

Updated: 2026-10-29

## Repository and branch state

- Repository: `uniquecasper/DeskTranslate` (fork of DeskTranslate/DeskTranslate).
- Baseline: release 2.0.0 commit `533ad42d1064cb7a85a7d1051ca380f1e4613e8b`.
- Keep the user's `main` branch untouched during this feature.
- Planned work branches:
  1. `claude/01-vocabulary-storage` — local persistence and domain contract.
  2. `claude/02-contextual-lookup` — contextual lookup/relevance, using only explicitly saved entries.
  3. `claude/03-learning-panel` — user-facing review/learning panel and explicit save/delete actions.
  4. `claude/04-tests-and-docs` — end-to-end regressions, product/privacy documentation, and final integration.
- The branches were initially created at the same baseline commit; do not assume work exists on a later branch unless it is present in its tree/history.

## Product intent

Add an optional vocabulary-learning workflow to the existing screen translator. A user should be able to explicitly save a recognized term and its displayed translation, review their saved items, and later use them as a learning aid. This complements the current glossary; it must not silently replace or mutate the approved glossary.

## Existing architecture to preserve

- `src/desktranslate/context.py` contains ephemeral dialogue context and approved glossary terminology. The architecture documentation explicitly does not promise persistent learned vocabulary.
- `src/desktranslate/settings.py` owns the application data directory and validated settings persistence. Do not place a growing vocabulary database inside `settings.json`.
- `src/desktranslate/profiles.py` handles portable title profiles and glossary exchange. Vocabulary is a separate user-owned collection, not an implicit profile export.
- `src/desktranslate/ui/window.py` coordinates the main UI; keep domain/persistence logic out of the main window.
- `tests/conftest.py` establishes offscreen Qt, temporary app data, mocked credentials, and no real desktop/browser or external-network access for routine tests.

## Privacy and behavior requirements

- Persistence is opt-in by an explicit action; do not auto-save every OCR result or the conversation.
- Store only the selected term, its translated term, source/target language codes, and creation metadata at this stage.
- Keep data local in a dedicated SQLite file under the app data directory when later integrated. The database must not contain API keys, screenshots, full frames, logs, or unbounded dialogue history.
- Keep lookups language-pair-aware; avoid leaking vocabulary between unrelated language pairs.
- Bound text lengths and collection size; parameterize SQL; reject unknown/future database schemas instead of destructively recreating them.
- Never silently add saved words to the glossary or send the saved collection to a provider. Those behaviors require a separate, explicit design.

## Work in this branch

This branch introduces the Claude project instructions, this handoff, and a Qt-free SQLite storage foundation with tests. It does not yet integrate the store into the application UI or translation pipeline. The design and QA checklist is documented in [`docs/vocabulary-learning-plan.md`](docs/vocabulary-learning-plan.md).

Review notes before feature completion: the storage cap uses a count-then-insert flow, so concurrent writes near the 10,000-entry limit need a concurrency test; current schema initialization should be tested against malformed existing tables, not only a newer `user_version`. These are review/test follow-ups, not confirmed runtime failures. Local execution is unavailable in the present tool session; use the repository's Windows CI on a draft PR and inspect the actual run result.

## Next steps

1. Review this storage API and its tests; run them in a complete checkout.
2. Integrate a contextual lookup service in `claude/02-contextual-lookup` without changing approved glossary behavior.
3. Build the learning panel in `claude/03-learning-panel`, with explicit save/delete and clear empty/error states.
4. In `claude/04-tests-and-docs`, cover the real user journey, update `docs/privacy.md` and user-facing documentation, then run the full prescribed checks.
5. Use a draft PR if needed to exercise CI without merging. Ask the user to review the combined change before any merge to `main`.

## Definition of done

- Existing translation and glossary flows still behave as before.
- Vocabulary is local, bounded, language-pair-aware, and explicitly user-saved.
- Persistence and UI tests are offscreen and use temporary data.
- No credentials, screenshots, or automatic conversation history are persisted.
- Tests and validation results are reported accurately; unavailable Windows/native qualification remains a stated limitation.
