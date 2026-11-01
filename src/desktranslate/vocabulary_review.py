"""Local spaced-repetition scheduling for explicitly saved vocabulary.

Review metadata is stored beside vocabulary entries in a separate table. The
existing vocabulary table and its schema version are left unchanged.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from desktranslate.vocabulary import VocabularyEntry

MAX_REVIEW_BATCH = 100
MAX_INTERVAL_DAYS = 3650
MIN_EASE = 1.3
_MAX_ENTRY_ID = 2**63 - 1
_TABLE = "vocabulary_review_state"
_COLUMNS = (
    ("entry_id", "INTEGER", 0, 1),
    ("due_at", "TEXT", 1, 0),
    ("interval_days", "REAL", 1, 0),
    ("ease", "REAL", 1, 0),
    ("repetitions", "INTEGER", 1, 0),
    ("lapses", "INTEGER", 1, 0),
    ("last_reviewed_at", "TEXT", 1, 0),
)
RATINGS = ("again", "hard", "good", "easy")


class VocabularyReviewError(RuntimeError):
    """A private review-state database could not be safely accessed."""


@dataclass(frozen=True, slots=True)
class ReviewState:
    entry_id: int
    due_at: str
    interval_days: float
    ease: float
    repetitions: int
    lapses: int
    last_reviewed_at: str


@dataclass(frozen=True, slots=True)
class ReviewItem:
    entry: VocabularyEntry
    state: ReviewState


def _utc_now(value: datetime | None = None) -> datetime:
    result = datetime.now(UTC) if value is None else value
    if not isinstance(result, datetime) or result.tzinfo is None:
        raise ValueError("Review timestamps must include a timezone.")
    return result.astimezone(UTC)


def _stamp(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def _entry_id(value: object) -> int:
    if type(value) is not int or not 1 <= value <= _MAX_ENTRY_ID:
        raise ValueError("Vocabulary entry id must be a positive integer.")
    return value


def _state(row: sqlite3.Row) -> ReviewState:
    return ReviewState(
        entry_id=int(row["entry_id"]),
        due_at=str(row["due_at"]),
        interval_days=float(row["interval_days"]),
        ease=float(row["ease"]),
        repetitions=int(row["repetitions"]),
        lapses=int(row["lapses"]),
        last_reviewed_at=str(row["last_reviewed_at"]),
    )


class VocabularyReviewStore:
    """Bounded review metadata backed by the existing local vocabulary database."""

    def __init__(self, vocabulary_path: Path | str, *, timeout: float = 5.0) -> None:
        self.path = Path(vocabulary_path)
        self.timeout = timeout
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=self.timeout, isolation_level=None)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _session(self, *, write: bool = False) -> Iterator[sqlite3.Connection]:
        try:
            with closing(self._connect()) as connection:
                if write:
                    connection.execute("BEGIN IMMEDIATE")
                yield connection
                if write:
                    connection.execute("COMMIT")
        except (sqlite3.Error, OSError) as error:
            raise VocabularyReviewError("Local review data could not be accessed.") from error

    def _initialize(self) -> None:
        if not self.path.is_file():
            raise VocabularyReviewError("Save a vocabulary word before opening review.")
        with self._session(write=True) as connection:
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (_TABLE,),
            ).fetchone()
            if exists is None:
                connection.execute(
                    """
                    CREATE TABLE vocabulary_review_state (
                        entry_id INTEGER PRIMARY KEY,
                        due_at TEXT NOT NULL,
                        interval_days REAL NOT NULL
                            CHECK (interval_days >= 0 AND interval_days <= 3650),
                        ease REAL NOT NULL CHECK (ease >= 1.3 AND ease <= 5.0),
                        repetitions INTEGER NOT NULL CHECK (repetitions >= 0),
                        lapses INTEGER NOT NULL CHECK (lapses >= 0),
                        last_reviewed_at TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    "CREATE INDEX idx_vocabulary_review_due "
                    "ON vocabulary_review_state (due_at, entry_id)"
                )
                return

            rows = connection.execute(
                'SELECT name, type, "notnull", pk FROM pragma_table_info(?)',
                (_TABLE,),
            ).fetchall()
            actual = tuple(
                (row["name"], str(row["type"]).upper(), row["notnull"], row["pk"]) for row in rows
            )
            index = connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' "
                "AND name = 'idx_vocabulary_review_due'"
            ).fetchone()
            index_columns = (
                tuple(
                    row["name"]
                    for row in connection.execute(
                        "SELECT name FROM pragma_index_info(?) ORDER BY seqno",
                        ("idx_vocabulary_review_due",),
                    )
                )
                if index is not None
                else ()
            )
            if actual != _COLUMNS or index_columns != ("due_at", "entry_id"):
                raise VocabularyReviewError(
                    "The local review database does not have the expected schema."
                )
            connection.execute(
                "DELETE FROM vocabulary_review_state "
                "WHERE entry_id NOT IN (SELECT id FROM vocabulary_entries)"
            )

    def state(self, entry_id: int) -> ReviewState | None:
        entry_id = _entry_id(entry_id)
        with self._session() as connection:
            row = connection.execute(
                "SELECT * FROM vocabulary_review_state WHERE entry_id = ?",
                (entry_id,),
            ).fetchone()
            return _state(row) if row is not None else None

    def due_count(self, *, now: datetime | None = None) -> int:
        current = _stamp(_utc_now(now))
        with self._session() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*)
                FROM vocabulary_entries AS vocabulary
                LEFT JOIN vocabulary_review_state AS review
                    ON review.entry_id = vocabulary.id
                WHERE review.entry_id IS NULL OR review.due_at <= ?
                """,
                (current,),
            ).fetchone()
            return int(row[0])

    def due_entries(
        self,
        *,
        limit: int = MAX_REVIEW_BATCH,
        now: datetime | None = None,
    ) -> list[ReviewItem]:
        if type(limit) is not int or not 1 <= limit <= MAX_REVIEW_BATCH:
            raise ValueError(f"Review limit must be between 1 and {MAX_REVIEW_BATCH}.")
        current = _utc_now(now)
        timestamp = _stamp(current)
        with self._session() as connection:
            rows = connection.execute(
                """
                SELECT
                    vocabulary.id, vocabulary.source, vocabulary.translation,
                    vocabulary.source_language, vocabulary.target_language,
                    vocabulary.created_at,
                    review.entry_id, review.due_at, review.interval_days,
                    review.ease, review.repetitions, review.lapses,
                    review.last_reviewed_at
                FROM vocabulary_entries AS vocabulary
                LEFT JOIN vocabulary_review_state AS review
                    ON review.entry_id = vocabulary.id
                WHERE review.entry_id IS NULL OR review.due_at <= ?
                ORDER BY CASE WHEN review.entry_id IS NULL THEN 0 ELSE 1 END,
                    review.due_at ASC, vocabulary.id ASC
                LIMIT ?
                """,
                (timestamp, limit),
            ).fetchall()

        result: list[ReviewItem] = []
        for row in rows:
            entry = VocabularyEntry(
                id=int(row["id"]),
                source=str(row["source"]),
                translation=str(row["translation"]),
                source_language=str(row["source_language"]),
                target_language=str(row["target_language"]),
                created_at=str(row["created_at"]),
            )
            if row["entry_id"] is None:
                state = ReviewState(
                    entry_id=entry.id,
                    due_at=timestamp,
                    interval_days=0.0,
                    ease=2.5,
                    repetitions=0,
                    lapses=0,
                    last_reviewed_at="",
                )
            else:
                state = _state(row)
            result.append(ReviewItem(entry, state))
        return result

    def review(
        self,
        entry_id: int,
        rating: str,
        *,
        now: datetime | None = None,
    ) -> ReviewState:
        entry_id = _entry_id(entry_id)
        if rating not in RATINGS:
            raise ValueError("Choose Again, Hard, Good or Easy.")
        current = _utc_now(now)
        timestamp = _stamp(current)

        with self._session(write=True) as connection:
            entry = connection.execute(
                "SELECT 1 FROM vocabulary_entries WHERE id = ?",
                (entry_id,),
            ).fetchone()
            if entry is None:
                raise ValueError("The saved vocabulary entry no longer exists.")
            row = connection.execute(
                "SELECT * FROM vocabulary_review_state WHERE entry_id = ?",
                (entry_id,),
            ).fetchone()

            previous = _state(row) if row is not None else ReviewState(
                entry_id=entry_id,
                due_at=timestamp,
                interval_days=0.0,
                ease=2.5,
                repetitions=0,
                lapses=0,
                last_reviewed_at="",
            )
            ease = previous.ease
            lapses = previous.lapses

            if rating == "again":
                interval_days = 10.0 / 1440.0
                repetitions = 0
                ease = max(MIN_EASE, ease - 0.2)
                lapses += 1
            elif rating == "hard":
                interval_days = (
                    1.0
                    if previous.repetitions == 0
                    else max(previous.interval_days * 1.2, previous.interval_days + 0.5)
                )
                repetitions = previous.repetitions + 1
                ease = max(MIN_EASE, ease - 0.15)
            elif rating == "good":
                interval_days = (
                    1.0
                    if previous.repetitions == 0
                    else 3.0
                    if previous.repetitions == 1
                    else max(1.0, round(previous.interval_days * ease))
                )
                repetitions = previous.repetitions + 1
            else:
                interval_days = (
                    4.0
                    if previous.repetitions == 0
                    else 6.0
                    if previous.repetitions == 1
                    else max(1.0, round(previous.interval_days * ease * 1.3))
                )
                repetitions = previous.repetitions + 1
                ease = min(5.0, ease + 0.15)

            interval_days = min(float(MAX_INTERVAL_DAYS), round(interval_days, 8))
            due_at = (
                _stamp(current + timedelta(minutes=10))
                if rating == "again"
                else _stamp(current + timedelta(days=interval_days))
            )
            connection.execute(
                """
                INSERT INTO vocabulary_review_state (
                    entry_id, due_at, interval_days, ease,
                    repetitions, lapses, last_reviewed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entry_id) DO UPDATE SET
                    due_at = excluded.due_at,
                    interval_days = excluded.interval_days,
                    ease = excluded.ease,
                    repetitions = excluded.repetitions,
                    lapses = excluded.lapses,
                    last_reviewed_at = excluded.last_reviewed_at
                """,
                (entry_id, due_at, interval_days, ease, repetitions, lapses, timestamp),
            )
            return ReviewState(entry_id, due_at, interval_days, ease, repetitions, lapses, timestamp)
