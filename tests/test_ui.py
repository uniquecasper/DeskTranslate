import json
import time

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from desktranslate.settings import Settings, SettingsStore
from desktranslate.ui.window import MainWindow

pytestmark = pytest.mark.headless_ui


@pytest.fixture(scope="module")
def qt_app():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def window(tmp_path, qt_app):
    store = SettingsStore(tmp_path)
    store.save(Settings())
    widget = MainWindow(store, demo=True)
    yield widget
    widget.quit()
    for _ in range(8):
        time.sleep(0.01)
        qt_app.processEvents()
    widget.overlay.deleteLater()
    widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qt_app.processEvents()


def test_all_pages_open_and_plain_text_is_not_markup(window):
    for index in range(window.navigation.count()):
        window.navigation.setCurrentRow(index)
        assert window.pages.currentIndex() == index
    window.overlay.display("<b>source</b>", "<script>literal</script>")
    assert window.overlay.translation.text() == "<script>literal</script>"
    window.overlay.copy()
    assert QApplication.clipboard().text() == "<script>literal</script>"


def test_setup_small_viewport_keeps_buttons_and_scroll_access(window):
    from PySide6.QtWidgets import QWizard

    window.onboarding()
    wizard = window.setup_dialog
    wizard.resize(560, 320)
    app = QApplication.instance()
    assert app is not None
    for _ in range(6):
        app.processEvents()
        page = wizard.currentPage()
        assert page is not None
        assert wizard.width() <= 560 and wizard.height() <= 320
        assert page.scroll_area.horizontalScrollBar().maximum() == 0
        for identifier in (
            QWizard.WizardButton.NextButton,
            QWizard.WizardButton.FinishButton,
            QWizard.WizardButton.CancelButton,
            QWizard.WizardButton.CustomButton1,
        ):
            button = wizard.button(identifier)
            if button.isVisible():
                assert wizard.rect().contains(button.mapTo(wizard, button.rect().bottomRight()))
        page.set_ready(True)
        wizard.next()
    assert not window.settings.onboarding_done
    wizard.reject()


def test_invalid_endpoint_does_not_start_test_or_change_saved_settings(window):
    window.provider_combo.setCurrentIndex(window.provider_combo.findData("custom"))
    window.endpoint_edit.setText("http://remote.example/v1")
    window.test_provider()
    assert not window.jobs.busy
    assert window.settings.provider == "google"
    assert window.store.load().provider == "google"


def test_language_appearance_and_diagnostics_privacy(window):
    window.source_combo.setCurrentIndex(window.source_combo.findData("es"))
    assert window.store.load().source == "es"
    window.theme_combo.setCurrentIndex(window.theme_combo.findData("light"))
    window.save_appearance()
    assert window.store.load().theme == "light"
    window.latest = "PRIVATE_TRANSLATION"
    window.result_source.setText("PRIVATE_SOURCE")
    window.key_edit.setText("PRIVATE_KEY")
    window.copy_diagnostics()
    output = QApplication.clipboard().text()
    assert "PRIVATE" not in output
    assert json.loads(output)["version"]


def test_stop_cancels_queued_start(window, monkeypatch):
    from PySide6.QtTest import QTest

    calls = []
    window.settings.recent_region = [0, 0, 100, 50]
    monkeypatch.setattr(window, "start", lambda once: calls.append(once))
    window.once()
    window.stop()
    QTest.qWait(250)
    assert calls == []


def test_recognition_interval_controls_keep_auto_or_safe_minimum(window):
    window.capture_interval_spin.setValue(0)
    assert window.capture_interval_spin.value() == 0
    window.capture_interval_spin.setValue(1)
    assert window.capture_interval_spin.value() == 50
    window.idle_interval_spin.setValue(0)
    assert window.idle_interval_spin.value() == 0
    window.idle_interval_spin.setValue(1)
    assert window.idle_interval_spin.value() == 100


def test_recognition_timing_controls_are_persisted_and_restored(window):
    window.capture_interval_spin.setValue(120)
    window.idle_interval_spin.setValue(450)
    window.capture_timeout_spin.setValue(18)
    window.ocr_timeout_spin.setValue(42)
    window.translation_timeout_spin.setValue(55)

    window.save_recognition()

    saved = window.store.load()
    assert saved.capture_interval_ms == 120
    assert saved.idle_interval_ms == 450
    assert saved.capture_timeout == 18
    assert saved.ocr_timeout == 42
    assert saved.timeout == 55
    assert window.capture_interval_spin.value() == 120
    assert window.idle_interval_spin.value() == 450


