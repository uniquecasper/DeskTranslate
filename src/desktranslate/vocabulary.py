"""Explicit, local persistence for user-saved vocabulary.

This module stores only term/translation pairs and language metadata. It never
captures OCR output or dialogue by itself; callers decide when to save an item.
"""

from __future__ import annotations

import sqlite3
import unicodedata
from collections.abc import Iterator
from contextlib import closing, contextmanager
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
DEFAULT_TIMEOUT_SECONDS = 5.0

_SQLITE_MAX_INT = 2**63 - 1
_TABLE = "vocabulary_entries"
_UNIQUE_COLUMNS = ("source_language", "target_language", "source", "translation")
# (name, declared type, NOT NULL, primary-key position) in table order.
_EXPECTED_COLUMNS = (
    ("id", "INTEGER", 0, 1),
    ("source", "TEXT", 1, 0),
    ("translation", "TEXT", 1, 0),
    ("source_language", "TEXT", 1, 0),
    ("target_language", "TEXT", 1, 0),
    ("created_at", "TEXT", 1, 0),
)
# Line/paragraph separators break the single-line contract; bidi embedding,
# override and isolate controls can make a saved term render as something else.
_REJECTED_CATEGORIES = frozenset({"Cc", "Zl", "Zp"})
_BIDI_CONTROLS = frozenset("\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")


class VocabularyStoreError(RuntimeError):
    """The vocabulary database is unusable or a SQLite/file-system call failed.

    Messages never contain saved terms. The original error is chained as the cause.
    """


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
    # Bound the work before normalizing; NFC changes length only by a small factor.
    if len(value) > max_chars * 4:
        raise ValueError(f"{label} is too large.")
    # Canonically equivalent spellings (e.g. precomposed vs combining accents) are one term.
    value = unicodedata.normalize("NFC", value).strip()
    if (
        not value
        or len(value) > max_chars
        or any(
            unicodedata.category(character) in _REJECTED_CATEGORIES or character in _BIDI_CONTROLS
            for character in value
        )
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


def _entry_id(value: object) -> int:
    if type(value) is not int or not 1 <= value <= _SQLITE_MAX_INT:
        raise ValueError("Vocabulary entry id must be a positive integer.")
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


def _schema_version(connection: sqlite3.Connection) -> int:
    version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if version > SCHEMA_VERSION:
        raise VocabularyStoreError(
            "The vocabulary database was created by a newer DeskTranslate version."
        )
    if version < 0:
        raise VocabularyStoreError("The vocabulary database has an invalid schema version.")
    return version


def _validate_schema(connection: sqlite3.Connection) -> None:
    """Refuse (never repair) a database whose table is not the expected one."""
    rows = connection.execute(
        'SELECT name, type, "notnull", pk FROM pragma_table_info(?)', (_TABLE,)
    ).fetchall()
    actual = tuple((r["name"], str(r["type"]).upper(), r["notnull"], r["pk"]) for r in rows)
    has_unique_key = any(
        tuple(
            column["name"]
            for column in connection.execute(
                "SELECT name FROM pragma_index_info(?) ORDER BY seqno", (index["name"],)
            )
        )
        == _UNIQUE_COLUMNS
        for index in connection.execute(
            'SELECT name FROM pragma_index_list(?) WHERE "unique"', (_TABLE,)
        )
    )
    table_sql_row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (_TABLE,)
    ).fetchone()
    table_sql = str(table_sql_row["sql"] or "") if table_sql_row is not None else ""
    normalized_sql = " ".join(table_sql.upper().split())
    has_expected_checks = (
        f"CHECK (LENGTH(SOURCE) BETWEEN 1 AND {MAX_SOURCE_CHARS})" in normalized_sql
        and f"CHECK (LENGTH(TRANSLATION) BETWEEN 1 AND {MAX_TRANSLATION_CHARS})" in normalized_sql
    )
    has_autoincrement = "ID INTEGER PRIMARY KEY AUTOINCREMENT" in normalized_sql

    expected_index = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index' AND name = ?",
        ("idx_vocabulary_language_pair",),
    ).fetchone()
    index_columns = (
        tuple(
            column["name"]
            for column in connection.execute(
                "SELECT name FROM pragma_index_info(?) ORDER BY seqno",
                ("idx_vocabulary_language_pair",),
            )
        )
        if expected_index is not None
        else ()
    )
    has_expected_index = index_columns == ("source_language", "target_language", "id")

    if (
        actual != _EXPECTED_COLUMNS
        or not has_unique_key
        or not has_expected_checks
        or not has_autoincrement
        or not has_expected_index
    ):
        raise VocabularyStoreError("The vocabulary database does not have the expected schema.")


