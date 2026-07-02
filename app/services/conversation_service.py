from datetime import UTC, datetime
from difflib import SequenceMatcher

from app.models.clinic import ClinicConfig, ServiceConfig
from app.models.conversation import ConversationResult, ConversationState, Stage
from app.utils.date_parser import is_within_operating_hours, parse_requested_datetime


class ConversationService:
    def process(
        self,
        state: ConversationState,
        clinic: ClinicConfig,
        text: str,
        now: datetime | None = None,
    ) -> ConversationResult:
        cleaned = text.strip()

        if state.stage == Stage.AWAITING_NAME:
            return self._collect_name(state, clinic, cleaned)
        if state.stage == Stage.AWAITING_SERVICE:
            return self._collect_service(state, clinic, cleaned)
        if state.stage == Stage.AWAITING_DATETIME:
            return self._collect_datetime(state, clinic, cleaned, now)
        if state.stage == Stage.AWAITING_CONFIRMATION:
            return self._collect_confirmation(state, clinic, cleaned)

        return ConversationResult(
            state=state,
            reply="This appointment flow is already complete.",
        )

    def _collect_name(
        self,
        state: ConversationState,
        clinic: ClinicConfig,
        text: str,
    ) -> ConversationResult:
        if not text or text.isdigit():
            return ConversationResult(
                state=state,
                reply=f"Please tell me the patient's full name for {clinic.name}.",
            )

        state.slots.patient_name = text
        state.stage = Stage.AWAITING_SERVICE
        state.updated_at = _utc_now()
        service_names = ", ".join(service.name for service in clinic.services)
        return ConversationResult(
            state=state,
            reply=f"Thanks {text}. What service do you need? We offer {service_names}.",
        )

    def _collect_service(
        self,
        state: ConversationState,
        clinic: ClinicConfig,
        text: str,
    ) -> ConversationResult:
        service = _match_service(text, clinic.services)
        if not service:
            service_names = ", ".join(service.name for service in clinic.services)
            return ConversationResult(
                state=state,
                reply=f"I could not match that service. Please choose one of: {service_names}.",
            )

        state.slots.service = service.name
        state.stage = Stage.AWAITING_DATETIME
        state.updated_at = _utc_now()
        return ConversationResult(
            state=state,
            reply=f"Got it, {service.name}. What date and time would you prefer?",
        )

    def _collect_datetime(
        self,
        state: ConversationState,
        clinic: ClinicConfig,
        text: str,
        now: datetime | None,
    ) -> ConversationResult:
        try:
            requested = parse_requested_datetime(text, clinic, now=now)
        except (TypeError, ValueError, OverflowError):
            return ConversationResult(
                state=state,
                reply="I could not understand that time. Please say something like tomorrow at 3pm.",
            )

        if not is_within_operating_hours(requested, clinic):
            return ConversationResult(
                state=state,
                reply="That time is outside our operating hours. Please choose a weekday between 10:00 and 19:00.",
            )

        state.slots.datetime = requested
        state.stage = Stage.AWAITING_CONFIRMATION
        state.updated_at = _utc_now()
        formatted = requested.strftime("%A, %d %B %Y at %I:%M %p")
        return ConversationResult(
            state=state,
            reply=f"Please confirm: book {state.slots.service} for {state.slots.patient_name} on {formatted}?",
        )

    def _collect_confirmation(
        self,
        state: ConversationState,
        clinic: ClinicConfig,
        text: str,
    ) -> ConversationResult:
        normalized = text.lower()
        if normalized in {"yes", "y", "confirm", "confirmed", "sure", "ok", "okay"}:
            state.stage = Stage.BOOKED
            state.updated_at = _utc_now()
            return ConversationResult(
                state=state,
                reply=f"Your appointment at {clinic.name} is confirmed.",
                ready_to_book=True,
            )

        if normalized in {"no", "n", "cancel", "stop"}:
            state.stage = Stage.CANCELLED
            state.updated_at = _utc_now()
            return ConversationResult(
                state=state,
                reply="No problem. I have not booked the appointment.",
            )

        return ConversationResult(
            state=state,
            reply="Please reply yes to confirm the booking, or no to cancel.",
        )


def _match_service(text: str, services: list[ServiceConfig]) -> ServiceConfig | None:
    normalized = text.strip().lower()
    best_service: ServiceConfig | None = None
    best_score = 0.0

    for service in services:
        candidates = [service.name, *service.aliases]
        for candidate in candidates:
            candidate_normalized = candidate.lower()
            if normalized in candidate_normalized or candidate_normalized in normalized:
                return service
            score = SequenceMatcher(None, normalized, candidate_normalized).ratio()
            if score > best_score:
                best_score = score
                best_service = service

    return best_service if best_score >= 0.72 else None


def _utc_now() -> datetime:
    return datetime.now(UTC)