def test_custom_overlay_style_is_validated_and_persisted(window):
    controls = window.overlay_editor.controls
    controls["overlay_color"].setText("#ffdd22")
    controls["overlay_background_opacity"].setValue(60)
    window.save_appearance()
    assert window.store.load().overlay_color == "#ffdd22"
    assert window.store.load().overlay_background_opacity == 60
    controls["overlay_color"].setText("invalid")
    window.save_appearance()
    assert window.store.load().overlay_color == "#ffdd22"


@pytest.mark.parametrize(
    "action", ["provider", "recognition", "preferences", "appearance", "language"]
)
def test_failed_settings_write_keeps_active_configuration_and_reports_failure(
    window, monkeypatch, action
):
    import copy

    original = copy.deepcopy(window.settings)

    def fail_write(settings):
        raise OSError("test disk full")

    monkeypatch.setattr(window.store, "save", fail_write)
    if action == "provider":
        window.provider_combo.setCurrentIndex(window.provider_combo.findData("libre"))
        assert not window.save_provider()
    elif action == "recognition":
        window.quality_combo.setCurrentIndex(window.quality_combo.findData("fast"))
        window.save_recognition()
    elif action == "preferences":
        window.tray_check.setChecked(True)
        window.save_preferences()
    elif action == "appearance":
        window.theme_combo.setCurrentIndex(window.theme_combo.findData("light"))
        window.save_appearance()
    else:
        window.source_combo.setCurrentIndex(window.source_combo.findData("es"))
    assert window.settings == original
    assert "could not be saved" in window.status_label.text()


def test_failed_provider_save_rolls_back_vault_key(window, monkeypatch):
    keys = {}
    monkeypatch.setattr(window.credentials, "get", lambda account: keys.get(account, ""))
    monkeypatch.setattr(
        window.credentials, "set", lambda account, value: keys.__setitem__(account, value)
    )
    monkeypatch.setattr(window.credentials, "delete", lambda account: keys.pop(account, None))

    def fail_write(settings):
        raise OSError("authored disk failure")

    monkeypatch.setattr(window.store, "save", fail_write)
    window.provider_combo.setCurrentIndex(window.provider_combo.findData("openai"))
    window.key_edit.setText("synthetic-credential")
    assert not window.save_provider()
    assert keys == {}
    assert window.settings.provider == "google"
    assert window.key_edit.text() == "synthetic-credential"


def test_invalid_language_search_cannot_start_with_another_language(window, monkeypatch):
    starts = []
    monkeypatch.setattr(
        "desktranslate.ui.window.ModelManager.installed",
        lambda *args, **kwargs: starts.append(True),
    )
    window.source_combo.setEditText("not a language")
    window.start(True)
    assert not starts
    assert window.settings.source == "ja"
    assert window.source_combo.currentText() == "Japanese"
    assert "Choose a language" in window.status_label.text()


def test_region_save_failure_keeps_previous_capture_and_does_not_queue_start(window, monkeypatch):
    from desktranslate.models import Rect

    starts = []

    def fail_write(settings):
        raise OSError("authored disk failure")

    monkeypatch.setattr(window.store, "save", fail_write)
    monkeypatch.setattr(window, "queue_start", lambda once: starts.append(once))
    window.selected_action = "once"
    window.region_selected(Rect(20, 20, 120, 80))
    assert not starts
    assert window.settings.recent_region is None
    assert "could not be saved" in window.status_label.text()


def test_runtime_errors_do_not_reopen_main_window(window, monkeypatch):
    from test_pipeline import OCR, Capture, SlowProvider

    from desktranslate.errors import ProviderAuthenticationError
    from desktranslate.pipeline import Pipeline

    opened = []
    monkeypatch.setattr(window, "showNormal", lambda: opened.append(True))
    pipeline = Pipeline(window.settings, Capture, OCR, SlowProvider)
    pipeline.session.start()
    window.pipeline = pipeline
    window.hide()
    pipeline.fail(ProviderAuthenticationError())
    window.poll_pipeline()
    assert not opened
    assert "key" in window.status_label.text().lower()
    assert window.pause_button.text() == "Retry translation"
    assert window.pause_button.isEnabled()
    assert window.overlay.pause_button.text() == "Retry translation"
    assert window.overlay.pause_button.isEnabled()


