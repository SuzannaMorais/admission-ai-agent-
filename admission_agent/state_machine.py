from enum import Enum


class ApplicationState(str, Enum):
    WAITING_FOR_STUDENT_DETAILS = "waiting_for_student_details"
    MISSING_STUDENT_DETAILS = "missing_student_details"
    INVALID_STUDENT_DETAILS = "invalid_student_details"
    WAITING_TO_UPLOAD_DOCUMENTS = "waiting_to_upload_documents"
    MISSING_DOCUMENTS = "missing_documents"
    WAITING_FOR_VERIFICATION = "waiting_for_verification"
    INVALID_DOCUMENTS = "invalid_documents"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    REVIEWING_ADMISSION_INFORMATION = "reviewing_admission_information"
    WAITING_FOR_ADMISSION_DECISION = "waiting_for_admission_decision"
    ADMISSION_APPROVED = "admission_approved"
    ADMISSION_REJECTED = "admission_rejected"
    STUDENT_WAITLISTED = "student_waitlisted"
    COMPLETING_ENROLLMENT = "completing_enrollment"
    ADMISSION_OFFER_DECLINED = "admission_offer_declined"
    ENROLLMENT_COMPLETED = "enrollment_completed"
    PAYMENT_FAILED = "payment_failed"
    APPLICATION_WITHDRAWN = "application_withdrawn"
    APPLICATION_DEADLINE_EXPIRED = "application_deadline_expired"
    AI_SYSTEM_ERROR = "ai_system_error"


TERMINAL_STATES = {
    ApplicationState.ADMISSION_REJECTED,
    ApplicationState.ADMISSION_OFFER_DECLINED,
    ApplicationState.ENROLLMENT_COMPLETED,
    ApplicationState.APPLICATION_WITHDRAWN,
    ApplicationState.APPLICATION_DEADLINE_EXPIRED,
}

TRANSITIONS = {
    (ApplicationState.WAITING_FOR_STUDENT_DETAILS, "submit_complete_details"): ApplicationState.WAITING_TO_UPLOAD_DOCUMENTS,
    (ApplicationState.WAITING_FOR_STUDENT_DETAILS, "submit_incomplete_details"): ApplicationState.MISSING_STUDENT_DETAILS,
    (ApplicationState.WAITING_FOR_STUDENT_DETAILS, "submit_invalid_details"): ApplicationState.INVALID_STUDENT_DETAILS,
    (ApplicationState.MISSING_STUDENT_DETAILS, "provide_missing_details"): ApplicationState.WAITING_TO_UPLOAD_DOCUMENTS,
    (ApplicationState.INVALID_STUDENT_DETAILS, "correct_invalid_details"): ApplicationState.WAITING_TO_UPLOAD_DOCUMENTS,
    (ApplicationState.WAITING_TO_UPLOAD_DOCUMENTS, "upload_all_documents"): ApplicationState.WAITING_FOR_VERIFICATION,
    (ApplicationState.WAITING_TO_UPLOAD_DOCUMENTS, "documents_missing"): ApplicationState.MISSING_DOCUMENTS,
    (ApplicationState.MISSING_DOCUMENTS, "upload_missing_documents"): ApplicationState.WAITING_FOR_VERIFICATION,
    (ApplicationState.WAITING_FOR_VERIFICATION, "documents_valid"): ApplicationState.REVIEWING_ADMISSION_INFORMATION,
    (ApplicationState.WAITING_FOR_VERIFICATION, "documents_invalid"): ApplicationState.INVALID_DOCUMENTS,
    (ApplicationState.INVALID_DOCUMENTS, "upload_corrected_documents"): ApplicationState.WAITING_FOR_VERIFICATION,
    (ApplicationState.WAITING_FOR_VERIFICATION, "documents_mismatched"): ApplicationState.MANUAL_REVIEW_REQUIRED,
    (ApplicationState.MANUAL_REVIEW_REQUIRED, "officer_resolves_discrepancy"): ApplicationState.REVIEWING_ADMISSION_INFORMATION,
    (ApplicationState.REVIEWING_ADMISSION_INFORMATION, "meets_requirements"): ApplicationState.WAITING_FOR_ADMISSION_DECISION,
    (ApplicationState.WAITING_FOR_ADMISSION_DECISION, "officer_approves"): ApplicationState.ADMISSION_APPROVED,
    (ApplicationState.WAITING_FOR_ADMISSION_DECISION, "officer_rejects"): ApplicationState.ADMISSION_REJECTED,
    (ApplicationState.WAITING_FOR_ADMISSION_DECISION, "qualifies_for_waitlist"): ApplicationState.STUDENT_WAITLISTED,
    (ApplicationState.STUDENT_WAITLISTED, "seat_available_selected"): ApplicationState.ADMISSION_APPROVED,
    (ApplicationState.ADMISSION_APPROVED, "accepts_offer"): ApplicationState.COMPLETING_ENROLLMENT,
    (ApplicationState.ADMISSION_APPROVED, "declines_offer"): ApplicationState.ADMISSION_OFFER_DECLINED,
    (ApplicationState.COMPLETING_ENROLLMENT, "fees_paid"): ApplicationState.ENROLLMENT_COMPLETED,
    (ApplicationState.COMPLETING_ENROLLMENT, "payment_fails"): ApplicationState.PAYMENT_FAILED,
    (ApplicationState.PAYMENT_FAILED, "retry_payment_succeeds"): ApplicationState.ENROLLMENT_COMPLETED,
}

GLOBAL_EVENTS = {
    "withdraw_application": ApplicationState.APPLICATION_WITHDRAWN,
    "deadline_expired": ApplicationState.APPLICATION_DEADLINE_EXPIRED,
    "system_error": ApplicationState.AI_SYSTEM_ERROR,
}


class InvalidTransitionError(Exception):
    def __init__(self, current_state: ApplicationState, event: str):
        super().__init__(f"Invalid transition: {current_state!r} + {event!r}")
        self.current_state = current_state
        self.event = event


def transition(
    current_state: ApplicationState,
    event: str,
    previous_state: ApplicationState | None = None,
) -> ApplicationState:
    if current_state in TERMINAL_STATES:
        raise InvalidTransitionError(current_state, event)

    if event == "system_recovers":
        if current_state == ApplicationState.AI_SYSTEM_ERROR and previous_state is not None:
            return previous_state
        raise InvalidTransitionError(current_state, event)

    key = (current_state, event)
    if key in TRANSITIONS:
        return TRANSITIONS[key]

    if event in GLOBAL_EVENTS:
        return GLOBAL_EVENTS[event]

    raise InvalidTransitionError(current_state, event)
