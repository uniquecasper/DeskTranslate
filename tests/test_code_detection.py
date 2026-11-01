from __future__ import annotations

import pytest

from desktranslate.code_detection import protect_code
from desktranslate.errors import TranslationError


def test_plain_prose_is_not_modified():
    source = "The character opens the inventory and chooses a potion."
    protected = protect_code(source)

    assert protected.masked_text == source
    assert protected.fragments == ()
    assert not protected.only_code


def test_fenced_code_is_masked_and_restored_byte_for_byte():
    code = "~~~python\n def greet(name):\n    return f'Hello, {name}'\n~~~"
    source = f"Explain this example:\n{code}\nIt prints a greeting."
    protected = protect_code(source)

    assert code not in protected.masked_text
    assert len(protected.fragments) == 1
    translated = protected.masked_text.replace("Explain this example:", "Bu örneği açıkla:").replace(
        "It prints a greeting.", "Bir selamlama yazdırır."
    )
    assert protected.restore(translated) == (
        f"Bu örneği açıkla:\n{code}\nBir selamlama yazdırır."
    )


def test_inline_code_is_protected_inside_prose():
    tick = chr(96)
    source = "Call the " + tick + "open_window()" + tick + " function to show the panel."
    protected = protect_code(source)

    assert "open_window()" not in protected.masked_text
    assert protected.restore(protected.masked_text) == source
    assert not protected.only_code


def test_clear_code_lines_are_protected_without_masking_following_prose():
    source = "const total = 3;\nThe total is shown below."
    protected = protect_code(source)

    assert "const total = 3;" not in protected.masked_text
    assert "The total is shown below." in protected.masked_text
    assert protected.restore(protected.masked_text) == source


def test_code_only_text_skips_translation():
    protected = protect_code("def greet(name):\n    return name")

    assert protected.only_code
    assert protected.fragments


@pytest.mark.parametrize("damage", ["missing", "duplicate", "reordered"])
def test_changed_code_markers_are_rejected(damage: str):
    tick = chr(96)
    protected = protect_code("Use " + tick + "x = 1" + tick + " then call " + tick + "run()" + tick + ".")
    assert len(protected.tokens) == 2
    result = protected.masked_text
    first, second = protected.tokens
    if damage == "missing":
        result = result.replace(first, "")
    elif damage == "duplicate":
        result = result.replace(first, first + first)
    else:
        result = result.replace(first, "TEMP").replace(second, first).replace("TEMP", second)

    with pytest.raises(TranslationError):
        protected.restore(result)

def test_non_latin_prose_surrounding_code_is_not_treated_as_code_only():
    code = "const total = 3;"
    source = f"このコードを説明してください。\n{code}\n結果を確認します。"
    protected = protect_code(source)

    assert protected.fragments == (code + "\n",)
    assert not protected.only_code
    translated = protected.masked_text.replace(
        "このコードを説明してください。", "Explain this code."
    ).replace("結果を確認します。", "Check the result.")
    assert code + "\n" in protected.restore(translated)


def test_common_csharp_declaration_is_protected():
    source = "public class PlayerController {"
    protected = protect_code(source)

    assert protected.only_code
    assert protected.restore(protected.masked_text) == source


def test_natural_sql_verbs_are_not_mistaken_for_code():
    source = "Select a character from the list.\nCreate a new save file."
    protected = protect_code(source)

    assert protected.masked_text == source
    assert not protected.only_code


def test_remove_code_keeps_only_prose_for_context():
    from desktranslate.code_detection import remove_code

    source = "The player enters the menu.\nconst total = 3;\nContinue to the next level."
    assert remove_code(source) == "The player enters the menu.\nContinue to the next level."
    assert remove_code("def run():\n    return 1").strip() == ""
