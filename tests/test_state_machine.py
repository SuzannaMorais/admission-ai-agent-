import pytest

from admission_agent.state_machine import ApplicationState, InvalidTransitionError, transition


def test_valid_transition_moves_state():
    assert transition(ApplicationState.WAITING_FOR_STUDENT_DETAILS, "submit_complete_details") == ApplicationState.WAITING_TO_UPLOAD_DOCUMENTS


def test_global_event_withdraw_from_any_nonterminal_state():
    assert transition(ApplicationState.WAITING_FOR_VERIFICATION, "withdraw_application") == ApplicationState.APPLICATION_WITHDRAWN


def test_system_error_then_recovery_returns_previous_state():
    errored = transition(ApplicationState.MANUAL_REVIEW_REQUIRED, "system_error")
    assert errored == ApplicationState.AI_SYSTEM_ERROR
    recovered = transition(errored, "system_recovers", previous_state=ApplicationState.MANUAL_REVIEW_REQUIRED)
    assert recovered == ApplicationState.MANUAL_REVIEW_REQUIRED


def test_invalid_transition_from_terminal_state_raises():
    with pytest.raises(InvalidTransitionError):
        transition(ApplicationState.ENROLLMENT_COMPLETED, "submit_complete_details")


def test_unmatched_event_raises():
    with pytest.raises(InvalidTransitionError):
        transition(ApplicationState.WAITING_FOR_STUDENT_DETAILS, "fees_paid")
