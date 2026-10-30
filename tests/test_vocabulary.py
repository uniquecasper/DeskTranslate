import sqlite3
import threading
import time

import pytest

from desktranslate import vocabulary
from desktranslate.vocabulary import (
    MAX_LIST_LIMIT,
    SCHEMA_VERSION,
    VocabularyStore,
    VocabularyStoreError,
)


@pytest.fixture
def path(tmp_path):
    return tmp_path / "vocabulary.sqlite3"


@pytest.fixture
def store(path):
    return VocabularyStore(path)


def _user_version(path) -> int:
    connection = sqlite3.connect(path)
    try:
        return int(connection.execute("PRAGMA user_version").fetchone()[0])
    finally:
        connection.close()


def _tables(path) -> list[str]:
    connection = sqlite3.connect(path)
    try:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        return sorted(row[0] for row in rows)
    finally:
        connection.close()


# --- persistence, Unicode, duplicates -------------------------------------------------


def test_vocabulary_round_trip_preserves_unicode_and_uses_local_database(tmp_path):
    path = tmp_path / "nested" / "vocabulary.sqlite3"
    store = VocabularyStore(path)

    saved = store.add("兄さん", "a=b", "ja", "tr")

    assert path.is_file()
    assert store.get(saved.id) == saved
    assert saved.source == "兄さん"
    assert saved.translation == "a=b"
    assert saved.source_language == "ja"
    assert saved.target_language == "tr"
    assert saved.created_at.endswith("+00:00")
    assert store.count() == 1


def test_data_survives_reopening_the_store(path):
    saved = VocabularyStore(path).add("hello", "merhaba", "en", "tr")

    reopened = VocabularyStore(path)

    assert reopened.get(saved.id) == saved
    assert reopened.count() == 1


@pytest.mark.parametrize(
    ("source", "translation", "source_language", "target_language"),
    [
        ("日本語のテキスト", "Japonca metin", "ja", "tr"),
        ("한국어 단어", "Korece kelime", "ko", "tr"),
        ("İstanbul ığşçöü", "Istanbul", "tr", "en"),
        ("crème brûlée", "kremalı tatlı", "fr", "tr"),
        # Joiner/non-joiner are legitimate in Persian/Indic text and must stay accepted.
        ("می\u200cخواهم", "istiyorum", "ar", "tr"),
        ("🐱🐈", "kedi", "en", "tr"),
    ],
)
def test_unicode_text_is_preserved_exactly(
    store, source, translation, source_language, target_language
):
    saved = store.add(source, translation, source_language, target_language)

    assert store.get(saved.id).source == source
    assert store.get(saved.id).translation == translation


def test_surrounding_whitespace_and_canonical_equivalents_are_one_entry(store):
    composed = store.add("caf\u00e9", "kahve", "en", "tr")
    combining = store.add("cafe\u0301", "kahve", "en", "tr")
    padded = store.add("  caf\u00e9  ", "  kahve ", "en", "tr")

    assert combining.id == composed.id == padded.id
    assert composed.source == "caf\u00e9"
    assert store.count() == 1


def test_exact_duplicate_is_idempotent_but_different_translation_is_allowed(tmp_path):
    store = VocabularyStore(tmp_path / "vocabulary.sqlite3")

    first = store.add("猫", "kedi", "ja", "tr")
    duplicate = store.add("猫", "kedi", "ja", "tr")
    alternate = store.add("猫", "minnoş", "ja", "tr")

    assert duplicate.id == first.id
    assert alternate.id != first.id
    assert store.count() == 2


def test_sql_metacharacters_are_stored_as_text(store, path):
    hostile = "x'); DROP TABLE vocabulary_entries; --"

    saved = store.add(hostile, "y", "en", "tr")

    assert store.get(saved.id).source == hostile
    assert _tables(path) == ["vocabulary_entries"]


def test_database_holds_only_the_approved_vocabulary_fields(store, path):
    store.add("hello", "merhaba", "en", "tr")

    connection = sqlite3.connect(path)
    try:
        columns = [row[1] for row in connection.execute("PRAGMA table_info(vocabulary_entries)")]
    finally:
        connection.close()
    assert _tables(path) == ["vocabulary_entries"]
    assert columns == [
        "id",
        "source",
        "translation",
        "source_language",
        "target_language",
        "created_at",
    ]


