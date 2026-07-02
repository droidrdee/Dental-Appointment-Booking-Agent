from datetime import datetime

import pytz

from app.models.conversation import ConversationState, Stage
from app.repositories.clinic_repo import ClinicRepository
from app.services.conversation_service import ConversationService


def test_full_conversation_reaches_booked_stage() -> None:
    clinic = ClinicRepository().get("smilecare_dental")
    service = ConversationService()
    state = ConversationState(call_id="call_123", clinic_id=clinic.clinic_id)
    now = pytz.timezone(clinic.timezone).localize(datetime(2026, 7, 2, 10, 0))

    name_result = service.process(state, clinic, "Asha Patel", now=now)
    service_result = service.process(name_result.state, clinic, "root canal", now=now)
    time_result = service.process(
        service_result.state,
        clinic,
        "tomorrow at 3pm",
        now=now,
    )
    confirm_result = service.process(time_result.state, clinic, "yes", now=now)

    assert confirm_result.state.stage == Stage.BOOKED
    assert confirm_result.ready_to_book is True
    assert confirm_result.state.slots.patient_name == "Asha Patel"
    assert confirm_result.state.slots.service == "Root Canal"


def test_reprompts_for_invalid_name() -> None:
    clinic = ClinicRepository().get("smilecare_dental")
    state = ConversationState(call_id="call_123", clinic_id=clinic.clinic_id)

    result = ConversationService().process(state, clinic, "12345")

    assert result.state.stage == Stage.AWAITING_NAME
    assert "full name" in result.reply


def test_reprompts_for_unknown_service() -> None:
    clinic = ClinicRepository().get("smilecare_dental")
    state = ConversationState(
        call_id="call_123",
        clinic_id=clinic.clinic_id,
        stage=Stage.AWAITING_SERVICE,
    )

    result = ConversationService().process(state, clinic, "haircut")

    assert result.state.stage == Stage.AWAITING_SERVICE
    assert "could not match" in result.reply.lower()


def test_reprompts_for_time_outside_hours() -> None:
    clinic = ClinicRepository().get("smilecare_dental")
    state = ConversationState(
        call_id="call_123",
        clinic_id=clinic.clinic_id,
        stage=Stage.AWAITING_DATETIME,
    )
    now = pytz.timezone(clinic.timezone).localize(datetime(2026, 7, 2, 10, 0))

    result = ConversationService().process(state, clinic, "tomorrow at 9pm", now=now)

    assert result.state.stage == Stage.AWAITING_DATETIME
    assert "outside our operating hours" in result.reply


def test_no_confirmation_cancels_without_booking() -> None:
    clinic = ClinicRepository().get("smilecare_dental")
    state = ConversationState(
        call_id="call_123",
        clinic_id=clinic.clinic_id,
        stage=Stage.AWAITING_CONFIRMATION,
    )

    result = ConversationService().process(state, clinic, "no")

    assert result.state.stage == Stage.CANCELLED
    assert result.ready_to_book is False

