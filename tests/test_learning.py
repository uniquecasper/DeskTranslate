from __future__ import annotations

import pytest

from desktranslate.ui.learning import LearningPage
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
