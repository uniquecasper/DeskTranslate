from __future__ import annotations

import pytest

from desktranslate.ui.learning import (
    LearningPage,
    VocabularySaveDialog,
)
from desktranslate.vocabulary import VocabularyStore

pytestmark = pytest.mark.headless_ui


@pytest.fixture
def learning_page(tmp_path, headless_application):
    store = VocabularyStore(tmp_path / "vocabulary.sqlite3")
    page = LearningPage(lambda: store)
    yield page, store
    page.deleteLater()
    headless_application.processEvents()


def test_learning_page_loads_only_the_selected_language_pair(learning_page):
    page, store = learning_page
    store.add("猫", "cat", "ja", "en")
    store.add("犬", "dog", "ja", "en")
    store.add("gato", "cat", "es", "en")

    page.source_filter.setCurrentIndex(page.source_filter.findData("ja"))

    assert page.table.rowCount() == 2
    assert page.match_count == 2
    assert page.total_count == 2


def test_learning_search_scans_all_saved_entries_not_only_first_page(learning_page):
    page, store = learning_page
    for index in range(125):
        store.add(f"term-{index}", f"translation-{index}", "en", "tr")

    page.search_edit.setText("term-124")
    page.search()

    assert page.match_count == 1
    assert page.table.rowCount() == 1
    assert page.table.item(0, 0).text() == "term-124"


def test_learning_page_paginates_and_returns_to_previous_page(learning_page):
    page, store = learning_page
    for index in range(125):
        store.add(f"term-{index}", f"translation-{index}", "en", "tr")
    page.refresh()

    assert page.table.rowCount() == 100
    assert page.next_button.isEnabled()

    page.next_page()
    assert page.page_number == 1
    assert page.table.rowCount() == 25

    page.previous_page()
    assert page.page_number == 0
    assert page.table.rowCount() == 100


def test_search_is_case_insensitive_and_checks_translation(learning_page):
    page, store = learning_page
    store.add("bonjour", "Hello there", "fr", "en")

    page.search_edit.setText("HELLO")
    page.search()

    assert page.match_count == 1
    assert page.table.item(0, 0).text() == "bonjour"


def test_empty_search_and_language_filter_can_be_cleared(learning_page):
    page, store = learning_page
    store.add("hola", "hello", "es", "en")
    store.add("bonjour", "hello", "fr", "en")

    page.source_filter.setCurrentIndex(page.source_filter.findData("es"))
    assert page.match_count == 1

    page.source_filter.setCurrentIndex(0)
    assert page.match_count == 2


def _double_click_word(widget, word: str) -> None:
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtGui import QFontMetrics
    from PySide6.QtTest import QTest

    start = widget.text().index(word)
    metrics = QFontMetrics(widget.font())
    x = metrics.horizontalAdvance(widget.text()[:start]) + max(
        1, metrics.horizontalAdvance(word) // 2
    )
    QTest.mouseDClick(
        widget,
        Qt.MouseButton.LeftButton,
        pos=QPoint(x, widget.height() // 2),
    )


def test_result_labels_keep_both_mouse_selections_until_save_click(headless_application):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget

    from desktranslate.ui.window import SelectableLabel

    host = QWidget()
    layout = QVBoxLayout(host)
    source = SelectableLabel("hello world")
    translation = SelectableLabel("merhaba dunya")
    save_button = QPushButton("Save")
    for widget in (source, translation):
        widget.setFixedSize(320, 48)
        widget.setWordWrap(True)
        layout.addWidget(widget)
    layout.addWidget(save_button)
    host.show()
    headless_application.processEvents()

    _double_click_word(source, "hello")
    assert source.selectedText() == "hello"

    # Selecting the translation moves focus away from the source label.
    _double_click_word(translation, "merhaba")
    assert source.selectedText() == "hello"
    assert translation.selectedText() == "merhaba"

    # Clicking Save moves focus away from the translation label too.
    from PySide6.QtTest import QTest

    QTest.mouseClick(save_button, Qt.MouseButton.LeftButton)
    headless_application.processEvents()
    assert source.selectedText() == "hello"
    assert translation.selectedText() == "merhaba"

    # A new OCR/translation result must not reuse stale selections.
    source.setText("new source")
    translation.setText("new translation")
    assert not source.hasSelectedText()
    assert not translation.hasSelectedText()

    host.close()
    host.deleteLater()
    headless_application.processEvents()


def test_auto_source_language_requires_a_specific_choice(headless_application, tmp_path):
    from PySide6.QtWidgets import QDialogButtonBox

    dialog = VocabularySaveDialog("猫", "cat", "auto", "en")

    assert dialog.source_language_combo is not None
    assert dialog.values() == ("猫", "cat", "")
    buttons = dialog.findChild(QDialogButtonBox)
    assert buttons is not None
    save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
    assert save_button is not None
    assert not save_button.isEnabled()

    language_index = dialog.source_language_combo.findData("ja")
    assert language_index > 0
    dialog.source_language_combo.setCurrentIndex(language_index)

    assert save_button.isEnabled()
    source, translation, source_language = dialog.values()
    entry = VocabularyStore(tmp_path / "vocabulary.sqlite3").add(
        source, translation, source_language, "en"
    )
    assert entry.source_language == "ja"
    assert entry.target_language == "en"
    dialog.deleteLater()


def test_fixed_source_language_is_preserved_without_extra_selection(headless_application):
    dialog = VocabularySaveDialog("hello", "merhaba", "en", "tr")

    assert dialog.source_language_combo is None
    assert dialog.values() == ("hello", "merhaba", "en")
    dialog.deleteLater()



def test_delete_selected_requires_explicit_confirmation(learning_page, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    page, store = learning_page
    entry = store.add("hello", "merhaba", "en", "tr")
    page.refresh()
    page.table.setCurrentCell(0, 0)

    decision = [QMessageBox.StandardButton.Cancel]
    monkeypatch.setattr(QMessageBox, "question", lambda *_args, **_kwargs: decision[0])

    page.delete_selected()
    assert store.get(entry.id) == entry
    assert page.table.rowCount() == 1

    decision[0] = QMessageBox.StandardButton.Yes
    page.delete_selected()
    assert store.get(entry.id) is None
    assert page.table.rowCount() == 0
    assert page.match_count == 0
