import sqlite3

import pytest

from desktranslate.vocabulary import VocabularyStore


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


def test_exact_duplicate_is_idempotent_but_different_translation_is_allowed(tmp_path):
    store = VocabularyStore(tmp_path / "vocabulary.sqlite3")

    first = store.add("猫", "kedi", "ja", "tr")
    duplicate = store.add("猫", "kedi", "ja", "tr")
    alternate = store.add("猫", "minnoş", "ja", "tr")

    assert duplicate.id == first.id
    assert alternate.id != first.id
    assert store.count() == 2


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


def test_delete_only_removes_requested_entry(tmp_path):
    store = VocabularyStore(tmp_path / "vocabulary.sqlite3")
    entry = store.add("hello", "merhaba", "en", "tr")

    assert store.delete(entry.id)
    assert not store.delete(entry.id)
    assert store.get(entry.id) is None
    assert store.count() == 0


@pytest.mark.parametrize(
    ("source", "translation", "source_language", "target_language"),
    [
        (" ", "word", "en", "tr"),
        ("word", "", "en", "tr"),
        ("word\\nline", "translation", "en", "tr"),
        ("x" * 501, "translation", "en", "tr"),
        ("word", "x" * 2001, "en", "tr"),
        ("word", "translation", "auto", "tr"),
        ("word", "translation", "en", "unknown"),
    ],
)
def test_add_rejects_invalid_or_oversized_values(
    tmp_path, source, translation, source_language, target_language
):
    store = VocabularyStore(tmp_path / "vocabulary.sqlite3")
    with pytest.raises(ValueError):
        store.add(source, translation, source_language, target_language)
    assert store.count() == 0


@pytest.mark.parametrize(
    ("limit", "offset"),
    [(0, 0), (501, 0), (True, 0), (10, -1), (10, True)],
)
def test_list_rejects_invalid_pagination(tmp_path, limit, offset):
    store = VocabularyStore(tmp_path / "vocabulary.sqlite3")
    with pytest.raises(ValueError):
        store.list_entries(limit=limit, offset=offset)


def test_database_from_newer_schema_is_not_modified(tmp_path):
    path = tmp_path / "vocabulary.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA user_version = 99")
    connection.close()

    with pytest.raises(RuntimeError, match="newer"):
        VocabularyStore(path)

    connection = sqlite3.connect(path)
    assert connection.execute("PRAGMA user_version").fetchone()[0] == 99
    connection.close()
