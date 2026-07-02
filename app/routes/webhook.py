from fastapi import APIRouter, Depends, HTTPException

from app.config import Settings, get_settings
from app.models.booking import Booking, BookingStatus
from app.models.conversation import Stage, TurnLog
from app.models.clinic import ClinicConfig
from app.repositories.booking_repo import BookingRepository
from app.repositories.clinic_repo import ClinicRepository
from app.repositories.conversation_repo import ConversationRepository
from app.services.calendar_service import CalendarService
from app.services.conversation_service import ConversationService
from app.services.sms_service import SmsService
from app.services.vapi_service import (
    VapiWebhookPayload,
    build_assistant_config,
    build_tool_results,
    extract_tool_text,
)

router = APIRouter(prefix="/webhook", tags=["webhook"])


def get_clinic_repository() -> ClinicRepository:
    return ClinicRepository(use_firestore=False)


def get_conversation_repository() -> ConversationRepository:
    return ConversationRepository()


def get_booking_repository() -> BookingRepository:
    return BookingRepository()


def get_calendar_service() -> CalendarService:
    return CalendarService()


def get_sms_service() -> SmsService:
    return SmsService()


@router.post("/vapi")
async def handle_vapi_webhook(
    payload: VapiWebhookPayload,
    settings: Settings = Depends(get_settings),
    clinic_repo: ClinicRepository = Depends(get_clinic_repository),
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
    booking_repo: BookingRepository = Depends(get_booking_repository),
    calendar_service: CalendarService = Depends(get_calendar_service),
    sms_service: SmsService = Depends(get_sms_service),
) -> dict:
    message = payload.message

    if message.type == "assistant-request":
        return build_assistant_config()

    if message.type == "tool-calls":
        if not message.call:
            raise HTTPException(status_code=400, detail="tool-calls message missing call")
        if not message.toolCallList:
            raise HTTPException(
                status_code=400,
                detail="tool-calls message missing toolCallList",
            )

        clinic = clinic_repo.get(settings.default_clinic_id)
        caller_number = message.call.customer.get("number")
        state = conversation_repo.get_or_create(
            call_id=message.call.id,
            clinic_id=clinic.clinic_id,
            caller_number=caller_number if isinstance(caller_number, str) else None,
        )
        service = ConversationService()
        tool_results: list[tuple[str, str]] = []

        for tool_call in message.toolCallList:
            user_text = extract_tool_text(tool_call)
            conversation_repo.append_turn(
                message.call.id,
                TurnLog(role="caller", message=user_text),
            )
            result = service.process(state, clinic, user_text)
            if result.ready_to_book:
                booking = _create_confirmed_booking(
                    state=result.state,
                    clinic=clinic,
                    booking_repo=booking_repo,
                    calendar_service=calendar_service,
                    sms_service=sms_service,
                )
                if booking.status == BookingStatus.CONFIRMED:
                    result.reply = (
                        f"{result.reply} Your booking reference is {booking.booking_id}."
                    )
                else:
                    result.state.stage = Stage.AWAITING_CONFIRMATION
                    result.reply = (
                        "I could not complete the calendar booking right now. "
                        "Please try confirming again in a moment."
                    )
            state = conversation_repo.update(result.state)
            conversation_repo.append_turn(
                message.call.id,
                TurnLog(role="assistant", message=result.reply),
            )
            tool_results.append((tool_call.id, result.reply))

        return build_tool_results(tool_results)

    if message.type == "end-of-call-report":
        if message.call:
            conversation_repo.mark_closed(
                message.call.id,
                {
                    "transcript": message.transcript,
                    "summary": message.summary,
                },
            )
        return {"received": True}

    return {"received": True}


def _create_confirmed_booking(
    *,
    state,
    clinic: ClinicConfig,
    booking_repo: BookingRepository,
    calendar_service: CalendarService,
    sms_service: SmsService,
) -> Booking:
    existing_booking = booking_repo.get_by_call_id(state.call_id)
    if existing_booking:
        return existing_booking

    if not state.slots.patient_name or not state.slots.service or not state.slots.datetime:
        raise HTTPException(
            status_code=400,
            detail="Cannot book appointment before all required slots are collected.",
        )

    service_config = next(
        (service for service in clinic.services if service.name == state.slots.service),
        None,
    )
    if not service_config:
        raise HTTPException(status_code=400, detail="Unknown selected service.")

    booking = Booking.from_confirmed_slots(
        clinic_id=clinic.clinic_id,
        call_id=state.call_id,
        caller_number=state.caller_number,
        patient_name=state.slots.patient_name,
        service=state.slots.service,
        start_time=state.slots.datetime,
        duration_minutes=service_config.duration_minutes,
    )

    try:
        booking.google_event_id = calendar_service.create_event(clinic, booking)
    except Exception as exc:
        booking.status = BookingStatus.FAILED
        booking.sms_error = f"Calendar booking failed: {exc}"
        booking_repo.create(booking)
        return booking

    try:
        booking.sms_sid = sms_service.send_confirmation(
            state.caller_number,
            clinic,
            booking,
        )
    except Exception as exc:
        booking.sms_error = str(exc)

    return booking_repo.create(booking)
