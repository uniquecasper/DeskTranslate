"""Safe, explicit CSV exchange for saved vocabulary (Anki-compatible fields)."""

from __future__ import annotations

import csv
import io
import unicodedata
from collections.abc import Iterable

from desktranslate.languages import REGISTRY
from desktranslate.vocabulary import (
    MAX_ENTRIES,
    MAX_SOURCE_BYTES,
    MAX_SOURCE_CHARS,
    MAX_TRANSLATION_BYTES,
    MAX_TRANSLATION_CHARS,
    VocabularyEntry,
)

MAX_EXPORT_BYTES = 24 * 1024 * 1024
_HEADER = ("Front", "Back", "SourceLanguage", "TargetLanguage")


def _validate_text(value: object, label: str, max_chars: int, max_bytes: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text.")
    if len(value) > max_chars or len(value.encode("utf-8")) > max_bytes:
        raise ValueError(f"{label} exceeds the vocabulary size limit.")
    if any(unicodedata.category(char).startswith("C") for char in value):
        raise ValueError(f"{label} contains unsupported control characters.")
    # Refuse formula-like cells rather than changing the user's vocabulary.
    # This keeps exports safe to open in spreadsheet software as well as Anki.
    if value.lstrip().startswith(("=", "+", "-", "@")):
        raise ValueError(
            f"{label} begins with a spreadsheet formula marker. "
            "Edit that saved term before exporting, or use a non-spreadsheet format."
        )
    return value


def _csv_row(values: tuple[str, ...]) -> str:
    buffer = io.StringIO(newline="")
    csv.writer(buffer, lineterminator="\n").writerow(values)
    return buffer.getvalue()


def export_anki_csv(entries: Iterable[VocabularyEntry]) -> str:
    """Export saved terms as UTF-8 CSV with Anki-friendly Front/Back fields.

    Language codes are extra columns so one export can safely contain multiple
    language pairs. Spaced-repetition scheduling metadata is intentionally not
    exported. The caller must invoke this only after an explicit user action.
    """
    chunks = [_csv_row(_HEADER)]
    size = len(chunks[0].encode("utf-8"))
    count = 0

    for entry in entries:
        count += 1
        if count > MAX_ENTRIES:
            raise ValueError("Too many vocabulary entries for one export.")
        if not isinstance(entry, VocabularyEntry):
            raise ValueError("The vocabulary export contains an invalid entry.")

        source = _validate_text(
            entry.source, "Source term", MAX_SOURCE_CHARS, MAX_SOURCE_BYTES
        )
        translation = _validate_text(
            entry.translation,
            "Translation",
            MAX_TRANSLATION_CHARS,
            MAX_TRANSLATION_BYTES,
        )
        if entry.source_language not in REGISTRY or entry.source_language == "auto":
            raise ValueError("The export contains an unsupported source language.")
        if entry.target_language not in REGISTRY or entry.target_language == "auto":
            raise ValueError("The export contains an unsupported target language.")

        row = _csv_row((source, translation, entry.source_language, entry.target_language))
        size += len(row.encode("utf-8"))
        if size > MAX_EXPORT_BYTES:
            raise ValueError("The export is too large. Apply a language filter and try again.")
        chunks.append(row)

    return "".join(chunks)
