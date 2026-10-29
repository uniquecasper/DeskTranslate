"""Explicit, local persistence for user-saved vocabulary.

This module stores only term/translation pairs and language metadata. It never
captures OCR output or dialogue by itself; callers decide when to save an item.
"""

from __future__ import annotations

import sqlite3
import unicodedata
from contextlib import closing
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from desktranslate.languages import REGISTRY

SCHEMA_VERSION = 1
MAX_ENTRIES = 10_000
MAX_SOURCE_CHARS = 500
MAX_TRANSLATION_CHARS = 2_000
MAX_SOURCE_BYTES = 2_000
MAX_TRANSLATION_BYTES = 8_000
MAX_LIST_LIMIT = 500


@dataclass(frozen=True, slots=True)
class VocabularyEntry:
    """One term deliberately saved by the user."""

    id: int
    source: str
    translation: str
    source_language: str
    target_language: str
    created_at: str


def _text(value: object, label: str, max_chars: int, max_bytes: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text.")
    value = value.strip()
    if not value or len(value) > max_chars or any(
        unicodedata.category(character) == "Cc" for character in value
    ):
        raise ValueError(f"{label} must be non-empty, single-line text within the size limit.")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise ValueError(f"{label} contains invalid Unicode.") from None
    if len(encoded) > max_bytes:
        raise ValueError(f"{label} is too large.")
    return value


def _language(value: object, label: str) -> str:
    if not isinstance(value, str) or value not in REGISTRY or value == "auto":
        raise ValueError(f"{label} must be a supported, specific language code.")
    return value


def _entry(row: sqlite3.Row) -> VocabularyEntry:
    return VocabularyEntry(
        id=int(row["id"]),
        source=str(row["source"]),
        translation=str(row["translation"]),
        source_language=str(row["source_language"]),
        target_language=str(row["target_language"]),
        created_at=str(row["created_at"]),
    )


class VocabularyStore:
    """SQLite-backed vocabulary owned by the local user's app-data directory.

    Pass a dedicated path such as data_dir() / "vocabulary.sqlite3".
    Each operation opens its own short-lived connection so calls from UI/job
    code do not share a mutable sqlite connection across threads.
    """

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if version > SCHEMA_VERSION:
                raise RuntimeError(
                    "The vocabulary database was created by a newer DeskTranslate version."
                )
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS vocabulary_entries (
                        id INTEGER PRIMARY KEY,
                        source TEXT NOT NULL
                            CHECK (length(source) BETWEEN 1 AND 500),
                        translation TEXT NOT NULL
                            CHECK (length(translation) BETWEEN 1 AND 2000),
                        source_language TEXT NOT NULL,
                        target_language TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        UNIQUE (source_language, target_language, source, translation)
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_vocabulary_language_pair
                    ON vocabulary_entries (source_language, target_language, id DESC)
                    """
                )
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    def add(
        self,
        source: str,
        translation: str,
        source_language: str,
        target_language: str,
    ) -> VocabularyEntry:
        """Save a term, returning the existing row for an exact duplicate."""
        source = _text(source, "Source term", MAX_SOURCE_CHARS, MAX_SOURCE_BYTES)
        translation = _text(
            translation, "Translation", MAX_TRANSLATION_CHARS, MAX_TRANSLATION_BYTES
        )
        source_language = _language(source_language, "Source language")
        target_language = _language(target_language, "Target language")
        created_at = datetime.now(UTC).isoformat(timespec="seconds")

        with closing(self._connect()) as connection:
            with connection:
                existing = connection.execute(
                    """
                    SELECT * FROM vocabulary_entries
                    WHERE source_language = ? AND target_language = ?
                        AND source = ? AND translation = ?
                    """,
                    (source_language, target_language, source, translation),
                ).fetchone()
                if existing is not None:
                    return _entry(existing)

                count = int(
                    connection.execute("SELECT COUNT(*) FROM vocabulary_entries").fetchone()[0]
                )
                if count >= MAX_ENTRIES:
                    raise ValueError("The saved vocabulary limit has been reached.")

                connection.execute(
                    """
                    INSERT INTO vocabulary_entries (
                        source, translation, source_language, target_language, created_at
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT (source_language, target_language, source, translation)
                    DO NOTHING
                    """,
                    (source, translation, source_language, target_language, created_at),
                )
                row = connection.execute(
                    """
                    SELECT * FROM vocabulary_entries
                    WHERE source_language = ? AND target_language = ?
                        AND source = ? AND translation = ?
                    """,
                    (source_language, target_language, source, translation),
                ).fetchone()
                if row is None:
                    raise RuntimeError("The saved vocabulary entry could not be read back.")
                return _entry(row)

    def get(self, entry_id: int) -> VocabularyEntry | None:
        if type(entry_id) is not int or entry_id <= 0:
            raise ValueError("Vocabulary entry id must be a positive integer.")
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM vocabulary_entries WHERE id = ?", (entry_id,)
            ).fetchone()
            return _entry(row) if row is not None else None

    def list_entries(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        source_language: str | None = None,
        target_language: str | None = None,
    ) -> list[VocabularyEntry]:
        if type(limit) is not int or not 1 <= limit <= MAX_LIST_LIMIT:
            raise ValueError(f"Limit must be between 1 and {MAX_LIST_LIMIT}.")
        if type(offset) is not int or offset < 0:
            raise ValueError("Offset must be a non-negative integer.")
        clauses: list[str] = []
        params: list[str | int] = []
        if source_language is not None:
            clauses.append("source_language = ?")
            params.append(_language(source_language, "Source language"))
        if target_language is not None:
            clauses.append("target_language = ?")
            params.append(_language(target_language, "Target language"))
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""

        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM vocabulary_entries{where}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (*params, limit, offset),
            ).fetchall()
            return [_entry(row) for row in rows]

    def delete(self, entry_id: int) -> bool:
        if type(entry_id) is not int or entry_id <= 0:
            raise ValueError("Vocabulary entry id must be a positive integer.")
        with closing(self._connect()) as connection:
            with connection:
                cursor = connection.execute(
                    "DELETE FROM vocabulary_entries WHERE id = ?", (entry_id,)
                )
                return cursor.rowcount > 0

    def count(self) -> int:
        with closing(self._connect()) as connection:
            return int(
                connection.execute("SELECT COUNT(*) FROM vocabulary_entries").fetchone()[0]
            )
