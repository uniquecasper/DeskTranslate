import time
from threading import Event, Lock
from typing import Any, cast

import pytest
from PIL import Image

from desktranslate.algorithms import PRESETS, FrameGate
from desktranslate.errors import CaptureTimeoutError, OCRTimeoutError
from desktranslate.models import OCRResult, SessionState
from desktranslate.ocr import IsolatedOCR
from desktranslate.pipeline import Pipeline, _capture_cadence
from desktranslate.settings import Settings


def test_timing_settings_validate_safe_ranges():
    Settings().validate()
    Settings(
        capture_interval_ms=50,
        idle_interval_ms=100,
        capture_timeout=3,
        ocr_timeout=120,
        timeout=120,
    ).validate()
    for values in (
        {"capture_interval_ms": 1},
        {"capture_interval_ms": 1001},
        {"idle_interval_ms": 99},
        {"idle_interval_ms": 5001},
        {"capture_timeout": 2},
        {"ocr_timeout": 121},
        {"timeout": 2},
    ):
        with pytest.raises(ValueError):
            Settings(**values).validate()


def test_isolated_ocr_uses_configured_timeout_and_retires_worker():
    class Pipe:
        closed = False

        def poll(self, interval):
            time.sleep(interval)
            return False

        def close(self):
            self.closed = True

    class Process:
        terminated = False

        def is_alive(self):
            return True

        def terminate(self):
            self.terminated = True

    engine = cast(Any, IsolatedOCR.__new__(IsolatedOCR))
    engine.timeout = 0.06
    engine.closed = Event()
    engine.cancelled = Event()
    engine.connection = Pipe()
    engine.process = Process()
    engine.job = None
    engine.lock = Lock()

    started = time.monotonic()
    with pytest.raises(OCRTimeoutError):
        engine.receive(Event())
    elapsed = time.monotonic() - started

    assert 0.05 <= elapsed < 0.5
    assert engine.closed.is_set()
    assert engine.connection.closed
    assert engine.process.terminated


def test_isolated_ocr_initialization_wait_uses_configured_timeout():
    class Pipe:
        closed = False

        def poll(self, interval):
            time.sleep(interval)
            return False

        def close(self):
            self.closed = True

    class Process:
        terminated = False

        def is_alive(self):
            return True

        def terminate(self):
            self.terminated = True

    engine = cast(Any, IsolatedOCR.__new__(IsolatedOCR))
    engine.timeout = 0.06
    engine.ready = False
    engine.closed = Event()
    engine.cancelled = Event()
    engine.connection = Pipe()
    engine.process = Process()
    engine.job = None
    engine.lock = Lock()

    with pytest.raises(OCRTimeoutError):
        engine.recognize(Image.new("RGB", (8, 8), "black"), "en")

    assert engine.closed.is_set()
    assert engine.connection.closed
    assert engine.process.terminated


def test_capture_timeout_fails_session_with_safe_error():
    class SlowCapture:
        def capture(self, region):
            time.sleep(3.05)
            return Image.new("RGB", (120, 80), "black")

        def close(self):
            pass

    class UnusedOCR:
        def recognize(self, image, language, vertical=False):
            return OCRResult("unused")

        def close(self):
            pass

    pipeline = Pipeline(
        Settings(recent_region=[0, 0, 120, 80], capture_timeout=3),
        SlowCapture,
        UnusedOCR,
        lambda: cast(Any, None),
        once=True,
    )
    pipeline.start()
    events = []
    deadline = time.monotonic() + 5
    try:
        while time.monotonic() < deadline:
            events.extend(pipeline.poll())
            if any(event.state == SessionState.ERROR for event in events):
                break
            time.sleep(0.01)
        failure = next(event for event in events if event.state == SessionState.ERROR)
        assert failure.category == "CaptureTimeoutError"
        assert failure.error == CaptureTimeoutError.message
    finally:
        pipeline.stop()
        assert pipeline.wait_closed()


def test_configured_capture_interval_is_applied_between_samples():
    class TimedCapture:
        def __init__(self):
            self.samples = []

        def capture(self, region):
            self.samples.append(time.monotonic())
            return Image.new("RGB", (120, 80), "black")

        def close(self):
            pass

    capture = TimedCapture()
    pipeline = Pipeline(
        Settings(
            recent_region=[0, 0, 120, 80],
            quality="fast",
            capture_interval_ms=120,
        ),
        lambda: capture,
        lambda: type(
            "OCR",
            (),
            {
                "recognize": lambda self, image, language, vertical=False: OCRResult(""),
                "close": lambda self: None,
            },
        )(),
        lambda: cast(Any, None),
    )
    pipeline.start()
    try:
        deadline = time.monotonic() + 2
        while len(capture.samples) < 3 and time.monotonic() < deadline:
            time.sleep(0.01)
        assert len(capture.samples) >= 3
        intervals = [
            right - left for left, right in zip(capture.samples, capture.samples[1:], strict=False)
        ]
        assert min(intervals) >= 0.09
    finally:
        pipeline.stop()
        assert pipeline.wait_closed()


def test_idle_interval_override_applies_after_stable_recognition():
    gate = FrameGate(settle=0)
    decision = gate.observe(Image.new("RGB", (120, 80), "black"), 10.0)
    assert decision.ready and gate.emitted

    settings = Settings(quality="fast", capture_interval_ms=150, idle_interval_ms=700)
    assert _capture_cadence(settings, PRESETS["fast"], gate, 14.0) == 0.7


def test_idle_interval_auto_uses_quality_preset():
    gate = FrameGate(settle=0)
    gate.observe(Image.new("RGB", (120, 80), "black"), 10.0)

    settings = Settings(quality="fast", capture_interval_ms=150)
    assert _capture_cadence(settings, PRESETS["fast"], gate, 14.0) == PRESETS["fast"].idle_cadence
