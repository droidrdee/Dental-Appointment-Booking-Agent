from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from app.config import get_settings
from app.models.booking import Booking
from app.models.conversation import ConversationState, Stage
from app.routes.admin import get_conversation, list_bookings, require_admin_key


class FakeBookingRepository:
    def list_by_clinic(self, clinic_id: str, limit: int = 50, offset: int = 0):
        return [
            Booking(
                clinic_id=clinic_id,
                call_id="call_123",
                patient_name="Asha Patel",
                service="Root Canal",
                start_time=datetime(2026, 7, 3, 15, 0, tzinfo=UTC),
                end_time=datetime(2026, 7, 3, 16, 30, tzinfo=UTC),
            )
        ]


class FakeConversationRepository:
    def list_by_clinic(self, clinic_id: str, limit: int = 50, offset: int = 0):
        return [
            ConversationState(
                call_id="call_123",
                clinic_id=clinic_id,
                stage=Stage.BOOKED,
            )
        ]

    def get(self, call_id: str):
        return ConversationState(
            call_id=call_id,
            clinic_id="smilecare_dental",
            stage=Stage.BOOKED,
        )


def test_admin_requires_api_key() -> None:
    with pytest.raises(HTTPException) as exc:
        require_admin_key(x_admin_key=None, settings=get_settings())

    assert exc.value.status_code == 401


def test_admin_lists_bookings_with_api_key() -> None:
    require_admin_key(
        x_admin_key=get_settings().admin_api_key,
        settings=get_settings(),
    )
    response = list_bookings(
        "smilecare_dental",
        booking_repo=FakeBookingRepository(),
    )

    assert response["items"][0]["service"] == "Root Canal"


def test_admin_gets_conversation_with_api_key() -> None:
    require_admin_key(
        x_admin_key=get_settings().admin_api_key,
        settings=get_settings(),
    )
    response = get_conversation(
        "call_123",
        conversation_repo=FakeConversationRepository(),
    )

    assert response["call_id"] == "call_123"