# --- input validation -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "translation", "source_language", "target_language"),
    [
        (" ", "word", "en", "tr"),
        ("word", "", "en", "tr"),
        ("word\nline", "translation", "en", "tr"),
        ("word", "trans\r\nlation", "en", "tr"),
        ("a\tb", "translation", "en", "tr"),
        ("a\x00b", "translation", "en", "tr"),
        ("a\x85b", "translation", "en", "tr"),
        ("a\u2028b", "translation", "en", "tr"),
        ("a\u2029b", "translation", "en", "tr"),
        ("abc\u202edef", "translation", "en", "tr"),
        ("word", "abc\u2066def", "en", "tr"),
        ("lone\ud800surrogate", "translation", "en", "tr"),
        ("x" * 501, "translation", "en", "tr"),
        ("word", "x" * 2001, "en", "tr"),
        ("🐱" * 501, "translation", "en", "tr"),
        ("x" * 1_000_000, "translation", "en", "tr"),
        (None, "translation", "en", "tr"),
        (b"bytes", "translation", "en", "tr"),
        (123, "translation", "en", "tr"),
        ("word", "translation", "auto", "tr"),
        ("word", "translation", "en", "unknown"),
        ("word", "translation", "EN", "tr"),
        ("word", "translation", None, "tr"),
        ("word", "translation", "en", 7),
    ],
    ids=[
        "blank-source",
        "empty-translation",
        "newline-in-source",
        "crlf-in-translation",
        "tab-in-source",
        "nul-in-source",
        "c1-nel-in-source",
        "line-separator-u2028",
        "paragraph-separator-u2029",
        "bidi-override-in-source",
        "bidi-isolate-in-translation",
        "lone-surrogate",
        "source-501-chars",
        "translation-2001-chars",
        "source-501-astral-chars",
        "source-1m-chars",
        "source-none",
        "source-bytes",
        "source-int",
        "source-language-auto",
        "target-language-unknown",
        "source-language-uppercase",
        "source-language-none",
        "target-language-int",
    ],
)
def test_add_rejects_invalid_or_oversized_values(
    store, source, translation, source_language, target_language
):
    with pytest.raises(ValueError):
        store.add(source, translation, source_language, target_language)
    assert store.count() == 0


def test_values_exactly_at_the_size_limits_are_accepted(store):
    # Four-byte characters at the maximum length also sit exactly at the byte limits.
    source = "🐱" * vocabulary.MAX_SOURCE_CHARS
    translation = "🐈" * vocabulary.MAX_TRANSLATION_CHARS

    saved = store.add(source, translation, "en", "tr")

    assert store.get(saved.id).source == source
    assert len(store.get(saved.id).translation) == vocabulary.MAX_TRANSLATION_CHARS


# --- language pairs, listing, pagination ----------------------------------------------


def test_listing_filters_language_pair_and_applies_pagination(tmp_path):
    store = VocabularyStore(tmp_path / "vocabulary.sqlite3")
    store.add("hello", "merhaba", "en", "tr")
    store.add("cat", "kedi", "en", "tr")
    store.add("猫", "kedi", "ja", "tr")
    store.add("hola", "merhaba", "es", "tr")

    english = store.list_entries(source_language="en", target_language="tr")
    page = store.list_entries(limit=1, offset=1, source_language="en", target_language="tr")

    assert [entry.source for entry in english] == ["cat", "hello"]
    assert [entry.source for entry in page] == ["hello"]
    assert len(store.list_entries(target_language="tr")) == 4


def test_same_term_in_different_language_pairs_stays_isolated(store):
    to_turkish = store.add("chat", "kedi", "fr", "tr")
    to_german = store.add("chat", "Katze", "fr", "de")
    same_words_other_pair = store.add("chat", "kedi", "fr", "de")

    assert len({to_turkish.id, to_german.id, same_words_other_pair.id}) == 3
    assert [e.id for e in store.list_entries(source_language="fr", target_language="tr")] == [
        to_turkish.id
    ]
    assert {e.id for e in store.list_entries(source_language="fr", target_language="de")} == {
        to_german.id,
        same_words_other_pair.id,
    }
    assert [e.id for e in store.list_entries(source_language="en")] == []
    assert len(store.list_entries(target_language="de")) == 2


