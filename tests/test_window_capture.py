from dataclasses import replace

import pytest
from PIL import Image

from desktranslate.errors import TargetUnavailableError
from desktranslate.models import Rect
from desktranslate.window_capture import WindowCapture, WindowInfo


def make_window(handle: int = 100, pid: int = 200) -> WindowInfo:
    return WindowInfo(
        handle=handle,
        pid=pid,
        executable="game.exe",
        executable_hash="trusted-executable-hash",
        title="Game Window",
        client=Rect(10, 20, 640, 480),
        bounds=Rect(5, 5, 650, 520),
    )


class FakeInspector:
    def __init__(self, window: WindowInfo) -> None:
        self.current = window
        self.window_scans = 0
        self.direct_checks: list[int] = []
        self.visibility_checks = 0
        self.visible = True

    def windows(self) -> list[WindowInfo]:
        self.window_scans += 1
        return [self.current]

    def info(self, handle: int) -> WindowInfo | None:
        self.direct_checks.append(handle)
        return self.current if self.current.handle == handle else None

    def unobscured(self, target: WindowInfo, region: Rect) -> bool:
        self.visibility_checks += 1
        return self.visible


class FakeBackend:
    def __init__(self) -> None:
        self.calls = 0

    def capture(self, region: Rect) -> Image.Image:
        self.calls += 1
        return Image.new("RGB", (region.width, region.height), "black")

    def close(self) -> None:
        pass


def make_capture(
    inspector: FakeInspector, backend: FakeBackend, *, follow_restart: bool = False
) -> WindowCapture:
    window = inspector.current
    return WindowCapture(
        binding={
            "executable": window.executable,
            "executable_hash": window.executable_hash,
            "title": window.title,
        },
        relative=[0.0, 0.0, 0.5, 0.5],
        follow_restart=follow_restart,
        inspector=inspector,
        backend=backend,  # type: ignore[arg-type]
    )


def test_bound_window_is_verified_directly_after_initial_resolution() -> None:
    inspector = FakeInspector(make_window())
    backend = FakeBackend()
    capture = make_capture(inspector, backend)

    capture.capture(Rect(0, 0, 100, 100))
    capture.capture(Rect(0, 0, 100, 100))

    # Only the first frame needs a full window-list scan. Each capture still
    # checks occlusion on both sides of the MSS read.
    assert inspector.window_scans == 1
    assert inspector.direct_checks == [100, 100, 100]
    assert inspector.visibility_checks == 4
    assert backend.calls == 2


def test_reused_handle_with_different_pid_is_rejected_before_next_capture() -> None:
    inspector = FakeInspector(make_window())
    backend = FakeBackend()
    capture = make_capture(inspector, backend)
    capture.capture(Rect(0, 0, 100, 100))

    inspector.current = replace(inspector.current, pid=201)
    with pytest.raises(TargetUnavailableError):
        capture.capture(Rect(0, 0, 100, 100))

    assert backend.calls == 1
    assert inspector.window_scans == 1


def test_opted_in_restart_following_still_requires_unique_matching_window() -> None:
    inspector = FakeInspector(make_window())
    backend = FakeBackend()
    capture = make_capture(inspector, backend, follow_restart=True)
    capture.capture(Rect(0, 0, 100, 100))

    inspector.current = make_window(handle=101, pid=201)
    capture.capture(Rect(0, 0, 100, 100))

    assert inspector.window_scans == 2
    assert capture.identity == (101, 201)
    assert capture.rebound is True
    assert backend.calls == 2
