"""Safe, explicit CSV exchange for saved vocabulary (Anki-compatible fields)."""

from __future__ import annotations

import csv
import io
import unicodedata
from collections.abc import Iterable

from desktranslate.languages import REGISTRY
from desktranslate.vocabulary import (
    MAX_ENTRIES,
    MAX_NOTE_BYTES,
    MAX_NOTE_CHARS,
    MAX_SOURCE_BYTES,
    MAX_SOURCE_CHARS,
    MAX_TRANSLATION_BYTES,
    MAX_TRANSLATION_CHARS,
    VocabularyEntry,
)

MAX_EXPORT_BYTES = 24 * 1024 * 1024
_REJECTED_CATEGORIES = frozenset({"Cc", "Zl", "Zp"})
_BIDI_CONTROLS = frozenset("\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")
_HEADER = "#separator:Comma\n#html:false\n#columns:Front,Back,SourceLanguage,TargetLanguage,Notes\n"


def _validate_text(value: object, label: str, max_chars: int, max_bytes: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text.")
    if len(value) > max_chars or len(value.encode("utf-8")) > max_bytes:
        raise ValueError(f"{label} exceeds the vocabulary size limit.")
    if any(
        unicodedata.category(char) in _REJECTED_CATEGORIES or char in _BIDI_CONTROLS
        for char in value
    ):
        raise ValueError(f"{label} contains unsupported control characters.")
    # Refuse formula-like cells rather than changing the user's vocabulary.
    # This keeps exports safe to open in spreadsheet software as well as Anki.
    if value.lstrip().startswith(("=", "+", "-", "@")):
        raise ValueError(
            f"{label} begins with a spreadsheet formula marker. "
            "Edit that saved term before exporting it."
        )
    return value


def _validate_note(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("Personal note must be text.")
    if len(value) > MAX_NOTE_CHARS or len(value.encode("utf-8")) > MAX_NOTE_BYTES:
        raise ValueError("Personal note exceeds the saved vocabulary size limit.")
    if any(
        (unicodedata.category(char) == "Cc" and char not in {"\\n", "\\t"})
        or char in {"\\u202a", "\\u202b", "\\u202c", "\\u202d", "\\u202e", "\\u2066", "\\u2067", "\\u2068", "\\u2069"}
        or unicodedata.category(char) in {"Zl", "Zp"}
        for char in value
    ):
        raise ValueError("Personal note contains unsupported control characters.")
    if value.lstrip().startswith(("=", "+", "-", "@")):
        raise ValueError(
            "Personal note begins with a spreadsheet formula marker. Edit it before exporting."
        )
    return value


def _csv_row(values: tuple[str, ...]) -> str:
    # Formula-like cells are rejected by _validate_text before reaching this
    # writer. CSV quoting is still required for commas, quotes and Unicode text.
    buffer = io.StringIO(newline="")
    csv.writer(buffer, lineterminator="\n").writerow(values)  # nosemgrep
    return buffer.getvalue()


def export_anki_csv(entries: Iterable[VocabularyEntry]) -> str:
    """Export saved terms as UTF-8 CSV with Anki-friendly Front/Back fields.

    Anki's text-import metadata names the columns. Language codes are extra
    fields so one export can safely contain multiple language pairs.
    Spaced-repetition scheduling metadata is intentionally not exported.
    The caller must invoke this only after an explicit user action.
    """
    chunks = [_HEADER]
    size = len(_HEADER.encode("utf-8"))
    for count, entry in enumerate(entries, start=1):
        if count > MAX_ENTRIES:
            raise ValueError("Too many vocabulary entries for one export.")
        if not isinstance(entry, VocabularyEntry):
            raise ValueError("The vocabulary export contains an invalid entry.")

        source = _validate_text(entry.source, "Source term", MAX_SOURCE_CHARS, MAX_SOURCE_BYTES)
        translation = _validate_text(
            entry.translation,
            "Translation",
            MAX_TRANSLATION_CHARS,
            MAX_TRANSLATION_BYTES,
        )
        if (
            not isinstance(entry.source_language, str)
            or entry.source_language not in REGISTRY
            or entry.source_language == "auto"
        ):
            raise ValueError("The export contains an unsupported source language.")
        if (
            not isinstance(entry.target_language, str)
            or entry.target_language not in REGISTRY
            or entry.target_language == "auto"
        ):
            raise ValueError("The export contains an unsupported target language.")

        note = _validate_note(entry.note)
        row = _csv_row((source, translation, entry.source_language, entry.target_language, note))
        size += len(row.encode("utf-8"))
        if size > MAX_EXPORT_BYTES:
            raise ValueError("The export is too large. Apply a language filter and try again.")
        chunks.append(row)

    return "".join(chunks)
