"""User-facing session semantics, independent of widgets and worker ownership."""

import math
from dataclasses import dataclass
from typing import Literal

from desktranslate.models import SessionState


@dataclass(frozen=True)
class SessionPresentation:
    summary: str
    pause_text: str
    can_pause: bool
    can_stop: bool


def session_presentation(
    state: SessionState | None,
    *,
    selecting: bool = False,
    retiring: bool = False,
    completed: bool = False,
    has_result: bool = False,
    preparation: Literal["needed", "downloading"] | None = None,
    restart_required: bool = False,
) -> SessionPresentation:
    if restart_required:
        return SessionPresentation("Restart required · capture stopped", "Pause", False, False)
    if selecting:
        return SessionPresentation(
            "Selecting a region · Enter confirms, Escape cancels", "Pause", False, True
        )
    if preparation:
        return SessionPresentation(
            "Preparing recognition · not capturing"
            if preparation == "downloading"
            else "Language pack needed · install to continue · not capturing",
            "Pause",
            False,
            True,
        )
    if state is None:
        return SessionPresentation(
            "Stopping · no new capture" if retiring else "Ready · not capturing",
            "Pause",
            False,
            False,
        )
    if completed and state != SessionState.ERROR:
        return SessionPresentation(
            "Translation complete · not capturing"
            if has_result
            else "No text found · not capturing",
            "Pause",
            False,
            False,
        )
    if state == SessionState.PAUSED:
        return SessionPresentation("Paused · capture stopped", "Resume", True, True)
    if state == SessionState.ERROR:
        return SessionPresentation(
            "Translation paused · see Translate for details", "Retry translation", True, True
        )
    summaries = {
        SessionState.STARTING: "Starting translation…",
        SessionState.WATCHING: "Live · watching selected content",
        SessionState.WAITING_TARGET: "Waiting for the chosen application",
        SessionState.RECOGNIZING: "Reading text locally…",
        SessionState.TRANSLATING: "Translating recognized text…",
        SessionState.STOPPING: "Stopping · no new capture",
        SessionState.IDLE: "Ready · not capturing",
        SessionState.SELECTING: "Selecting a region · Enter confirms, Escape cancels",
    }
    active = state not in {SessionState.IDLE, SessionState.STOPPING, SessionState.SELECTING}
    return SessionPresentation(summaries[state], "Pause", active, active)


def latency_details(timings: dict[str, float]) -> str:
    """Format the latest stage timings for a tooltip without accepting content fields."""
    groups = (
        (
            "Capture",
            (("Capture", "capture_ms"), ("Frame analysis", "change_ms")),
        ),
        (
            "OCR",
            (
                ("Preprocessing", "preprocess_ms"),
                ("Engine", "ocr_ms"),
                ("Process round-trip", "ocr_call_ms"),
                ("Detection", "ocr_detect_ms"),
                ("Classification", "ocr_classify_ms"),
                ("Recognition", "ocr_recognize_ms"),
                ("Reconstruction", "ocr_reconstruct_ms"),
                ("Layout detection", "ocr_layout_detect_ms"),
                ("Layout recognition", "ocr_layout_recognize_ms"),
                ("Regional recognition", "ocr_regional_ms"),
            ),
        ),
        ("Stabilization", (("Text stabilization", "temporal_ms"),)),
        (
            "Translation",
            (
                ("Context preparation", "context_ms"),
                ("Queue wait", "queue_ms"),
                ("Provider", "provider_ms"),
            ),
        ),
        (
            "Delivery",
            (
                ("End-to-end", "total_ms"),
                ("GUI delivery", "gui_delivery_ms"),
                ("Overlay update", "overlay_schedule_ms"),
            ),
        ),
    )
    lines = ["Latest translation latency · milliseconds"]
    for title, fields in groups:
        values = []
        for label, key in fields:
            value = timings.get(key)
            if (
                type(value) in {int, float}
                and 0 <= value <= 600_000
                and math.isfinite(value)
            ):
                values.append(f"{label} {value:.1f}")
        if values:
            lines.append(f"{title}: " + " · ".join(values))
    return "\n".join(lines) if len(lines) > 1 else ""
