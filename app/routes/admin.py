from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.config import Settings, get_settings
from app.repositories.booking_repo import BookingRepository
from app.repositories.conversation_repo import ConversationRepository

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin_key(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    if not x_admin_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid admin API key.")


def get_booking_repository() -> BookingRepository:
    return BookingRepository()


def get_conversation_repository() -> ConversationRepository:
    return ConversationRepository()


@router.get(
    "/clinics/{clinic_id}/bookings",
    dependencies=[Depends(require_admin_key)],
)
def list_bookings(
    clinic_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    booking_repo: BookingRepository = Depends(get_booking_repository),
) -> dict:
    bookings = booking_repo.list_by_clinic(clinic_id, limit=limit, offset=offset)
    return {
        "items": [booking.model_dump(mode="json") for booking in bookings],
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/clinics/{clinic_id}/conversations",
    dependencies=[Depends(require_admin_key)],
)
def list_conversations(
    clinic_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
) -> dict:
    conversations = conversation_repo.list_by_clinic(
        clinic_id,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [
            {
                "call_id": conversation.call_id,
                "clinic_id": conversation.clinic_id,
                "caller_number": conversation.caller_number,
                "stage": conversation.stage,
                "updated_at": conversation.updated_at.isoformat(),
                "turn_count": len(conversation.turns),
            }
            for conversation in conversations
        ],
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/conversations/{call_id}",
    dependencies=[Depends(require_admin_key)],
)
def get_conversation(
    call_id: str,
    conversation_repo: ConversationRepository = Depends(get_conversation_repository),
) -> dict:
    try:
        conversation = conversation_repo.get(call_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return conversation.model_dump(mode="json")

