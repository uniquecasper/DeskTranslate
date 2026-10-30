import pytest

from desktranslate.vocabulary import VocabularyStore
from desktranslate.vocabulary_lookup import VocabularyLookup


@pytest.fixture
def lookup_store(tmp_path):
    return VocabularyStore(tmp_path / "vocabulary.sqlite3")


def test_lookup_returns_current_text_matches_for_exact_language_pair(lookup_store):
    hello = lookup_store.add("hello", "merhaba", "en", "tr")
    hallo = lookup_store.add("hallo", "merhaba", "de", "tr")
    other_direction = lookup_store.add("hello", "bonjour", "en", "fr")

    results = VocabularyLookup(lookup_store).relevant("She said HELLO!", "en", "tr")

    assert [match.entry for match in results] == [hello]
    assert results[0].matched_current_text
    assert hallo not in [match.entry for match in results]
    assert other_direction not in [match.entry for match in results]


def test_lookup_uses_recent_sources_only_when_current_text_has_no_match(lookup_store):
    current = lookup_store.add("current", "şimdiki", "en", "tr")
    recent = lookup_store.add("moonlight", "ay ışığı", "en", "tr")

    results = VocabularyLookup(lookup_store).relevant(
        "A quiet night", "en", "tr", recent_sources=("The moonlight was bright",)
    )

    assert [match.entry for match in results] == [recent]
    assert not results[0].matched_current_text
    assert current not in [match.entry for match in results]


def test_current_matches_rank_before_recent_matches_and_longer_terms_first(lookup_store):
    short = lookup_store.add("star", "yıldız", "en", "tr")
    long = lookup_store.add("morning star", "çoban yıldızı", "en", "tr")
    recent = lookup_store.add("moon", "ay", "en", "tr")

    results = VocabularyLookup(lookup_store).relevant(
        "The morning star is visible", "en", "tr", recent_sources=("The moon is bright",)
    )

    assert [match.entry for match in results] == [long, short, recent]
    assert [match.matched_current_text for match in results] == [True, True, False]


def test_lookup_obeys_word_boundaries(lookup_store):
    entry = lookup_store.add("cat", "kedi", "en", "tr")

    assert VocabularyLookup(lookup_store).relevant("cathedral", "en", "tr") == ()
    assert VocabularyLookup(lookup_store).relevant("A cat sleeps", "en", "tr")[0].entry == entry


def test_lookup_supports_unicode_normalization_and_cjk(lookup_store):
    accent = lookup_store.add("café", "kahve", "fr", "tr")
    japanese = lookup_store.add("猫", "kedi", "ja", "tr")

    accent_result = VocabularyLookup(lookup_store).relevant("CAFE\u0301", "fr", "tr")
    japanese_result = VocabularyLookup(lookup_store).relevant("黒猫がいる", "ja", "tr")

    assert accent_result[0].entry == accent
    assert japanese_result[0].entry == japanese


def test_lookup_is_read_only(lookup_store):
    entry = lookup_store.add("hello", "merhaba", "en", "tr")
    before = lookup_store.count()

    results = VocabularyLookup(lookup_store).relevant("hello", "en", "tr")

    assert results[0].entry == entry
    assert lookup_store.count() == before
    assert lookup_store.list_entries() == [entry]


def test_lookup_bounds_result_count_and_serialized_bytes(lookup_store):
    for index in range(10):
        lookup_store.add(f"word{index}", f"translation{index}", "en", "tr")

    results = VocabularyLookup(lookup_store).relevant(
        "word0 word1 word2 word3 word4 word5 word6 word7 word8 word9",
        "en",
        "tr",
        limit=3,
    )

    assert len(results) == 3
    assert len(results) <= 24


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"limit": 0}, "Limit"),
        ({"limit": 25}, "Limit"),
        ({"limit": True}, "Limit"),
        ({"max_bytes": 0}, "Byte budget"),
        ({"max_bytes": 1801}, "Byte budget"),
        ({"max_bytes": False}, "Byte budget"),
        ({"recent_sources": ["hello"]}, "tuple"),
    ],
)
def test_lookup_rejects_invalid_bounds_and_context(lookup_store, kwargs, message):
    with pytest.raises(ValueError, match=message):
        VocabularyLookup(lookup_store).relevant("hello", "en", "tr", **kwargs)


def test_lookup_rejects_non_text_input(lookup_store):
    with pytest.raises(ValueError, match="text"):
        VocabularyLookup(lookup_store).relevant(None, "en", "tr")  # type: ignore[arg-type]


def test_lookup_scans_past_first_database_page(lookup_store):
    for index in range(501):
        lookup_store.add(f"term{index}", f"çeviri{index}", "en", "tr")

    oldest = lookup_store.list_entries(limit=1, offset=500)[0]
    results = VocabularyLookup(lookup_store).relevant(oldest.source, "en", "tr")

    assert [match.entry for match in results] == [oldest]


def test_lookup_joins_recent_source_lines_with_a_real_newline(lookup_store):
    entry = lookup_store.add("red fox", "kızıl tilki", "en", "tr")

    results = VocabularyLookup(lookup_store).relevant(
        "Nothing relevant here",
        "en",
        "tr",
        recent_sources=("A red", "fox crossed the path"),
    )

    assert [match.entry for match in results] == [entry]
    assert not results[0].matched_current_text
