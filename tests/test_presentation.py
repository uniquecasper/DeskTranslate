from desktranslate.models import SessionState
from desktranslate.presentation import session_presentation


def test_terminal_one_shot_has_no_live_actions_and_keeps_failure_recoverable():
    for result in (True, False):
        view = session_presentation(SessionState.WATCHING, completed=True, has_result=result)
        assert "not capturing" in view.summary
        assert not view.can_pause and not view.can_stop
    failed = session_presentation(SessionState.ERROR, completed=True)
    assert failed.can_pause and failed.can_stop and "Retry" in failed.pause_text


def test_region_selection_and_preparation_can_be_cancelled_without_enabling_pause():
    selecting = session_presentation(None, selecting=True, preparation="needed")
    assert "Escape" in selecting.summary and selecting.can_stop and not selecting.can_pause
    for stage in ("needed", "downloading"):
        preparing = session_presentation(None, preparation=stage)
        assert "not capturing" in preparing.summary and preparing.can_stop
        assert not preparing.can_pause


def test_paused_waiting_and_idle_states_have_distinct_feedback():
    paused = session_presentation(SessionState.PAUSED)
    assert paused.pause_text == "Resume" and "capture stopped" in paused.summary
    waiting = session_presentation(SessionState.WAITING_TARGET)
    assert "Waiting" in waiting.summary and waiting.can_pause
    idle = session_presentation(None)
    retiring = session_presentation(None, retiring=True)
    assert "Ready" in idle.summary and "Stopping" in retiring.summary
    assert not idle.can_pause and not retiring.can_pause


def test_cleanup_failure_overrides_success_retry_and_preparation():
    for state in (None, SessionState.ERROR, SessionState.WATCHING):
        view = session_presentation(
            state, completed=True, has_result=True, preparation="needed", restart_required=True
        )
        assert "Restart required" in view.summary
        assert not view.can_pause and not view.can_stop


def test_latency_details_exposes_numeric_stages_without_any_content_fields():
    from math import inf, nan

    from desktranslate.presentation import latency_details

    details = latency_details(
        {
            "capture_ms": 4.5,
            "ocr_call_ms": 210,
            "ocr_detect_ms": 80.0,
            "temporal_ms": 0.3,
            "context_ms": 0.2,
            "queue_ms": 1.0,
            "provider_ms": 450.4,
            "total_ms": 680.0,
            "gui_delivery_ms": 8.5,
            "overlay_schedule_ms": 2.1,
            "private_screen_text": "SHOULD_NOT_APPEAR",
            "invalid_ms": -1,
            "not_finite_ms": inf,
            "nan_ms": nan,
            "boolean_ms": True,
        }
    )

    assert "Capture: Capture 4.5" in details
    assert "Process round-trip 210.0" in details
    assert "Detection 80.0" in details
    assert "Provider 450.4" in details
    assert "End-to-end 680.0" in details
    assert "Overlay update 2.1" in details
    assert "SHOULD_NOT_APPEAR" not in details
    assert "invalid_ms" not in details
    assert "not_finite_ms" not in details
    assert "nan_ms" not in details
    assert "boolean_ms" not in details


def test_latency_details_is_empty_when_no_known_numeric_stage_is_available():
    from desktranslate.presentation import latency_details

    assert latency_details({}) == ""
    assert latency_details({"unknown_ms": 1.0}) == ""
