"""Small, bounded English dictionary lookup for the word-learning UI.

Only the word explicitly double-clicked by the user is sent to the public
dictionary endpoint. OCR images and surrounding screen text are never sent.
The endpoint is optional enrichment; translation still works when it is down.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import quote

import httpx

MAX_WORD_CHARS = 100
MAX_RESPONSE_BYTES = 512 * 1024
MAX_SENSES = 4
REQUEST_TIMEOUT_SECONDS = 4.0
_ENDPOINT = "https://api.dictionaryapi.dev/api/v2/entries/en/"
_WORD_PATTERN = re.compile(r"[^\W_]+(?:[-'][^\W_]+)*", re.UNICODE)


class DictionaryLookupError(RuntimeError):
    """The optional public dictionary service could not be used safely."""


@dataclass(frozen=True, slots=True)
class DictionarySense:
    part_of_speech: str
    definition: str
    example: str


@dataclass(frozen=True, slots=True)
class EnglishDictionaryEntry:
    word: str
    senses: tuple[DictionarySense, ...]
    source_urls: tuple[str, ...]
    license_name: str
    license_url: str


def lookup_english_word(
    word: str, *, timeout: float = REQUEST_TIMEOUT_SECONDS
) -> EnglishDictionaryEntry | None:
    """Return a few bounded English senses, or None when the word is not found."""
    if not isinstance(word, str):
        raise ValueError("Dictionary lookup requires text.")
    normalized = word.strip()
    if (
        not normalized
        or len(normalized) > MAX_WORD_CHARS
        or _WORD_PATTERN.fullmatch(normalized) is None
    ):
        raise ValueError("Dictionary lookup accepts one English word only.")
    if not isinstance(timeout, (int, float)) or not 0 < timeout <= 15:
        raise ValueError("Dictionary timeout must be between 0 and 15 seconds.")

    url = _ENDPOINT + quote(normalized, safe="")
    try:
        response = httpx.get(
            url,
            headers={"Accept": "application/json", "User-Agent": "DeskTranslate/2"},
            timeout=float(timeout),
            follow_redirects=False,
        )
    except httpx.HTTPError as error:
        raise DictionaryLookupError("The public dictionary service is unavailable.") from error

    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise DictionaryLookupError("The public dictionary service returned an error.")
    if len(response.content) > MAX_RESPONSE_BYTES:
        raise DictionaryLookupError("The dictionary response exceeded the size limit.")
    try:
        payload = response.json()
    except ValueError as error:
        raise DictionaryLookupError("The dictionary response was not valid JSON.") from error
    if not isinstance(payload, list):
        raise DictionaryLookupError("The dictionary response had an unexpected format.")

    senses: list[DictionarySense] = []
    source_urls: list[str] = []
    license_name = ""
    license_url = ""
    response_word = normalized

    for item in payload[:3]:
        if not isinstance(item, dict):
            continue
        candidate_word = item.get("word")
        if isinstance(candidate_word, str) and candidate_word.strip():
            response_word = candidate_word.strip()[:MAX_WORD_CHARS]

        sources = item.get("sourceUrls")
        if isinstance(sources, list):
            for source in sources:
                if (
                    isinstance(source, str)
                    and source.startswith("https://")
                    and len(source) <= 2048
                    and source not in source_urls
                ):
                    source_urls.append(source)
                    if len(source_urls) >= 5:
                        break

        license_data = item.get("license")
        if isinstance(license_data, dict):
            name = license_data.get("name")
            link = license_data.get("url")
            if isinstance(name, str) and not license_name:
                license_name = name[:100]
            if isinstance(link, str) and link.startswith("https://") and not license_url:
                license_url = link[:2048]

        meanings = item.get("meanings")
        if not isinstance(meanings, list):
            continue
        for meaning in meanings[:5]:
            if not isinstance(meaning, dict):
                continue
            part = meaning.get("partOfSpeech")
            part_of_speech = part.strip()[:40] if isinstance(part, str) else ""
            definitions = meaning.get("definitions")
            if not isinstance(definitions, list):
                continue
            for definition in definitions:
                if not isinstance(definition, dict):
                    continue
                value = definition.get("definition")
                if not isinstance(value, str) or not value.strip():
                    continue
                example = definition.get("example")
                senses.append(
                    DictionarySense(
                        part_of_speech,
                        value.strip()[:500],
                        example.strip()[:400] if isinstance(example, str) else "",
                    )
                )
                if len(senses) >= MAX_SENSES:
                    break
            if len(senses) >= MAX_SENSES:
                break
        if len(senses) >= MAX_SENSES:
            break

    if not senses:
        return None
    return EnglishDictionaryEntry(
        word=response_word,
        senses=tuple(senses),
        source_urls=tuple(source_urls),
        license_name=license_name,
        license_url=license_url,
    )
