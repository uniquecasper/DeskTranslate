from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from desktranslate.vocabulary import VocabularyStore
from desktranslate.vocabulary_review import (
    VocabularyReviewError,
    VocabularyReviewStore,
)

pytestmark = pytest.mark.filterwarnings("error")


@pytest.fixture
def stores(tmp_path):
    vocabulary = VocabularyStore(tmp_path / "vocabulary.sqlite3")
    review = VocabularyReviewStore(vocabulary.path)
    return vocabulary, review


def test_new_words_are_due_without_changing_existing_vocabulary_rows(stores):
    vocabulary, review = stores
    first = vocabulary.add("hello", "merhaba", "en", "tr")
    second = vocabulary.add("world", "dünya", "en", "tr")

    due = review.due_entries()

    assert [item.entry.id for item in due] == [first.id, second.id]
    assert review.due_count() == 2
    assert vocabulary.count() == 2
    assert review.state(first.id) is None


def test_good_rating_schedules_first_review_for_one_day(stores):
    vocabulary, review = stores
    entry = vocabulary.add("hello", "merhaba", "en", "tr")
    now = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)

    state = review.review(entry.id, "good", now=now)

    assert state.interval_days == 1
    assert state.repetitions == 1
    assert state.lapses == 0
    assert state.ease == 2.5
    assert datetime.fromisoformat(state.due_at) == now + timedelta(days=1)
    assert review.due_count(now=now) == 0
    assert review.due_count(now=now + timedelta(days=1)) == 1


def test_again_resets_learning_streak_and_retries_in_ten_minutes(stores):
    vocabulary, review = stores
    entry = vocabulary.add("again", "tekrar", "en", "tr")
    now = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)

    review.review(entry.id, "good", now=now)
    state = review.review(entry.id, "again", now=now + timedelta(hours=1))

    assert state.repetitions == 0
    assert state.lapses == 1
    assert state.ease == 2.3
    assert datetime.fromisoformat(state.due_at) == now + timedelta(hours=1, minutes=10)


def test_hard_good_easy_change_interval_and_ease_as_expected(stores):
    vocabulary, review = stores
    entry = vocabulary.add("review", "tekrar", "en", "tr")
    now = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)

    hard = review.review(entry.id, "hard", now=now)
    assert hard.interval_days == 1
    assert hard.repetitions == 1
    assert hard.ease == 2.35

    good = review.review(entry.id, "good", now=now + timedelta(days=1))
    assert good.interval_days == 3
    assert good.repetitions == 2

    easy = review.review(entry.id, "easy", now=now + timedelta(days=4))
    assert easy.interval_days == 9
    assert easy.repetitions == 3
    assert easy.ease == 2.5


def test_review_state_survives_store_reopen(stores):
    vocabulary, review = stores
    entry = vocabulary.add("persistent", "kalıcı", "en", "tr")
    expected = review.review(entry.id, "good")
    reopened = VocabularyReviewStore(vocabulary.path)

    assert reopened.state(entry.id) == expected
    assert vocabulary.get(entry.id) == entry


def test_deleted_vocabulary_is_not_left_in_review_queue(stores):
    vocabulary, review = stores
    entry = vocabulary.add("remove", "sil", "en", "tr")
    review.review(entry.id, "good")

    assert vocabulary.delete(entry.id)
    assert review.due_count() == 0
    assert review.due_entries() == []


def test_review_rejects_unknown_words_ratings_and_naive_timestamps(stores):
    vocabulary, review = stores
    entry = vocabulary.add("valid", "geçerli", "en", "tr")

    with pytest.raises(ValueError, match="Again"):
        review.review(entry.id, "unknown")
    with pytest.raises(ValueError, match="timezone"):
        review.review(entry.id, "good", now=datetime(2026, 11, 1))
    with pytest.raises(ValueError, match="no longer exists"):
        review.review(entry.id + 100, "good")


def test_review_batch_limit_is_bounded(stores):
    vocabulary, review = stores
    vocabulary.add("one", "bir", "en", "tr")

    with pytest.raises(ValueError, match="limit"):
        review.due_entries(limit=101)


def test_review_table_creation_preserves_version_one_database(tmp_path):
    path = tmp_path / "vocabulary.sqlite3"
    vocabulary = VocabularyStore(path)
    entry = vocabulary.add("kept", "korundu", "en", "tr")
    review = VocabularyReviewStore(path)

    connection = sqlite3.connect(path)
    try:
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    finally:
        connection.close()

    assert version == 1
    assert "vocabulary_entries" in tables
    assert "vocabulary_review_state" in tables
    assert vocabulary.get(entry.id) == entry
    assert review.due_count() == 1


def test_malformed_existing_review_table_is_rejected_without_repair(tmp_path):
    path = tmp_path / "vocabulary.sqlite3"
    VocabularyStore(path)
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE vocabulary_review_state (entry_id INTEGER, secret TEXT)")
    connection.commit()
    connection.close()
    before = path.read_bytes()

    with pytest.raises(VocabularyReviewError, match="expected schema"):
        VocabularyReviewStore(path)

    assert path.read_bytes() == before

def test_review_connection_enables_secure_delete_and_delete_is_atomic(stores):
    vocabulary, review = stores
    entry = vocabulary.add("erase", "sil", "en", "tr")
    initial = review.review(entry.id, "good")

    connection = review._connect()
    try:
        assert connection.execute("PRAGMA secure_delete").fetchone()[0] == 1
        connection.close()
    finally:
        connection.close()

    # A failed review-state deletion must roll back the vocabulary deletion too.
    blocker = sqlite3.connect(vocabulary.path)
    try:
        blocker.execute(
            """
            CREATE TRIGGER block_review_state_delete
            BEFORE DELETE ON vocabulary_review_state
            BEGIN
                SELECT RAISE(ABORT, 'blocked review-state delete');
            END
            """
        )
        blocker.commit()
    finally:
        blocker.close()

    with pytest.raises(VocabularyReviewError):
        review.delete_entry(entry.id)

    assert vocabulary.get(entry.id) == entry
    assert review.state(entry.id) == initial