def test_pages_cover_every_entry_exactly_once_newest_first(store):
    ids = [store.add(f"word{i}", "t", "en", "tr").id for i in range(7)]

    pages = [store.list_entries(limit=3, offset=offset) for offset in (0, 3, 6)]

    assert [len(page) for page in pages] == [3, 3, 1]
    assert [entry.id for page in pages for entry in page] == list(reversed(ids))
    assert store.list_entries(limit=3, offset=7) == []
    assert store.list_entries(offset=vocabulary.MAX_ENTRIES) == []


@pytest.mark.parametrize(
    ("limit", "offset"),
    [
        (0, 0),
        (501, 0),
        (True, 0),
        (-1, 0),
        (1.5, 0),
        ("10", 0),
        (10, -1),
        (10, True),
        (10, 1.0),
        (10, vocabulary.MAX_ENTRIES + 1),
        (10, 2**63),
        (10, 2**64),
    ],
)
def test_list_rejects_invalid_pagination(store, limit, offset):
    with pytest.raises(ValueError):
        store.list_entries(limit=limit, offset=offset)


def test_list_accepts_the_largest_allowed_limit(store):
    store.add("a", "b", "en", "tr")

    assert len(store.list_entries(limit=MAX_LIST_LIMIT)) == 1


@pytest.mark.parametrize("language", ["auto", "unknown", "EN", "", 5])
def test_list_rejects_invalid_language_filters(store, language):
    with pytest.raises(ValueError):
        store.list_entries(source_language=language)
    with pytest.raises(ValueError):
        store.list_entries(target_language=language)


# --- deletion -------------------------------------------------------------------------


def test_delete_only_removes_requested_entry(tmp_path):
    store = VocabularyStore(tmp_path / "vocabulary.sqlite3")
    entry = store.add("hello", "merhaba", "en", "tr")

    assert store.delete(entry.id)
    assert not store.delete(entry.id)
    assert store.get(entry.id) is None
    assert store.count() == 0


def test_delete_leaves_other_entries_untouched(store):
    keep = store.add("keep", "tut", "en", "tr")
    drop = store.add("drop", "at", "en", "tr")

    assert store.delete(drop.id)

    assert store.get(keep.id) == keep
    assert store.count() == 1


@pytest.mark.parametrize("entry_id", [0, -1, True, "1", 1.0, None, 2**63, 2**64])
def test_get_and_delete_reject_invalid_ids(store, entry_id):
    with pytest.raises(ValueError):
        store.get(entry_id)
    with pytest.raises(ValueError):
        store.delete(entry_id)


def test_deleted_id_is_never_reused(store):
    first = store.add("one", "bir", "en", "tr")
    last = store.add("two", "iki", "en", "tr")
    store.delete(last.id)

    replacement = store.add("three", "uc", "en", "tr")

    # A UI still holding the old id must not be able to delete the new entry.
    assert replacement.id != last.id
    assert not store.delete(last.id)
    assert store.get(replacement.id) == replacement
    assert store.get(first.id) == first


def test_deleted_text_is_not_left_in_database_files(store, path):
    secret = "ZZ-unique-secret-term-ZZ"
    entry = store.add(secret, "ZZ-unique-secret-translation-ZZ", "en", "tr")

    store.delete(entry.id)

    for file in path.parent.iterdir():
        assert b"ZZ-unique-secret" not in file.read_bytes()


# --- collection limit -----------------------------------------------------------------


def _fill(store, count):
    for index in range(count):
        store.add(f"word{index}", "t", "en", "tr")


def test_limit_blocks_new_entries_but_not_duplicates_and_deletion_frees_space(store, monkeypatch):
    monkeypatch.setattr(vocabulary, "MAX_ENTRIES", 5)
    _fill(store, 5)

    with pytest.raises(ValueError, match="limit"):
        store.add("extra", "t", "en", "tr")
    assert store.count() == 5
    assert store.add("word0", "t", "en", "tr").source == "word0"  # existing row, not new
    assert store.count() == 5

    assert store.delete(store.list_entries(limit=1)[0].id)
    store.add("extra", "t", "en", "tr")
    assert store.count() == 5


def test_rejected_add_does_not_leave_a_write_lock_behind(store, path, monkeypatch):
    monkeypatch.setattr(vocabulary, "MAX_ENTRIES", 1)
    store.add("only", "t", "en", "tr")
    with pytest.raises(ValueError):
        store.add("extra", "t", "en", "tr")

    other = sqlite3.connect(path, timeout=0.2)
    try:
        other.execute("BEGIN IMMEDIATE")  # would raise "database is locked" if a lock leaked
        other.rollback()
    finally:
        other.close()