class VocabularyStore:
    """SQLite-backed vocabulary owned by the local user's app-data directory.

    Pass a dedicated path such as data_dir() / "vocabulary.sqlite3".
    Each operation opens its own short-lived connection so calls from UI/job
    code do not share a mutable sqlite connection across threads.

    Failures of the database or file system surface as VocabularyStoreError;
    invalid caller input surfaces as ValueError. Saved text is never logged.
    """

    def __init__(self, path: Path | str, *, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.path = Path(path)
        self._timeout = timeout
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # isolation_level=None: transactions are explicit (BEGIN IMMEDIATE), never implicit.
        connection = sqlite3.connect(self.path, timeout=self._timeout, isolation_level=None)
        connection.row_factory = sqlite3.Row
        # Deleted vocabulary must not linger in free pages of the file.
        connection.execute("PRAGMA secure_delete = ON")
        return connection

    @contextmanager
    def _session(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        """Yield a connection; a write session is one atomic, exclusive-writer transaction.

        BEGIN IMMEDIATE takes the write lock before the first read, so a
        check-then-insert sequence cannot interleave with another writer. On an
        error the connection is closed without COMMIT, which rolls back.
        """
        try:
            with closing(self._connect()) as connection:
                if write:
                    connection.execute("BEGIN IMMEDIATE")
                yield connection
                if write:
                    connection.execute("COMMIT")
        except (sqlite3.Error, OSError) as error:
            raise VocabularyStoreError("The vocabulary database could not be accessed.") from error

    def _initialize(self) -> None:
        with self._session() as connection:
            if _schema_version(connection) == SCHEMA_VERSION:
                _validate_schema(connection)
                return
        with self._session(write=True) as connection:
            # Re-check under the write lock: another process may have initialized it.
            if _schema_version(connection) == SCHEMA_VERSION:
                _validate_schema(connection)
                return
            foreign = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' LIMIT 1"
            ).fetchone()
            if foreign is not None:
                # Version 0 with existing objects is some other application's database.
                raise VocabularyStoreError("The file is not a DeskTranslate vocabulary database.")
            connection.execute(
                """
                CREATE TABLE vocabulary_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL CHECK (length(source) BETWEEN 1 AND 500),
                    translation TEXT NOT NULL CHECK (length(translation) BETWEEN 1 AND 2000),
                    source_language TEXT NOT NULL,
                    target_language TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE (source_language, target_language, source, translation)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX idx_vocabulary_language_pair
                ON vocabulary_entries (source_language, target_language, id DESC)
                """
            )
            connection.execute("PRAGMA user_version = 1")

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
        key = (source_language, target_language, source, translation)

        with self._session(write=True) as connection:
            existing = connection.execute(
                """
                SELECT * FROM vocabulary_entries
                WHERE source_language = ? AND target_language = ?
                    AND source = ? AND translation = ?
                """,
                key,
            ).fetchone()
            if existing is not None:
                return _entry(existing)

            count = int(connection.execute("SELECT COUNT(*) FROM vocabulary_entries").fetchone()[0])
            if count >= MAX_ENTRIES:
                raise ValueError("The saved vocabulary limit has been reached.")

            cursor = connection.execute(
                """
                INSERT INTO vocabulary_entries (
                    source_language, target_language, source, translation, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (*key, created_at),
            )
            row = connection.execute(
                "SELECT * FROM vocabulary_entries WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
            if row is None:
                raise VocabularyStoreError("The saved vocabulary entry could not be read back.")
            return _entry(row)

    def get(self, entry_id: int) -> VocabularyEntry | None:
        entry_id = _entry_id(entry_id)
        with self._session() as connection:
            row = connection.execute("SELECT * FROM vocabulary_entries WHERE id = ?", (entry_id,)).fetchone()
            return _entry(row) if row is not None else None

    def list_entries(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        source_language: str | None = None,
        target_language: str | None = None,
    ) -> list[VocabularyEntry]:
        """Newest first. An offset past the end returns an empty list."""
        if type(limit) is not int or not 1 <= limit <= MAX_LIST_LIMIT:
            raise ValueError(f"Limit must be between 1 and {MAX_LIST_LIMIT}.")
        if type(offset) is not int or not 0 <= offset <= MAX_ENTRIES:
            raise ValueError(f"Offset must be an integer between 0 and {MAX_ENTRIES}.")
        source_language = (
            _language(source_language, "Source language") if source_language is not None else None
        )
        target_language = (
            _language(target_language, "Target language") if target_language is not None else None
        )

        with self._session() as connection:
            if source_language is not None and target_language is not None:
                rows = connection.execute(
                    """
                    SELECT * FROM vocabulary_entries
                    WHERE source_language = ? AND target_language = ?
                    ORDER BY id DESC LIMIT ? OFFSET ?
                    """,
                    (source_language, target_language, limit, offset),
                ).fetchall()
            elif source_language is not None:
                rows = connection.execute(
                    """
                    SELECT * FROM vocabulary_entries
                    WHERE source_language = ?
                    ORDER BY id DESC LIMIT ? OFFSET ?
                    """,
                    (source_language, limit, offset),
                ).fetchall()
            elif target_language is not None:
                rows = connection.execute(
                    """
                    SELECT * FROM vocabulary_entries
                    WHERE target_language = ?
                    ORDER BY id DESC LIMIT ? OFFSET ?
                    """,
                    (target_language, limit, offset),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM vocabulary_entries
                    ORDER BY id DESC LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                ).fetchall()
            return [_entry(row) for row in rows]

    def delete(self, entry_id: int) -> bool:
        entry_id = _entry_id(entry_id)
        with self._session(write=True) as connection:
            cursor = connection.execute("DELETE FROM vocabulary_entries WHERE id = ?", (entry_id,))
            return cursor.rowcount > 0

    def count(self) -> int:
        with self._session() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM vocabulary_entries").fetchone()[0])
