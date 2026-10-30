"""Read-only contextual retrieval for explicitly saved vocabulary.

The lookup never writes to the store, changes the approved glossary, or sends
saved entries to a provider. Results are restricted to one language pair.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from desktranslate.context import contains_term, folded
from desktranslate.vocabulary import MAX_ENTRIES, MAX_LIST_LIMIT, VocabularyEntry, VocabularyStore

DEFAULT_RESULT_LIMIT = 24
DEFAULT_RESULT_BYTES = 1_800


@dataclass(frozen=True, slots=True)
class VocabularyMatch:
    """A saved entry and the reason it was considered relevant."""

    entry: VocabularyEntry
    matched_current_text: bool


class VocabularyLookup:
    """Find saved source terms in current/recent text without mutating storage."""

    def __init__(self, store: VocabularyStore) -> None:
        self._store = store

    def relevant(
        self,
        text: str,
        source_language: str,
        target_language: str,
        *,
        recent_sources: tuple[str, ...] = (),
        limit: int = DEFAULT_RESULT_LIMIT,
        max_bytes: int = DEFAULT_RESULT_BYTES,
    ) -> tuple[VocabularyMatch, ...]:
        """Return bounded, language-pair-aware matches; current text ranks first.

        The complete bounded collection is scanned in pages, so older saved
        entries are not silently excluded by the database's newest-first page.
        """
        if not isinstance(text, str):
            raise ValueError("Lookup text must be text.")
        if type(limit) is not int or not 1 <= limit <= DEFAULT_RESULT_LIMIT:
            raise ValueError(f"Limit must be between 1 and {DEFAULT_RESULT_LIMIT}.")
        if type(max_bytes) is not int or not 1 <= max_bytes <= DEFAULT_RESULT_BYTES:
            raise ValueError(f"Byte budget must be between 1 and {DEFAULT_RESULT_BYTES}.")
        if not isinstance(recent_sources, tuple) or any(
            not isinstance(item, str) for item in recent_sources
        ):
            raise ValueError("Recent sources must be a tuple of text values.")

        current = folded(text)
        recent = folded("\\n".join(recent_sources[-2:]))
        matches: list[VocabularyMatch] = []
        offset = 0
        while offset < MAX_ENTRIES:
            page = self._store.list_entries(
                limit=MAX_LIST_LIMIT,
                offset=offset,
                source_language=source_language,
                target_language=target_language,
            )
            if not page:
                break
            for entry in page:
                term = folded(entry.source)
                in_current = bool(current) and contains_term(current, term)
                if not in_current and (not recent or not contains_term(recent, term)):
                    continue
                matches.append(VocabularyMatch(entry, in_current))
            offset += len(page)
            if len(page) < MAX_LIST_LIMIT:
                break

        matches.sort(
            key=lambda match: (
                not match.matched_current_text,
                -len(match.entry.source),
                -match.entry.id,
            )
        )
        result: list[VocabularyMatch] = []
        used = 0
        for match in matches:
            size = len(
                json.dumps(
                    [match.entry.source, match.entry.translation],
                    ensure_ascii=False,
                ).encode("utf-8")
            )
            if len(result) >= limit or used + size > max_bytes:
                continue
            result.append(match)
            used += size
        return tuple(result)