def _concurrent_adds(store, words):
    barrier = threading.Barrier(len(words))
    outcomes: list[str] = []
    lock = threading.Lock()

    def work(word):
        barrier.wait()
        try:
            store.add(word, "t", "en", "tr")
            outcome = "saved"
        except ValueError:
            outcome = "limit"
        except Exception as error:  # noqa: BLE001 - the assertion below reports any surprise
            outcome = f"unexpected:{type(error).__name__}"
        with lock:
            outcomes.append(outcome)

    threads = [threading.Thread(target=work, args=(word,)) for word in words]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return outcomes


def test_concurrent_writers_never_exceed_the_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(vocabulary, "MAX_ENTRIES", 20)
    # Many short rounds: a check-then-insert race is probabilistic, so repeat it.
    for round_number in range(25):
        store = VocabularyStore(tmp_path / f"round{round_number}.sqlite3")
        _fill(store, 15)

        outcomes = _concurrent_adds(store, [f"new{i}" for i in range(16)])

        assert store.count() == 20, outcomes
        assert outcomes.count("saved") == 5
        assert outcomes.count("limit") == 11
        assert len(outcomes) == 16


def test_concurrent_identical_adds_produce_one_row(store):
    barrier = threading.Barrier(8)
    ids: list[int] = []
    lock = threading.Lock()

    def work():
        barrier.wait()
        entry = store.add("same", "same", "en", "tr")
        with lock:
            ids.append(entry.id)

    threads = [threading.Thread(target=work) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert len(ids) == 8
    assert len(set(ids)) == 1
    assert store.count() == 1


# --- schema initialization ------------------------------------------------------------


def test_fresh_database_gets_the_expected_schema_once(path):
    VocabularyStore(path)
    VocabularyStore(path)  # re-initializing a current database is a no-op

    assert _user_version(path) == SCHEMA_VERSION
    assert _tables(path) == ["vocabulary_entries"]


def test_database_from_newer_schema_is_not_modified(tmp_path):
    path = tmp_path / "vocabulary.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA user_version = 99")
    connection.close()
    before = path.read_bytes()

    with pytest.raises(RuntimeError, match="newer"):
        VocabularyStore(path)

    assert _user_version(path) == 99
    assert _tables(path) == []
    assert path.read_bytes() == before


def _make_database(path, statements, user_version):
    connection = sqlite3.connect(path)
    try:
        for statement in statements:
            connection.execute(statement)
        connection.execute(f"PRAGMA user_version = {user_version}")
        connection.commit()
    finally:
        connection.close()


_GOOD_COLUMNS = """
    id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL, translation TEXT NOT NULL,
    source_language TEXT NOT NULL, target_language TEXT NOT NULL, created_at TEXT NOT NULL
"""


@pytest.mark.parametrize(
    ("statements", "user_version", "message"),
    [
        # Wrong columns under the current version.
        (["CREATE TABLE vocabulary_entries (id INTEGER, junk TEXT)"], 1, "schema"),
        # Right columns, but the unique duplicate guard is missing.
        ([f"CREATE TABLE vocabulary_entries ({_GOOD_COLUMNS})"], 1, "schema"),
        # Right columns, but the unique guard covers the wrong columns.
        (
            [
                f"CREATE TABLE vocabulary_entries ({_GOOD_COLUMNS}, UNIQUE (source))",
            ],
            1,
            "schema",
        ),
        # Current version number on an unrelated database (table missing).
        (["CREATE TABLE something_else (x TEXT)"], 1, "schema"),
        # Unversioned database that belongs to something else.
        (
            ["CREATE TABLE secrets (k TEXT, v TEXT)", "INSERT INTO secrets VALUES ('a', 'b')"],
            0,
            "not a",
        ),
        # Unversioned database with a half-built table of our name: never adopted either.
        (["CREATE TABLE vocabulary_entries (id INTEGER, junk TEXT)"], 0, "not a"),
        # Nonsensical version.
        ([], -5, "invalid"),
    ],
)
def test_malformed_or_foreign_database_is_rejected_without_modification(
    path, statements, user_version, message
):
    _make_database(path, statements, user_version)
    before = path.read_bytes()

    with pytest.raises(VocabularyStoreError, match=message):
        VocabularyStore(path)

    assert path.read_bytes() == before


