"""Conservative code-fragment protection for screen translation.

Recognized code spans are replaced before a translation provider is called and
restored only when every opaque marker survives exactly once and in order.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from desktranslate.errors import TranslationError

_TICK = chr(96)
_LINE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"^\s*(?:def|class|function|func)\s+[A-Za-z_$][\w$]*",
        r"^\s*(?:(?:public|private|protected|internal|static|async|sealed|abstract)\s+)+(?:class|interface|enum|struct|void|int|string|bool|Task(?:<[^>]+>)?)\b",
        r"^\s*(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*(?::[^=]+)?=",
        r"^\s*(?:import|from)\s+[\w.*]+",
        r"^\s*(?:using|namespace|package)\s+[\w.]+;?\s*$",
        r"^\s*return\s+[A-Za-z_$][\w$]*\s*(?:[;(]|$)",
        r"^\s*(?:if|for|while|switch|catch)\s*\(",
        r"^\s*(?:#include|#!/|>>>|\$\s)",
        r"^\s*[{}\[\]]+;?\s*$",
        r"^\s*[A-Za-z_$][\w$.[\]]*\s*(?:=|:=|=>)\s*\S",
        r"^\s*(?:console\.log|print|System\.out\.print|printf)\s*\(",
        r"^\s*(?:SELECT\s+(?:\*|[\w.]+(?:\s*,\s*[\w.]+)*)\s+FROM\s+[\w.]+|INSERT\s+INTO\s+[\w.]+|UPDATE\s+[\w.]+\s+SET\s+[\w.]+\s*=|DELETE\s+FROM\s+[\w.]+|CREATE\s+(?:TABLE|INDEX|VIEW)\s+[\w.]+|ALTER\s+TABLE\s+[\w.]+|DROP\s+TABLE\s+[\w.]+)\b",
        r"^\s*(?:[A-Za-z]:\\|/)[\w.\-/\\]+$",
    )
)


@dataclass(frozen=True, slots=True)
class ProtectedText:
    masked_text: str
    fragments: tuple[str, ...]
    tokens: tuple[str, ...]
    only_code: bool

    def restore(self, translated: str) -> str:
        """Restore every protected span or reject an incomplete provider response."""
        if not self.fragments:
            return translated
        positions: list[int] = []
        for token in self.tokens:
            if translated.count(token) != 1:
                raise TranslationError(
                    "The provider changed a protected code marker. Try a different provider or a smaller region."
                )
            positions.append(translated.index(token))
        if positions != sorted(positions):
            raise TranslationError(
                "The provider reordered protected code markers. Try a different provider or a smaller region."
            )
        restored = translated
        for token, fragment in zip(self.tokens, self.fragments, strict=True):
            restored = restored.replace(token, fragment)
        return restored


def _fenced_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    active: tuple[str, int, int] | None = None
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        marker_char = _TICK if stripped.startswith(_TICK * 3) else "~" if stripped.startswith("~~~") else ""
        if marker_char:
            marker_length = len(stripped) - len(stripped.lstrip(marker_char))
            if active is None:
                active = (marker_char, marker_length, offset)
            else:
                char, length, start = active
                if marker_char == char and marker_length >= length:
                    spans.append((start, offset + len(line)))
                    active = None
        offset += len(line)
    if active is not None:
        spans.append((active[2], len(text)))
    return spans


def _overlaps(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    return any(span[0] < end and start < span[1] for start, end in spans)


def _inline_spans(text: str, existing: list[tuple[int, int]]) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    cursor = 0
    while cursor < len(text):
        start = text.find(_TICK, cursor)
        if start < 0:
            break
        end = text.find(_TICK, start + 1)
        if end < 0:
            break
        candidate = (start, end + 1)
        if "\n" not in text[start:end] and end - start > 1 and not _overlaps(candidate, existing):
            spans.append(candidate)
            cursor = end + 1
        else:
            cursor = start + 1
    return spans


def protect_code(text: str) -> ProtectedText:
    """Mask fenced, inline and clearly code-shaped lines without storing them."""
    if not isinstance(text, str):
        raise TypeError("Code protection requires text.")
    if not text:
        return ProtectedText(text, (), (), False)

    spans = _fenced_spans(text)
    offset = 0
    for line in text.splitlines(keepends=True):
        line_end = offset + len(line)
        line_body = line.rstrip("\r\n")
        line_span = (offset, line_end)
        if line_body.strip() and not _overlaps(line_span, spans) and any(
            pattern.search(line_body) for pattern in _LINE_PATTERNS
        ):
            spans.append(line_span)
        offset = line_end
    spans.extend(_inline_spans(text, spans))

    if not spans:
        return ProtectedText(text, (), (), False)

    spans.sort()
    merged: list[tuple[int, int]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    prefix = "DTXQZ_LOCK_"
    while prefix in text:
        prefix += "X"
    fragments = tuple(text[start:end] for start, end in merged)
    tokens = tuple(f"{prefix}{index:04d}_END" for index in range(len(fragments)))

    pieces: list[str] = []
    cursor = 0
    for (start, end), token in zip(merged, tokens, strict=True):
        pieces.append(text[cursor:start])
        pieces.append(token)
        cursor = end
    pieces.append(text[cursor:])
    masked = "".join(pieces)
    visible = masked
    for token in tokens:
        visible = visible.replace(token, "")
    only_code = not visible.strip()
    return ProtectedText(masked, fragments, tokens, only_code)


def remove_code(text: str) -> str:
    """Return only non-code text for contextual reference sent to a provider."""
    protected = protect_code(text)
    visible = protected.masked_text
    for token in protected.tokens:
        visible = visible.replace(token, "")
    return visible