@pytest.mark.parametrize("change", ["pixels", "blank", "context"])
def test_identical_text_delivery_follows_visible_dialogue(window, monkeypatch, change):
    from test_pipeline import OCR, Capture, SlowProvider, until

    from desktranslate.models import OCRResult
    from desktranslate.pipeline import Pipeline

    class DialogueOCR(OCR):
        def recognize(self, image, *args, **kwargs):
            return OCRResult("" if image.getpixel((0, 0))[0] == 100 else "A", confidence=0.99)

    capture, provider = Capture(), SlowProvider()
    provider.release.set()
    window.settings.quality = "fast"
    window.settings.recent_region = [0, 0, 120, 80]
    pipeline = Pipeline(window.settings, lambda: capture, DialogueOCR, lambda: provider)
    window.pipeline = pipeline
    displayed = []
    monkeypatch.setattr(window.overlay, "display", lambda source, text: displayed.append(source))
    pipeline.start()

    def received(count):
        window.poll_pipeline()
        return len(displayed) >= count

    try:
        until(lambda: received(1))
        assert pipeline.delivered_source == "A"
        initial_ocr = pipeline.counters["ocr"]
        if change == "context":
            pipeline.clear_context()
        else:
            capture.color = 100 if change == "blank" else 200
        until(lambda: pipeline.counters["ocr"] > initial_ocr)
        if change == "pixels":
            time.sleep(0.3)
            window.poll_pipeline()
            assert displayed == ["A"]
            assert provider.calls == ["A"]
        else:
            if change == "blank":
                until(lambda: pipeline.delivered_source == "")
                window.poll_pipeline()
                capture.color = 200
            until(lambda: received(2))
            assert displayed == ["A", "A"]
    finally:
        pipeline.stop()
        assert pipeline.wait_closed()


def test_polled_result_discarded_before_gui_delivery_can_retry(window, monkeypatch):
    from test_pipeline import OCR, Capture, SlowProvider, until

    from desktranslate.models import OCRResult
    from desktranslate.pipeline import Pipeline

    class SameTextOCR(OCR):
        def recognize(self, *args, **kwargs):
            return OCRResult("A", confidence=0.99)

    capture, provider = Capture(), SlowProvider()
    provider.release.set()
    window.settings.quality = "fast"
    window.settings.recent_region = [0, 0, 120, 80]
    pipeline = Pipeline(window.settings, lambda: capture, SameTextOCR, lambda: provider)
    window.pipeline = pipeline
    displayed = []
    monkeypatch.setattr(window.overlay, "display", lambda source, text: displayed.append(source))
    pipeline.start()
    polled = []

    def awaiting_delivery():
        polled.extend(event for event in pipeline.poll() if event.result)
        return bool(polled)

    try:
        until(awaiting_delivery)
        assert pipeline.delivered_source == ""
        initial = pipeline.session.stamp()
        capture.color = 200
        until(lambda: pipeline.session.stamp() != initial)

        def delivered():
            window.poll_pipeline()
            return bool(displayed)

        until(delivered)
        assert displayed == ["A"]
        assert pipeline.delivered_source == "A"
        assert not pipeline.session.current(polled[-1].stamp)
    finally:
        pipeline.stop()
        assert pipeline.wait_closed()


def test_user_hidden_overlay_stays_hidden_and_explicit_show_recovers(window):
    window.overlay.display("A", "Translated A")
    window.overlay.hide_by_user()
    window.overlay.display("B", "Translated B")
    assert not window.overlay.isVisible()
    window.overlay.configure(window.settings)
    assert not window.overlay.isVisible()
    window.overlay.toggle_visibility()
    assert window.overlay.isVisible()
    window.overlay.hide()  # A blank interval hides automatically rather than by user request.
    window.overlay.toggle_visibility()
    assert window.overlay.isVisible()


