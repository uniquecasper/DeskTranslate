import csv
import io

import pytest

from desktranslate.vocabulary import VocabularyEntry
from desktranslate.vocabulary_exchange import export_anki_csv


def entry(source="hello", translation="merhaba", source_language="en", target_language="tr"):
    return VocabularyEntry(
        id=1,
        source=source,
        translation=translation,
        source_language=source_language,
        target_language=target_language,
        created_at="2026-11-02T00:00:00+00:00",
    )


def _data_rows(content):
    marker = "#columns:Front,Back,SourceLanguage,TargetLanguage\n"
    assert content.startswith("#separator:Comma\n#html:false\n" + marker)
    return list(csv.reader(io.StringIO(content.split(marker, 1)[1])))


def test_export_has_anki_front_back_and_language_columns():
    assert _data_rows(export_anki_csv([entry()])) == [["hello", "merhaba", "en", "tr"]]


def test_export_preserves_unicode_commas_quotes_and_multiple_language_pairs():
    content = export_anki_csv(
        [
            entry('「こんにちは, "世界"」', 'Merhaba, "dünya" ', "ja", "tr"),
            entry("안녕하세요", "Hello", "ko", "en"),
        ]
    )

    assert _data_rows(content) == [
        ['「こんにちは, "世界"」', 'Merhaba, "dünya" ', "ja", "tr"],
        ["안녕하세요", "Hello", "ko", "en"],
    ]


def test_empty_export_contains_valid_anki_column_metadata():
    assert export_anki_csv([]) == (
        "#separator:Comma\n#html:false\n"
        "#columns:Front,Back,SourceLanguage,TargetLanguage\n"
    )


@pytest.mark.parametrize("term", ["=1+1", " +SUM(A1:A2)", "-cmd", "@SUM(1,2)"])
def test_export_rejects_spreadsheet_formula_like_terms(term):
    with pytest.raises(ValueError, match="formula marker"):
        export_anki_csv([entry(source=term)])


@pytest.mark.parametrize("language", ["auto", "unknown", "EN"])
def test_export_rejects_invalid_language_codes(language):
    with pytest.raises(ValueError, match="unsupported"):
        export_anki_csv([entry(source_language=language)])


@pytest.mark.parametrize("value", ["", "   ", "line\nfeed", "nul\x00byte"])
def test_export_rejects_invalid_vocabulary_text(value):
    with pytest.raises(ValueError):
        export_anki_csv([entry(source=value)])


def test_export_does_not_include_ids_timestamps_or_review_schedule():
    content = export_anki_csv([entry()])

    assert "created_at" not in content
    assert "2026-11-02" not in content
    assert "review" not in content.casefold()
    assert ",1," not in content
