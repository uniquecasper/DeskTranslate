"""Local, explicit vocabulary review UI.

The page reads the bounded SQLite collection in pages. Search scans the whole
bounded collection rather than only the currently visible page.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktranslate.languages import LANGUAGES
from desktranslate.vocabulary import (
    MAX_ENTRIES,
    MAX_LIST_LIMIT,
    MAX_SOURCE_CHARS,
    MAX_TRANSLATION_CHARS,
    VocabularyEntry,
    VocabularyStore,
)


class VocabularySaveDialog(QDialog):
    """Let the user review/edit the exact selected pair before saving it."""

    def __init__(
        self,
        source: str,
        translation: str,
        source_language: str,
        target_language: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._source_language = source_language
        self.setWindowTitle("Save vocabulary pair")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        if source_language == "auto":
            language_summary = (
                f"Local vocabulary · Auto → {target_language}\n"
                "OCR used automatic source detection. Choose the actual source language below."
            )
        else:
            language_summary = (
                f"Local vocabulary · {source_language} → {target_language}\n"
                "Review both selected terms before saving."
            )
        layout.addWidget(QLabel(language_summary))

        form = QFormLayout()
        self.source_language_combo: QComboBox | None = None
        if source_language == "auto":
            source_language_combo = QComboBox()
            source_language_combo.addItem("Choose source language…", "")
            for language in LANGUAGES:
                if language.code != "auto":
                    source_language_combo.addItem(language.name, language.code)
            source_language_combo.setAccessibleName("Actual source language")
            self.source_language_combo = source_language_combo
            form.addRow("Actual source language", source_language_combo)

        self.source_edit = QLineEdit(source)
        self.source_edit.setMaxLength(MAX_SOURCE_CHARS)
        self.source_edit.setAccessibleName("Source vocabulary term")
        self.translation_edit = QLineEdit(translation)
        self.translation_edit.setMaxLength(MAX_TRANSLATION_CHARS)
        self.translation_edit.setAccessibleName("Translated vocabulary term")
        form.addRow("Source term", self.source_edit)
        form.addRow("Translation", self.translation_edit)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
        assert save_button is not None
        if self.source_language_combo is not None:
            source_language_combo = self.source_language_combo
            save_button.setEnabled(False)
            source_language_combo.currentIndexChanged.connect(
                lambda _index: save_button.setEnabled(
                    isinstance(source_language_combo.currentData(), str)
                    and bool(source_language_combo.currentData())
                )
            )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, str, str]:
        """Return the edited terms and a specific, storable source language."""
        if self.source_language_combo is None:
            source_language = self._source_language
        else:
            source_language = self.source_language_combo.currentData()
        if not isinstance(source_language, str) or not source_language:
            source_language = ""
        return self.source_edit.text(), self.translation_edit.text(), source_language


class LearningPage(QWidget):
    """Review and search explicitly saved terms without exporting them."""

    PAGE_SIZE = 100

    def __init__(
        self,
        store_factory: Callable[[], VocabularyStore],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._store_factory = store_factory
        self._store: VocabularyStore | None = None
        self.page_number = 0
        self.match_count = 0
        self.total_count = 0
        self._loaded = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        filters = QHBoxLayout()
        self.source_filter = QComboBox()
        self.source_filter.addItem("Any source", None)
        self.target_filter = QComboBox()
        self.target_filter.addItem("Any target", None)
        for language in LANGUAGES:
            if language.code == "auto":
                continue
            self.source_filter.addItem(language.name, language.code)
            self.target_filter.addItem(language.name, language.code)
        self.source_filter.setAccessibleName("Filter by source language")
        self.target_filter.setAccessibleName("Filter by target language")
        filters.addWidget(self.source_filter)
        filters.addWidget(self.target_filter)
        layout.addLayout(filters)

        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setMaxLength(256)
        self.search_edit.setPlaceholderText("Search saved source terms and translations")
        self.search_edit.setAccessibleName("Search saved vocabulary")
        self.search_button = QPushButton("Search")
        self.search_button.setAccessibleName("Search all saved vocabulary")
        search_row.addWidget(self.search_edit, 1)
        search_row.addWidget(self.search_button)
        layout.addLayout(search_row)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Source term", "Translation", "Saved"])
        self.table.setAccessibleName("Saved vocabulary entries")
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 190)
        self.table.setColumnWidth(1, 230)
        layout.addWidget(self.table, 1)

        footer = QHBoxLayout()
        self.previous_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")
        self.delete_button = QPushButton("Delete selected")
        self.delete_button.setAccessibleName("Delete selected vocabulary entry")
        self.status_label = QLabel("Open this page to load saved vocabulary.")
        self.status_label.setWordWrap(True)
        footer.addWidget(self.previous_button)
        footer.addWidget(self.next_button)
        footer.addWidget(self.delete_button)
        layout.addLayout(footer)
        layout.addWidget(self.status_label)

        self.search_button.clicked.connect(self.search)
        self.search_edit.returnPressed.connect(self.search)
        self.source_filter.currentIndexChanged.connect(self._filters_changed)
        self.target_filter.currentIndexChanged.connect(self._filters_changed)
        self.previous_button.clicked.connect(self.previous_page)
        self.next_button.clicked.connect(self.next_page)
        self.delete_button.clicked.connect(self.delete_selected)

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if not self._loaded:
            self.refresh()
            self._loaded = True

    @property
    def store(self) -> VocabularyStore:
        if self._store is None:
            self._store = self._store_factory()
        return self._store

    def _filters_changed(self) -> None:
        self.page_number = 0
        self.refresh()

    def search(self) -> None:
        self.page_number = 0
        self.refresh()

    def previous_page(self) -> None:
        if self.page_number > 0:
            self.page_number -= 1
            self.refresh()

    def next_page(self) -> None:
        if (self.page_number + 1) * self.PAGE_SIZE < self.match_count:
            self.page_number += 1
            self.refresh()

    def _language_filter(self, control: QComboBox) -> str | None:
        value = control.currentData()
        return value if isinstance(value, str) and value else None

    def refresh(self) -> None:
        """Scan at most MAX_ENTRIES in bounded pages; retain only the visible page."""
        try:
            source_language = self._language_filter(self.source_filter)
            target_language = self._language_filter(self.target_filter)
            needle = self.search_edit.text().strip().casefold()
            page_start = self.page_number * self.PAGE_SIZE
            matches = 0
            total = 0
            visible: list[VocabularyEntry] = []
            offset = 0

            while offset < MAX_ENTRIES:
                entries = self.store.list_entries(
                    limit=MAX_LIST_LIMIT,
                    offset=offset,
                    source_language=source_language,
                    target_language=target_language,
                )
                if not entries:
                    break
                total += len(entries)
                for entry in entries:
                    if needle and (
                        needle not in entry.source.casefold()
                        and needle not in entry.translation.casefold()
                    ):
                        continue
                    if page_start <= matches < page_start + self.PAGE_SIZE:
                        visible.append(entry)
                    matches += 1
                offset += len(entries)
                if len(entries) < MAX_LIST_LIMIT:
                    break

            self.total_count = total
            self.match_count = matches
            self._loaded = True
            if page_start and not visible and page_start >= matches:
                self.page_number = max(0, (matches - 1) // self.PAGE_SIZE)
                self.refresh()
                return

            self.table.setRowCount(len(visible))
            for row, entry in enumerate(visible):
                source_item = QTableWidgetItem(entry.source)
                source_item.setData(Qt.ItemDataRole.UserRole, entry.id)
                translation_item = QTableWidgetItem(entry.translation)
                saved_item = QTableWidgetItem(entry.created_at[:10])
                self.table.setItem(row, 0, source_item)
                self.table.setItem(row, 1, translation_item)
                self.table.setItem(row, 2, saved_item)

            first = page_start + 1 if visible else 0
            last = page_start + len(visible)
            self.status_label.setText(
                f"{first}–{last} of {matches} matches · {total} saved in this language filter"
            )
            self.previous_button.setEnabled(self.page_number > 0)
            self.next_button.setEnabled(last < matches)
            self.delete_button.setEnabled(bool(visible))
        except (OSError, ValueError, RuntimeError):
            self.table.setRowCount(0)
            self.match_count = 0
            self.total_count = 0
            self.previous_button.setEnabled(False)
            self.next_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.status_label.setText(
                "Saved vocabulary could not be opened. Your existing data was not changed."
            )

    def delete_selected(self) -> None:
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        if item is None:
            self.status_label.setText("Select a saved entry first.")
            return
        entry_id = item.data(Qt.ItemDataRole.UserRole)
        if type(entry_id) is not int:
            self.status_label.setText("The selected entry is unavailable.")
            return
        answer = QMessageBox.question(
            self,
            "Delete saved vocabulary",
            "Delete the selected local vocabulary entry?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.store.delete(entry_id)
            self.refresh()
        except (OSError, ValueError, RuntimeError):
            self.status_label.setText(
                "The entry could not be deleted. Your saved data was not changed."
            )