def test_session_transcript_is_opt_in_and_cleared_without_persisting_text(window):
    from test_pipeline import OCR, Capture, SlowProvider

    from desktranslate.models import PipelineEvent, SessionState, TranslationResult
    from desktranslate.pipeline import Pipeline

    pipeline = Pipeline(window.settings, Capture, OCR, SlowProvider)
    stamp = pipeline.session.start()
    window.pipeline = pipeline
    pipeline.enqueue(
        PipelineEvent(
            stamp, SessionState.WATCHING, "PRIVATE_SOURCE", TranslationResult("PRIVATE_TRANSLATION")
        )
    )
    window.poll_pipeline()
    assert not window.transcript_page.transcript.entries
    assert window.result_source.text() == "PRIVATE_SOURCE"
    assert window.result_translation.text() == "PRIVATE_TRANSLATION"
    assert window.overlay.source.text() == "PRIVATE_SOURCE"
    assert window.overlay.translation.text() == "PRIVATE_TRANSLATION"
    assert window.overlay.isVisible()
    window.transcript_page.enable.setChecked(True)
    pipeline.enqueue(
        PipelineEvent(
            stamp, SessionState.WATCHING, "PRIVATE_SOURCE", TranslationResult("PRIVATE_TRANSLATION")
        )
    )
    window.poll_pipeline()
    assert len(window.transcript_page.transcript.entries) == 1
    window.stop()
    assert not window.transcript_page.transcript.entries
    assert "PRIVATE" not in window.store.path.read_text()


def test_onboarding_requires_a_real_sample_result_and_can_recover(window, monkeypatch):
    from desktranslate.errors import ProviderTimeoutError
    from desktranslate.models import OCRResult, TranslationResult
    from desktranslate.ui.onboarding import Onboarding

    class Engine:
        def __init__(self, *args):
            pass

        def recognize(self, *args, **kwargs):
            return OCRResult("明日、またここで会おう。")

        def close(self):
            pass

        def reap(self):
            pass

    class Provider:
        fail = True

        def translate(self, request):
            if self.fail:
                raise ProviderTimeoutError()
            return TranslationResult("Let's meet here again tomorrow.")

        def close(self):
            pass

    monkeypatch.setattr("desktranslate.ui.onboarding.IsolatedOCR", Engine)
    monkeypatch.setattr(
        "desktranslate.ui.onboarding.ModelManager.installed", lambda *args, **kwargs: True
    )
    provider = Provider()
    wizard = Onboarding(
        lambda: window.settings, window.commit_settings, lambda settings: lambda: provider, window
    )
    wizard.show()
    assert not wizard.test_page.isComplete()
    wizard.accept()
    assert not window.settings.onboarding_done
    assert wizard.isVisible()
    wizard.test()
    for _ in range(40):
        time.sleep(0.025)
        QApplication.processEvents()
        if not wizard.jobs.busy:
            break
    assert wizard.isVisible()
    assert not wizard.test_page.isComplete()
    assert "took too long" in wizard.test_status.text()
    provider.fail = False
    wizard.test()
    for _ in range(40):
        time.sleep(0.025)
        QApplication.processEvents()
        if not wizard.jobs.busy:
            break
    assert wizard.test_page.isComplete()
    assert "明日" in wizard.sample_result.toPlainText()
    wizard.accept()
    assert window.store.load().onboarding_done


def test_passive_restart_preflight_does_not_open_main_window(window, monkeypatch):
    calls = []
    monkeypatch.setattr(window, "showNormal", lambda: calls.append("focus"))
    monkeypatch.setattr(
        "desktranslate.ui.window.ModelManager.installed", lambda *args, **kwargs: False
    )
    window.settings.recent_region = [0, 0, 100, 50]
    window.start(False, False)
    assert calls == []


def test_compact_navigation_keeps_low_resolution_high_scale_pages_usable(window):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    window.setMinimumSize(1, 1)
    window.resize(600, 320)
    window.show()
    QApplication.processEvents()
    assert window.compact_navigation.isVisible()
    assert not window.sidebar_widget.isVisible()
    for index in range(window.navigation.count()):
        window.compact_navigation.setCurrentIndex(index)
        QApplication.processEvents()
        page = window.pages.currentWidget()
        assert window.pages.currentIndex() == index
        assert page.horizontalScrollBar().maximum() == 0, window.navigation.item(index).text()
    window.compact_navigation.setCurrentIndex(0)
    window.compact_navigation.setFocus()
    QTest.keyClick(window.compact_navigation, Qt.Key.Key_Down)
    assert window.pages.currentIndex() == 1
    window.resize(1000, 800)
    QApplication.processEvents()
    assert window.sidebar_widget.isVisible()
    assert not window.compact_navigation.isVisible()
    assert window.pages.currentIndex() == 1


