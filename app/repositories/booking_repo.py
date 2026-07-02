from app.models.booking import Booking
from app.repositories.firestore_client import get_firestore_client


class BookingRepository:
    collection_name = "bookings"

    def create(self, booking: Booking) -> Booking:
        self._collection().document(booking.booking_id).set(
            booking.model_dump(mode="json")
        )
        return booking

    def list_by_clinic(
        self,
        clinic_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Booking]:
        query = (
            self._collection()
            .where("clinic_id", "==", clinic_id)
            .limit(limit)
            .offset(offset)
        )
        return [Booking.model_validate(snapshot.to_dict()) for snapshot in query.stream()]

    def get(self, booking_id: str) -> Booking:
        snapshot = self._collection().document(booking_id).get()
        if not snapshot.exists:
            raise KeyError(f"Booking not found: {booking_id}")
        return Booking.model_validate(snapshot.to_dict())

    def get_by_call_id(self, call_id: str) -> Booking | None:
        query = (
            self._collection()
            .where("call_id", "==", call_id)
            .limit(1)
        )
        snapshots = list(query.stream())
        if not snapshots:
            return None
        return Booking.model_validate(snapshots[0].to_dict())

    def _collection(self):
        return get_firestore_client().collection(self.collection_name)
