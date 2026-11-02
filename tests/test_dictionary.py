from __future__ import annotations

import httpx
import pytest

from desktranslate.dictionary import (
    DictionaryLookupError,
    lookup_english_word,
)


def _entry_response() -> list[dict[str, object]]:
    return [
        {
            "word": "run",
            "meanings": [
                {
                    "partOfSpeech": "verb",
                    "definitions": [
                        {
                            "definition": "To move swiftly on foot.",
                            "example": "She runs every morning.",
                        },
                        {"definition": "To operate or function."},
                    ],
                }
            ],
            "sourceUrls": ["https://en.wiktionary.org/wiki/run"],
            "license": {
                "name": "CC BY-SA 3.0",
                "url": "https://creativecommons.org/licenses/by-sa/3.0/",
            },
        }
    ]


def test_lookup_extracts_bounded_definitions_examples_and_attribution(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(200, json=_entry_response())

    monkeypatch.setattr("desktranslate.dictionary.httpx.get", fake_get)

    result = lookup_english_word("run")

    assert result is not None
    assert result.word == "run"
    assert result.senses[0].part_of_speech == "verb"
    assert result.senses[0].definition == "To move swiftly on foot."
    assert result.senses[0].example == "She runs every morning."
    assert result.senses[1].example == ""
    assert result.source_urls == ("https://en.wiktionary.org/wiki/run",)
    assert result.license_name == "CC BY-SA 3.0"
    assert result.license_url.startswith("https://")
    assert calls[0][0] == "https://api.dictionaryapi.dev/api/v2/entries/en/run"
    assert calls[0][1]["follow_redirects"] is False
    assert calls[0][1]["timeout"] == 4.0


def test_lookup_encodes_the_selected_word_and_returns_none_for_404(monkeypatch):
    calls = []

    def fake_get(url, **_kwargs):
        calls.append(url)
        return httpx.Response(404, json={"title": "No Definitions Found"})

    monkeypatch.setattr("desktranslate.dictionary.httpx.get", fake_get)

    assert lookup_english_word("mother-in-law") is None
    assert calls == ["https://api.dictionaryapi.dev/api/v2/entries/en/mother-in-law"]


@pytest.mark.parametrize("word", ["", "two words", "hello!", "x" * 101, "hello/../world"])
def test_lookup_rejects_non_word_input_without_network_access(monkeypatch, word):
    def unexpected_get(*_args, **_kwargs):
        raise AssertionError("Invalid words must not be sent to the dictionary service.")

    monkeypatch.setattr("desktranslate.dictionary.httpx.get", unexpected_get)

    with pytest.raises(ValueError):
        lookup_english_word(word)


def test_lookup_wraps_network_errors_without_exposing_the_requested_word(monkeypatch):
    def failed_get(*_args, **_kwargs):
        raise httpx.ConnectError("connection failed")

    monkeypatch.setattr("desktranslate.dictionary.httpx.get", failed_get)

    with pytest.raises(DictionaryLookupError, match="unavailable") as caught:
        lookup_english_word("confidentialword")

    assert "confidentialword" not in str(caught.value)


def test_lookup_rejects_http_errors_and_oversized_or_invalid_responses(monkeypatch):
    monkeypatch.setattr(
        "desktranslate.dictionary.httpx.get",
        lambda *_args, **_kwargs: httpx.Response(503),
    )
    with pytest.raises(DictionaryLookupError, match="returned an error"):
        lookup_english_word("hello")

    monkeypatch.setattr(
        "desktranslate.dictionary.httpx.get",
        lambda *_args, **_kwargs: httpx.Response(200, content=b"x" * (512 * 1024 + 1)),
    )
    with pytest.raises(DictionaryLookupError, match="size limit"):
        lookup_english_word("hello")

    monkeypatch.setattr(
        "desktranslate.dictionary.httpx.get",
        lambda *_args, **_kwargs: httpx.Response(200, content=b"not-json"),
    )
    with pytest.raises(DictionaryLookupError, match="valid JSON"):
        lookup_english_word("hello")


def test_lookup_ignores_untrusted_non_https_source_and_license_urls(monkeypatch):
    payload = _entry_response()
    payload[0]["sourceUrls"] = ["http://example.invalid/source"]
    payload[0]["license"] = {"name": "Some license", "url": "javascript:alert(1)"}
    monkeypatch.setattr(
        "desktranslate.dictionary.httpx.get",
        lambda *_args, **_kwargs: httpx.Response(200, json=payload),
    )

    result = lookup_english_word("run")

    assert result is not None
    assert result.source_urls == ()
    assert result.license_name == "Some license"
    assert result.license_url == ""


def test_lookup_extracts_bounded_ipa_and_only_trusted_audio_urls(monkeypatch):
    payload = _entry_response()
    payload[0]["phonetic"] = "/rʌn/"
    payload[0]["phonetics"] = [
        {
            "text": "/rʌn/",
            "audio": "https://api.dictionaryapi.dev/media/pronunciations/en/run-uk.mp3",
        },
        {
            "text": "/rʌn/",
            "audio": "https://api.dictionaryapi.dev/media/pronunciations/en/run-us.ogg",
        },
        {"audio": "https://api.dictionaryapi.dev/media/pronunciations/en/run-au.wav"},
        {"audio": "https://api.dictionaryapi.dev/media/pronunciations/en/run-extra.mp3"},
        {"audio": "https://evil.invalid/media/pronunciations/en/run.mp3"},
        {"audio": "http://api.dictionaryapi.dev/media/pronunciations/en/run.mp3"},
        {"audio": "https://api.dictionaryapi.dev/media/pronunciations/en/../run.mp3"},
        {"audio": "https://api.dictionaryapi.dev/media/pronunciations/en/run.mp3?redirect=https%3A%2F%2Fevil.invalid"},
        {"audio": "javascript:alert(1)"},
    ]
    monkeypatch.setattr(
        "desktranslate.dictionary.httpx.get",
        lambda *_args, **_kwargs: httpx.Response(200, json=payload),
    )

    result = lookup_english_word("run")

    assert result is not None
    assert result.phonetic == "/rʌn/"
    assert result.audio_urls == (
        "https://api.dictionaryapi.dev/media/pronunciations/en/run-uk.mp3",
        "https://api.dictionaryapi.dev/media/pronunciations/en/run-us.ogg",
        "https://api.dictionaryapi.dev/media/pronunciations/en/run-au.wav",
    )


def test_lookup_uses_phonetic_array_text_when_top_level_value_is_invalid(monkeypatch):
    payload = _entry_response()
    payload[0]["phonetic"] = "bad\nvalue"
    payload[0]["phonetics"] = [{"text": "/rʌn/"}]
    monkeypatch.setattr(
        "desktranslate.dictionary.httpx.get",
        lambda *_args, **_kwargs: httpx.Response(200, json=payload),
    )

    result = lookup_english_word("run")

    assert result is not None
    assert result.phonetic == "/rʌn/"


def test_lookup_can_return_audio_without_a_definition(monkeypatch):
    audio = "https://api.dictionaryapi.dev/media/pronunciations/en/hello-us.mp3"
    monkeypatch.setattr(
        "desktranslate.dictionary.httpx.get",
        lambda *_args, **_kwargs: httpx.Response(
            200,
            json=[{"word": "hello", "phonetics": [{"audio": audio}]}],
        ),
    )

    result = lookup_english_word("hello")

    assert result is not None
    assert result.senses == ()
    assert result.audio_urls == (audio,)
    assert result.phonetic == ""
