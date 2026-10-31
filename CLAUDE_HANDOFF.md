# Active assignment — DeskTranslate 2.0.1 qualification and integration

Updated: 2026-10-31

**This is the active project handoff.** The Windows 2.0.1 candidate and the security remediation must be integrated and qualified together.

- Repository: `uniquecasper/DeskTranslate`
- Candidate branch: `claude/windows-installer-2-0-1`
- Security remediation branch: `fix/codacy-security-remediation`
- Pull requests: [#4](https://github.com/uniquecasper/DeskTranslate/pull/4) (already merged), [#5](https://github.com/uniquecasper/DeskTranslate/pull/5), [#6](https://github.com/uniquecasper/DeskTranslate/pull/6)
- Active scope: merge the security remediation into the Windows 2.0.1 candidate, qualify the exact candidate, then merge the completed PR into `main`.
- Do not create a stable tag or publish a 2.0.1 release as part of candidate qualification.

## Current acceptance requirements

1. Keep the PR #6 SQL parameterization, runtime assertion replacements, executable-launch policy, privacy-scan trust boundary, CI Codacy evidence capture and documentation.
2. Keep the PR #5 application/manifest version at 2.0.1.
3. Download the official DeskTranslate v2.0.0 installer and verify SHA-256
   `2c2aab018c7e34b38fe4b04f3ffb099c6707fbd63d14dbd21546effe43443fe5` before running it.
4. Prove the installed previous executable and uninstall metadata both identify version 2.0.0, then upgrade to 2.0.1 and verify settings/models remain unchanged.
5. Run the 7,200-second steady and 1,800-second chaos endurance workloads on the exact packaged candidate. Validate version, Python runtime, source/assets, harness hash, completion, resource qualification and worker cleanup.
6. Keep stable-release evidence separate. The existing manual qualification and unsigned approval describe v2.0.0 and must not be reused for v2.0.1.
7. Preserve the distinction between hosted offscreen qualification and native consumer-PC checks that remain NOT TESTED.

## Responsibility and merge policy

Project coordination, repository edits, evidence review and PR integration are performed directly against the connected GitHub repository. No external coding assistant is required for this handoff.

Merge only after the candidate branch's Windows quality workflow and full release-candidate qualification workflow have succeeded on the final combined commit. Merge PR #5 with a merge commit so the PR #6 history remains reachable; then verify GitHub records PR #6 as merged. PR #4 is already merged.

The upstream v2.0.0 release asset is the only approved previous-installer fixture. Do not run a downloaded installer unless the SHA-256 matches the value above.

## Evidence reporting

Record exact commit SHAs, workflow run IDs, artifact digests, test counts and limitations. Do not call skipped or untested checks passed. An internal qualification artifact is not a stable release.

---

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

## Responsibility split and stage gate

- **ChatGPT (project coordination, non-coding):** owns feature scope, product requirements, architecture/branch sequencing, privacy and acceptance criteria, non-code documentation, handoff notes for Claude Code, PR/check-status tracking, and review of reported test results/diffs. It must not author or edit application implementation code or test code going forward.
- **Claude Code (implementation):** owns application code, test code, code-level fixes, and implementation-specific validation. It must read this handoff and `CLAUDE.md` before each task, work only on the assigned feature branch, and report exact commands/results without claiming unrun checks.
- **User/maintainer:** decides when to hand a task to Claude Code and whether changes are accepted/merged. Never merge to `main` automatically.
- When the non-coding scope, requirements, branch/task, and acceptance criteria are ready, ChatGPT tells the user explicitly: **“Claude’un sırası geldi”** and provides a focused copy/paste task for Claude Code.
- The next Claude task is **not** the contextual lookup implementation yet. First Claude should review and verify the existing storage foundation in `claude/01-vocabulary-storage`, address any code-level defects, and run the focused tests plus the repository validation available to it. After results are reviewed, ChatGPT will prepare the next task/branch handoff.

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