def test_display_change_refits_after_the_native_window_geometry_arrives(window):
    window.hide()
    window.settings.recent_region = [20, 20, 100, 50]
    window.overlay.display("Authored source", "Authored translation")
    window.display_changed()
    # Windows applies a suggested top-level rectangle after screen signals.
    bounds = window.overlay.screen().availableGeometry()
    window.overlay.setGeometry(
        bounds.x() - 30, bounds.y() - 30, bounds.width() + 80, bounds.height() + 80
    )
    deadline = time.monotonic() + 0.35
    while time.monotonic() < deadline:
        QApplication.processEvents()
        time.sleep(0.01)
    assert bounds.contains(window.overlay.geometry())
    assert window.settings.recent_region is None
    assert window.store.load().recent_region is None
    assert not window.isVisible()
    assert window.overlay.latest == "Authored translation"
    assert window.overlay.status.text().endswith("STOPPED")


def test_stop_closes_region_picker_and_rejects_late_selection(window, monkeypatch):
    from desktranslate.models import Rect
    from desktranslate.ui.selection import RegionSelector

    picker = RegionSelector()
    selected = []
    picker.selected.connect(selected.append)
    window.selector = picker
    window.stop()
    picker.start()  # The pending singleShot must not reopen it after Stop.
    picker.finish(Rect(1, 1, 100, 80))
    assert picker.closed and not picker.windows
    assert window.selector is None and selected == []


def test_first_success_keeps_unsaved_completion_visible(window, monkeypatch):
    from desktranslate.models import PipelineEvent, SessionState, Stamp, TranslationResult

    def unwritable(*args):
        raise OSError("authored disk failure")

    monkeypatch.setattr(window.store, "save", unwritable)
    window.handle_pipeline_event(
        PipelineEvent(
            Stamp(1, 1),
            SessionState.WATCHING,
            source="Authored text",
            result=TranslationResult("Authored translation"),
        )
    )
    assert not window.settings.onboarding_done
    assert window.result_translation.text() == "Authored translation"
    assert "could not be saved" in window.status_label.text()


def test_onboarding_is_singleton_and_waits_for_cancelled_work(window):
    window.onboarding()
    original = window.setup_dialog
    window.onboarding()
    assert window.setup_dialog is original
    original.jobs.busy = True
    original.reject()
    window.onboarding()
    assert window.setup_dialog is original
    original.jobs.busy = False


@pytest.mark.parametrize("once", [False, True])
def test_suppressed_result_only_opens_main_for_explicit_one_shot(window, monkeypatch, once):
    from types import SimpleNamespace

    from desktranslate.models import PipelineEvent, SessionState, Stamp, TranslationResult

    calls = []
    with monkeypatch.context() as patch:
        patch.setattr(window, "pipeline", SimpleNamespace(once=once))
        patch.setattr(window, "showNormal", lambda: calls.append("opened"))
        window.overlay.suppressed = True
        window.handle_pipeline_event(
            PipelineEvent(
                Stamp(1, 1),
                SessionState.WATCHING,
                source="Authored source",
                result=TranslationResult("Authored result"),
            )
        )
        assert calls == (["opened"] if once else [])
        assert window.result_translation.text() == "Authored result"
        assert ("overlay cannot fit" in window.status_label.text()) is (not once)


