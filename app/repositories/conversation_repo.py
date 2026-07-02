from datetime import UTC, datetime
from typing import Any

from google.cloud.firestore import ArrayUnion

from app.models.conversation import ConversationState, TurnLog
from app.repositories.firestore_client import get_firestore_client


class ConversationRepository:
    collection_name = "conversations"

    def get_or_create(
        self,
        call_id: str,
        clinic_id: str,
        caller_number: str | None = None,
    ) -> ConversationState:
        ref = self._collection().document(call_id)
        snapshot = ref.get()

        if snapshot.exists:
            return ConversationState.model_validate(snapshot.to_dict())

        state = ConversationState(
            call_id=call_id,
            clinic_id=clinic_id,
            caller_number=caller_number,
        )
        ref.set(state.model_dump(mode="json"))
        return state

    def update(self, state: ConversationState) -> ConversationState:
        state.updated_at = datetime.now(UTC)
        self._collection().document(state.call_id).set(
            state.model_dump(mode="json"),
            merge=True,
        )
        return state

    def append_turn(self, call_id: str, turn: TurnLog) -> None:
        self._collection().document(call_id).update(
            {"turns": ArrayUnion([turn.model_dump(mode="json")])}
        )

    def mark_closed(self, call_id: str, summary: dict[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {
            "closed_at": datetime.now(UTC).isoformat(),
        }
        if summary:
            payload["summary"] = summary
        self._collection().document(call_id).set(payload, merge=True)

    def get(self, call_id: str) -> ConversationState:
        snapshot = self._collection().document(call_id).get()
        if not snapshot.exists:
            raise KeyError(f"Conversation not found: {call_id}")
        return ConversationState.model_validate(snapshot.to_dict())

    def list_by_clinic(
        self,
        clinic_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ConversationState]:
        query = (
            self._collection()
            .where("clinic_id", "==", clinic_id)
            .order_by("updated_at")
            .limit(limit)
            .offset(offset)
        )
        return [
            ConversationState.model_validate(snapshot.to_dict())
            for snapshot in query.stream()
        ]

    def _collection(self):
        return get_firestore_client().collection(self.collection_name)