def test_garbage_file_is_reported_and_left_untouched(path):
    path.write_bytes(b"this is definitely not a sqlite database\n" * 64)
    before = path.read_bytes()

    with pytest.raises(VocabularyStoreError):
        VocabularyStore(path)

    assert path.read_bytes() == before


def test_empty_existing_file_is_a_valid_new_database(path):
    path.write_bytes(b"")

    store = VocabularyStore(path)

    assert store.add("a", "b", "en", "tr").source == "a"


def test_directory_in_place_of_the_database_is_reported(tmp_path):
    (tmp_path / "vocabulary.sqlite3").mkdir()

    with pytest.raises(VocabularyStoreError):
        VocabularyStore(tmp_path / "vocabulary.sqlite3")


def test_unusable_parent_directory_is_reported(tmp_path):
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("x", encoding="utf-8")

    with pytest.raises(VocabularyStoreError):
        VocabularyStore(blocker / "vocabulary.sqlite3")


# --- SQLite failure behavior ----------------------------------------------------------


def test_locked_database_fails_fast_with_a_store_error_and_recovers(path):
    store = VocabularyStore(path, timeout=0.1)
    entry = store.add("keep", "tut", "en", "tr")
    blocker = sqlite3.connect(path)
    blocker.execute("BEGIN EXCLUSIVE")
    try:
        started = time.monotonic()
        with pytest.raises(VocabularyStoreError) as added:
            store.add("secret-term-xyz", "t", "en", "tr")
        with pytest.raises(VocabularyStoreError):
            store.delete(entry.id)
        with pytest.raises(VocabularyStoreError):
            store.count()
        assert time.monotonic() - started < 5
        assert isinstance(added.value.__cause__, sqlite3.OperationalError)
        assert "secret-term-xyz" not in str(added.value)
    finally:
        blocker.rollback()
        blocker.close()

    # Nothing from the failed calls was applied, and the store works again afterwards.
    assert store.count() == 1
    assert store.get(entry.id) == entry
    assert store.add("later", "sonra", "en", "tr").source == "later"


def test_validation_errors_stay_value_errors_and_store_errors_are_runtime_errors():
    assert not issubclass(VocabularyStoreError, ValueError)
    assert issubclass(VocabularyStoreError, RuntimeError)

@pytest.mark.parametrize(
    "statements",
    [
        # Missing the source length constraint.
        [
            """
            CREATE TABLE vocabulary_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                translation TEXT NOT NULL CHECK (length(translation) BETWEEN 1 AND 2000),
                source_language TEXT NOT NULL, target_language TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (source_language, target_language, source, translation)
            )
            """,
            """
            CREATE INDEX idx_vocabulary_language_pair
            ON vocabulary_entries (source_language, target_language, id DESC)
            """,
        ],
        # IDs can be reused if AUTOINCREMENT is missing.
        [
            """
            CREATE TABLE vocabulary_entries (
                id INTEGER PRIMARY KEY,
                source TEXT NOT NULL CHECK (length(source) BETWEEN 1 AND 500),
                translation TEXT NOT NULL CHECK (length(translation) BETWEEN 1 AND 2000),
                source_language TEXT NOT NULL, target_language TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (source_language, target_language, source, translation)
            )
            """,
            """
            CREATE INDEX idx_vocabulary_language_pair
            ON vocabulary_entries (source_language, target_language, id DESC)
            """,
        ],
        # The expected language-pair index is part of the storage contract.
        [
            """
            CREATE TABLE vocabulary_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL CHECK (length(source) BETWEEN 1 AND 500),
                translation TEXT NOT NULL CHECK (length(translation) BETWEEN 1 AND 2000),
                source_language TEXT NOT NULL, target_language TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE (source_language, target_language, source, translation)
            )
            """,
        ],
    ],
    ids=["missing-check", "missing-autoincrement", "missing-language-index"],
)
def test_current_version_schema_missing_required_constraints_is_rejected_unchanged(
    path, statements
):
    _make_database(path, statements, SCHEMA_VERSION)
    before = path.read_bytes()

    with pytest.raises(VocabularyStoreError, match="expected schema"):
        VocabularyStore(path)

    assert path.read_bytes() == before