def test_double_clicking_a_recognized_word_emits_the_selected_word(window):
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtGui import QFontMetrics
    from PySide6.QtTest import QTest

    activated = []
    window.result_source.setText("hello world")
    window.result_source.setFixedSize(320, 48)
    window.result_source.wordActivated.connect(activated.append)
    window.show()
    QApplication.processEvents()

    metrics = QFontMetrics(window.result_source.font())
    word = "hello"
    x = max(1, metrics.horizontalAdvance("hello") // 2)
    QTest.mouseDClick(
        window.result_source,
        Qt.MouseButton.LeftButton,
        pos=QPoint(x, window.result_source.height() // 2),
    )
    QApplication.processEvents()

    assert activated == [word]


def test_dictionary_dialog_shows_meaning_definition_pronunciation_and_audio(window, monkeypatch):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMessageBox

    from desktranslate.dictionary import DictionarySense, EnglishDictionaryEntry

    captured = []
    monkeypatch.setattr(
        QMessageBox,
        "exec",
        lambda dialog: captured.append(
            (
                dialog.text(),
                dialog.informativeText(),
                dialog.textFormat(),
                [button.text() for button in dialog.buttons()],
            )
        ),
    )

    window.show_word_lookup_result(
        "run",
        "koşmak",
        "en",
        "tr",
        dictionary_entry=EnglishDictionaryEntry(
            "run",
            (DictionarySense("verb", "To move swiftly on foot.", "She runs every morning."),),
            ("https://en.wiktionary.org/wiki/run",),
            "CC BY-SA 3.0",
            "https://creativecommons.org/licenses/by-sa/3.0/",
            phonetic="/rʌn/",
            audio_urls=("https://api.dictionaryapi.dev/media/pronunciations/en/run-us.mp3",),
        ),
    )

    assert len(captured) == 1
    body, attribution, text_format, buttons = captured[0]
    assert text_format == Qt.TextFormat.PlainText
    assert "Meaning (Turkish):" in body
    assert "koşmak" in body
    assert "Pronunciation (IPA): /rʌn/" in body
    assert "English explanation and example" in body
    assert "To move swiftly on foot." in body
    assert "She runs every morning." in body
    assert "dictionaryapi.dev" in attribution
    assert "CC BY-SA 3.0" in attribution
    assert "Open pronunciation audio" in buttons


def test_dictionary_audio_button_opens_only_the_validated_source_url(window, monkeypatch):
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QMessageBox

    from desktranslate.dictionary import EnglishDictionaryEntry

    opened = []

    def fake_exec(dialog):
        audio_button = next(
            button for button in dialog.buttons() if button.text() == "Open pronunciation audio"
        )
        audio_button.click()
        return 0

    monkeypatch.setattr(QMessageBox, "exec", fake_exec)
    monkeypatch.setattr(
        QDesktopServices,
        "openUrl",
        lambda url: opened.append(url.toString()) or True,
    )

    window.show_word_lookup_result(
        "hello",
        "merhaba",
        "en",
        "tr",
        dictionary_entry=EnglishDictionaryEntry(
            "hello",
            (),
            (),
            "",
            "",
            audio_urls=("https://api.dictionaryapi.dev/media/pronunciations/en/hello-us.mp3",),
        ),
    )

    assert opened == ["https://api.dictionaryapi.dev/media/pronunciations/en/hello-us.mp3"]


def test_translation_status_tooltip_exposes_latest_numeric_stages_only(window):
    from desktranslate.models import PipelineEvent, SessionState, Stamp, TranslationResult

    window.settings.onboarding_done = True
    window.handle_pipeline_event(
        PipelineEvent(
            Stamp(1, 1),
            SessionState.WATCHING,
            source="PRIVATE_SOURCE_TEXT",
            result=TranslationResult("PRIVATE_TRANSLATION_TEXT"),
            timings={
                "capture_ms": 3.0,
                "ocr_call_ms": 180.5,
                "temporal_ms": 0.4,
                "provider_ms": 325.0,
                "total_ms": 515.0,
            },
        )
    )

    tooltip = window.status_label.toolTip()
    assert "Capture: Capture 3.0" in tooltip
    assert "Process round-trip 180.5" in tooltip
    assert "Provider 325.0" in tooltip
    assert "PRIVATE" not in tooltip


@pytest.mark.parametrize(
    ("provider_name", "expected_endpoint"),
    [
        ("ollama", "http://localhost:11434"),
        ("lmstudio", "http://localhost:1234/v1"),
    ],
)
def test_local_model_probe_uses_bundled_sample_without_saving_or_sending_screen_content(
    window, monkeypatch, provider_name, expected_endpoint
):
    from desktranslate.models import TranslationResult

    window.provider_combo.setCurrentIndex(window.provider_combo.findData(provider_name))
    window.model_combo.setCurrentText("qwen2.5:1.5b")
    calls = []
    closed = []

    class FakeProvider:
        def translate(self, request):
            calls.append(request)
            return TranslationResult("明日また会いましょう。")

        def close(self):
            closed.append(True)

    provider = FakeProvider()
    snapshots = []
    monkeypatch.setattr(
        window,
        "provider_factory",
        lambda snapshot: snapshots.append(snapshot) or (lambda: provider),
    )

    def run_inline(operation, callback):
        try:
            callback(operation(), "")
        except Exception as error:
            callback(None, str(error))

    monkeypatch.setattr(window, "job", run_inline)
    saved_provider = window.store.load().provider

    window.test_local_model()

    assert len(calls) == 1
    assert calls[0].text == "明日、またここで会おう。"
    assert calls[0].source == "ja"
    assert calls[0].target == "en"
    assert calls[0].model == "qwen2.5:1.5b"
    assert snapshots[0].provider == provider_name
    assert snapshots[0].endpoint == expected_endpoint
    assert closed == [True]
    assert window.store.load().provider == saved_provider
    assert "Generation succeeded" in window.provider_status.text()
    assert "review translation accuracy manually" in window.provider_status.text()


def test_local_model_probe_requires_a_specific_language_and_model(window, monkeypatch):
    # Language changes commit settings and restore the saved provider selection.
    # Set the source first, then select LM Studio for this validation case.
    window.source_combo.setCurrentIndex(window.source_combo.findData("auto"))
    window.provider_combo.setCurrentIndex(window.provider_combo.findData("lmstudio"))
    calls = []
    monkeypatch.setattr(window, "job", lambda *args, **kwargs: calls.append(True))

    window.model_combo.setCurrentText("")
    window.test_local_model()
    assert not calls
    assert "Choose a model" in window.provider_status.text()

    window.model_combo.setCurrentText("test-model")
    window.test_local_model()
    assert not calls
    assert "specific source language" in window.provider_status.text()


def test_local_model_probe_preserves_configured_local_endpoint(window, monkeypatch):
    window.settings.provider_endpoints["ollama"] = "http://127.0.0.1:11435"
    window.provider_combo.setCurrentIndex(window.provider_combo.findData("ollama"))
    window.model_combo.setCurrentText("qwen2.5:1.5b")
    snapshots = []

    class FakeProvider:
        def translate(self, request):
            from desktranslate.models import TranslationResult

            return TranslationResult("Tomorrow, let's meet here again.")

        def close(self):
            pass

    provider = FakeProvider()
    monkeypatch.setattr(
        window,
        "provider_factory",
        lambda snapshot: snapshots.append(snapshot) or (lambda: provider),
    )

    def run_inline(operation, callback):
        try:
            callback(operation(), "")
        except Exception as error:
            callback(None, str(error))

    monkeypatch.setattr(window, "job", run_inline)
    window.test_local_model()

    assert snapshots[0].endpoint == "http://127.0.0.1:11435"
    assert snapshots[0].provider_endpoints["ollama"] == "http://127.0.0.1:11435"



def test_local_model_probe_executes_with_lm_studio(window, monkeypatch):
    from desktranslate.models import TranslationResult

    window.source_combo.setCurrentIndex(window.source_combo.findData("ja"))
    window.target_combo.setCurrentIndex(window.target_combo.findData("en"))
    window.provider_combo.setCurrentIndex(window.provider_combo.findData("lmstudio"))
    window.model_combo.setCurrentText("qwen2.5:1.5b")
    requests = []
    closed = []

    class FakeProvider:
        def translate(self, request):
            requests.append(request)
            return TranslationResult("We will meet here again tomorrow.")

        def close(self):
            closed.append(True)

    provider = FakeProvider()
    snapshots = []
    monkeypatch.setattr(
        window,
        "provider_factory",
        lambda snapshot: snapshots.append(snapshot) or (lambda: provider),
    )

    def run_inline(operation, callback):
        try:
            callback(operation(), "")
        except Exception as error:
            callback(None, str(error))

    monkeypatch.setattr(window, "job", run_inline)

    window.test_local_model()

    assert len(requests) == 1
    assert requests[0].source == "ja"
    assert requests[0].target == "en"
    assert requests[0].model == "qwen2.5:1.5b"
    assert snapshots[0].provider == "lmstudio"
    assert snapshots[0].endpoint == "http://localhost:1234/v1"
    assert closed == [True]
    assert "Generation succeeded" in window.provider_status.text()

def test_local_model_probe_rejects_identical_languages(window, monkeypatch):
    window.provider_combo.setCurrentIndex(window.provider_combo.findData("ollama"))
    window.model_combo.setCurrentText("qwen2.5:1.5b")
    # The normal UI rejects an identical pair immediately and restores the
    # previous selection. Block signals to exercise the probe's defensive guard
    # against an invalid/stale control state.
    window.source_combo.blockSignals(True)
    window.target_combo.blockSignals(True)
    # English is present in both the managed OCR source list and target list.
    # Use it to create a valid, identical pair in the defensive guard test.
    window.source_combo.setCurrentIndex(window.source_combo.findData("en"))
    window.target_combo.setCurrentIndex(window.target_combo.findData("en"))
    window.source_combo.blockSignals(False)
    window.target_combo.blockSignals(False)
    assert window.source_combo.currentData() == "en"
    assert window.target_combo.currentData() == "en"
    calls = []
    monkeypatch.setattr(window, "job", lambda *args, **kwargs: calls.append(True))

    window.test_local_model()

    assert not calls
    assert "different source and translation languages" in window.provider_status.text()


def test_local_model_probe_rejects_source_without_bundled_sample(window, monkeypatch):
    from desktranslate.ui import onboarding

    window.provider_combo.setCurrentIndex(window.provider_combo.findData("ollama"))
    window.model_combo.setCurrentText("qwen2.5:1.5b")
    monkeypatch.setattr(onboarding, "SAMPLES", {})
    calls = []
    monkeypatch.setattr(window, "job", lambda *args, **kwargs: calls.append(True))

    window.test_local_model()

    assert not calls
    assert "No bundled test sentence" in window.provider_status.text()


def test_local_model_probe_handles_provider_construction_failure(window, monkeypatch):
    window.provider_combo.setCurrentIndex(window.provider_combo.findData("ollama"))
    window.model_combo.setCurrentText("qwen2.5:1.5b")
    calls = []
    monkeypatch.setattr(
        window,
        "provider_factory",
        lambda snapshot: (_ for _ in ()).throw(ValueError("bad endpoint")),
    )
    monkeypatch.setattr(window, "job", lambda *args, **kwargs: calls.append(True))

    window.test_local_model()

    assert not calls
    assert "bad endpoint" in window.provider_status.text()


@pytest.mark.parametrize("failure", ["empty", "exception"])
def test_local_model_probe_closes_provider_on_bad_output(window, monkeypatch, failure):
    from desktranslate.errors import DeskTranslateError
    from desktranslate.models import TranslationResult

    window.provider_combo.setCurrentIndex(window.provider_combo.findData("ollama"))
    window.model_combo.setCurrentText("qwen2.5:1.5b")
    closed = []

    class FakeProvider:
        def translate(self, request):
            if failure == "exception":
                raise DeskTranslateError("local server rejected the request")
            return TranslationResult("   ")

        def close(self):
            closed.append(True)

    provider = FakeProvider()
    monkeypatch.setattr(window, "provider_factory", lambda snapshot: lambda: provider)

    def run_inline(operation, callback):
        try:
            callback(operation(), "")
        except Exception as error:
            callback(None, str(error))

    monkeypatch.setattr(window, "job", run_inline)
    window.test_local_model()

    assert closed == [True]
    assert "Model test failed" in window.provider_status.text()


def test_local_model_probe_discards_stale_async_result(window, monkeypatch):
    window.provider_combo.setCurrentIndex(window.provider_combo.findData("ollama"))
    window.model_combo.setCurrentText("qwen2.5:1.5b")
    pending = []
    monkeypatch.setattr(
        window, "job", lambda operation, callback: pending.append((operation, callback))
    )

    window.test_local_model()
    assert len(pending) == 1

    window.model_combo.setCurrentText("different-model")
    pending[0][1]("stale output", "")

    assert "Setup changed during the model test" in window.provider_status.text()


def test_local_model_probe_button_visibility_tracks_supported_providers(window):
    window.provider_combo.setCurrentIndex(window.provider_combo.findData("google"))
    assert window.model_test_button.isHidden()

    window.provider_combo.setCurrentIndex(window.provider_combo.findData("ollama"))
    assert not window.model_test_button.isHidden()

    window.provider_combo.setCurrentIndex(window.provider_combo.findData("lmstudio"))
    assert not window.model_test_button.isHidden()

    window.provider_combo.setCurrentIndex(window.provider_combo.findData("custom"))
    assert window.model_test_button.isHidden()
