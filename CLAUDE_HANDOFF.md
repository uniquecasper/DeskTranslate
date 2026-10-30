# Active assignment — Windows 2.0.1 release candidate

Updated: 2026-10-31

**This is the active task for this branch.** The vocabulary-learning workstream documented below is paused and must not be continued as part of this assignment.

- Repository: `uniquecasper/DeskTranslate`
- Branch: `claude/windows-installer-2-0-1`
- Pull request: [#5](https://github.com/uniquecasper/DeskTranslate/pull/5)
- Scope: finish Windows 2.0.1 release-candidate qualification only. Do not work on Android/APK.
- Do not merge to `main`, create a release tag, or publish a release.

## Responsibility

- ChatGPT handles coordination, factual evidence review, release-status documentation and this handoff.
- Claude Code handles workflow/build/qualification implementation changes and code-level tests.
- The maintainer makes all merge, stable-promotion and unsigned-publication decisions.

## Verified previous installer

The official upstream GitHub release record for v2.0.0 lists:

- URL: https://github.com/DeskTranslate/DeskTranslate/releases/download/v2.0.0/DeskTranslate-2.0.0-Setup-x64.exe
- Expected SHA-256: `2c2aab018c7e34b38fe4b04f3ffb099c6707fbd63d14dbd21546effe43443fe5`

Download this exact asset, verify its SHA-256 before execution, and pass it to
`tools/qualify_installer.ps1 -PreviousInstaller`. Do not execute an unverified file.
The expected hash and qualification status are also recorded in
[`docs/windows-2.0.1-qualification-status.md`](docs/windows-2.0.1-qualification-status.md).

## Implementation task

1. Wire the verified previous installer into the release-candidate workflow and
   require a genuine 2.0.0-to-2.0.1 upgrade. Preserve/check user settings and
   existing models. A same-version reinstall is not an upgrade test.
2. Make the 7,200-second steady and 1,800-second fault/chaos endurance checks
   runnable for the exact 2.0.1 candidate. Record and validate version, source/assets,
   Python 3.12.15 and `tools/soak.py` hashes; incomplete or mismatched reports fail.
3. Fix the release-gate ordering. The current pre-deployment step invokes
   `stable_gate` before hosted endurance reports exist, and hosted report names
   differ from the filenames consumed by `stable_gate`. Design a safe staged flow:
   qualification build → all required evidence → exact-source/runtime evidence
   validation → stable gate → final artifact verification. Never reuse 2.0.0
   qualification/soak reports as 2.0.1 evidence.
4. Keep `docs/manual-qualification.json` truthful. Do not mark a gate true without
   matching evidence; leave unavailable physical display/DPI/media checks NOT TESTED.
5. Do not inherit the 2.0.0 unsigned-release approval. No publisher certificate is
   configured in the observed candidate run. Leave 2.0.1 unsigned stable approval
   unset unless the maintainer explicitly authorizes it. Never self-sign or claim
   publisher identity without a trusted certificate.

## Acceptance and reporting

- Existing 2.0.1 Windows CI, packaged startup, portable/installer qualification,
  SHA-256, SBOM, provenance and privacy checks remain required.
- Genuine previous-installer upgrade evidence is required.
- Both endurance workloads must complete and match the exact candidate source,
  runtime and harness hashes.
- Stable promotion must fail closed on missing, stale, false or mismatched evidence.
- Report changed files, exact commands, run IDs and actual results. Do not claim
  unrun tests passed.
- Keep PR #5 as a draft; do not merge, tag or publish.

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
