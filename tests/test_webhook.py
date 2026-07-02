import asyncio
from typing import Any

from app.config import get_settings
from app.models.booking import Booking
from app.models.conversation import ConversationState, Stage, TurnLog
from app.repositories.clinic_repo import ClinicRepository
from app.routes.webhook import handle_vapi_webhook
from app.services.vapi_service import VapiWebhookPayload


class FakeConversationRepository:
    def __init__(self) -> None:
        self.states: dict[str, ConversationState] = {}
        self.turns: dict[str, list[TurnLog]] = {}
        self.closed: dict[str, dict[str, Any]] = {}

    def get_or_create(
        self,
        call_id: str,
        clinic_id: str,
        caller_number: str | None = None,
    ) -> ConversationState:
        if call_id not in self.states:
            self.states[call_id] = ConversationState(
                call_id=call_id,
                clinic_id=clinic_id,
                caller_number=caller_number,
            )
        return self.states[call_id]

    def update(self, state: ConversationState) -> ConversationState:
        self.states[state.call_id] = state
        return state

    def append_turn(self, call_id: str, turn: TurnLog) -> None:
        self.turns.setdefault(call_id, []).append(turn)

    def mark_closed(self, call_id: str, summary: dict[str, Any] | None = None) -> None:
        self.closed[call_id] = summary or {}


class FakeBookingRepository:
    def __init__(self) -> None:
        self.bookings: list[Booking] = []

    def create(self, booking: Booking) -> Booking:
        self.bookings.append(booking)
        return booking

    def get_by_call_id(self, call_id: str) -> Booking | None:
        for booking in self.bookings:
            if booking.call_id == call_id:
                return booking
        return None


class FakeCalendarService:
    def create_event(self, clinic, booking: Booking) -> str:
        return "event_123"


class FakeSmsService:
    def send_confirmation(self, to_number, clinic, booking: Booking) -> str:
        return "sms_123"


def test_assistant_request_returns_config() -> None:
    payload = VapiWebhookPayload.model_validate(
        {"message": {"type": "assistant-request"}}
    )

    response = asyncio.run(
        handle_vapi_webhook(
            payload,
            settings=get_settings(),
            clinic_repo=ClinicRepository(),
            conversation_repo=FakeConversationRepository(),
            booking_repo=FakeBookingRepository(),
            calendar_service=FakeCalendarService(),
            sms_service=FakeSmsService(),
        )
    )

    assert response["assistant"]["name"] == "SmileCare Dental Receptionist"


def test_tool_calls_progress_conversation_state() -> None:
    repo = FakeConversationRepository()
    booking_repo = FakeBookingRepository()
    settings = get_settings()
    clinic_repo = ClinicRepository()
    call_id = "call_test_123"
    tool_inputs = [
        ("tool_1", "collect_patient_name", {"value": "Asha Patel"}),
        ("tool_2", "collect_service", {"value": "root canal"}),
        ("tool_3", "collect_datetime", {"value": "2026-07-03 3pm"}),
        ("tool_4", "confirm_and_book", {"value": "yes"}),
    ]

    for tool_id, name, arguments in tool_inputs:
        payload = VapiWebhookPayload.model_validate(
            {
                "message": {
                    "type": "tool-calls",
                    "call": {
                        "id": call_id,
                        "customer": {"number": "+911234567890"},
                    },
                    "toolCallList": [
                        {
                            "id": tool_id,
                            "name": name,
                            "arguments": arguments,
                        }
                    ],
                }
            }
        )
        response = asyncio.run(
            handle_vapi_webhook(
                payload,
                settings=settings,
                clinic_repo=clinic_repo,
                conversation_repo=repo,
                booking_repo=booking_repo,
                calendar_service=FakeCalendarService(),
                sms_service=FakeSmsService(),
            )
        )

        assert response["results"][0]["toolCallId"] == tool_id

    assert repo.states[call_id].stage == Stage.BOOKED
    assert repo.states[call_id].slots.service == "Root Canal"
    assert len(repo.turns[call_id]) == 8
    assert len(booking_repo.bookings) == 1
    assert booking_repo.bookings[0].google_event_id == "event_123"
    assert booking_repo.bookings[0].sms_sid == "sms_123"


def test_confirmation_retry_does_not_duplicate_booking() -> None:
    repo = FakeConversationRepository()
    booking_repo = FakeBookingRepository()
    settings = get_settings()
    clinic_repo = ClinicRepository()
    call_id = "call_retry_123"
    steps = [
        ("tool_1", "collect_patient_name", {"value": "Asha Patel"}),
        ("tool_2", "collect_service", {"value": "root canal"}),
        ("tool_3", "collect_datetime", {"value": "2026-07-03 3pm"}),
        ("tool_4", "confirm_and_book", {"value": "yes"}),
        ("tool_5", "confirm_and_book", {"value": "yes"}),
    ]

    for tool_id, name, arguments in steps:
        payload = VapiWebhookPayload.model_validate(
            {
                "message": {
                    "type": "tool-calls",
                    "call": {
                        "id": call_id,
                        "customer": {"number": "+911234567890"},
                    },
                    "toolCallList": [
                        {
                            "id": tool_id,
                            "name": name,
                            "arguments": arguments,
                        }
                    ],
                }
            }
        )
        asyncio.run(
            handle_vapi_webhook(
                payload,
                settings=settings,
                clinic_repo=clinic_repo,
                conversation_repo=repo,
                booking_repo=booking_repo,
                calendar_service=FakeCalendarService(),
                sms_service=FakeSmsService(),
            )
        )

    assert len(booking_repo.bookings) == 1


def test_end_of_call_report_marks_conversation_closed() -> None:
    repo = FakeConversationRepository()
    payload = VapiWebhookPayload.model_validate(
        {
            "message": {
                "type": "end-of-call-report",
                "call": {"id": "call_done", "customer": {}},
                "summary": "Caller booked an appointment.",
            }
        }
    )

    response = asyncio.run(
        handle_vapi_webhook(
            payload,
            settings=get_settings(),
            clinic_repo=ClinicRepository(),
            conversation_repo=repo,
            booking_repo=FakeBookingRepository(),
            calendar_service=FakeCalendarService(),
            sms_service=FakeSmsService(),
        )
    )

    assert response == {"received": True}
    assert repo.closed["call_done"]["summary"] == "Caller booked an appointment."
