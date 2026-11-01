from __future__ import annotations

import pytest
from PySide6.QtWidgets import QMessageBox

from desktranslate.ui.learning import LearningPage
from desktranslate.vocabulary import VocabularyStore

pytestmark = pytest.mark.headless_ui


def test_deleting_vocabulary_also_deletes_review_state_atomically(
    tmp_path, headless_application, monkeypatch
):
    store = VocabularyStore(tmp_path / "vocabulary.sqlite3")
    page = LearningPage(lambda: store)
    entry = store.add("retain", "sakla", "en", "tr")
    page.review_store.review(entry.id, "good")
    page.refresh()
    page.table.setCurrentCell(0, 0)

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )

    page.delete_selected()

    assert store.get(entry.id) is None
    assert page.review_store.state(entry.id) is None
    assert page.review_store.due_count() == 0
    page.deleteLater()
    headless_application.processEvents()
