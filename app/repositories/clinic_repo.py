import json
from pathlib import Path

from app.models.clinic import ClinicConfig
from app.repositories.firestore_client import get_firestore_client

DATA_FILE = Path(__file__).resolve().parents[1] / "data" / "clinics.json"


class ClinicRepository:
    def __init__(self, use_firestore: bool = False) -> None:
        self.use_firestore = use_firestore

    def get(self, clinic_id: str) -> ClinicConfig:
        if self.use_firestore:
            return self._get_from_firestore(clinic_id)
        return self._get_from_file(clinic_id)

    def list(self) -> list[ClinicConfig]:
        if self.use_firestore:
            return self._list_from_firestore()
        return self._list_from_file()

    def _get_from_file(self, clinic_id: str) -> ClinicConfig:
        for clinic in self._list_from_file():
            if clinic.clinic_id == clinic_id:
                return clinic
        raise KeyError(f"Clinic not found: {clinic_id}")

    def _list_from_file(self) -> list[ClinicConfig]:
        clinics = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return [ClinicConfig.model_validate(clinic) for clinic in clinics]

    def _get_from_firestore(self, clinic_id: str) -> ClinicConfig:
        snapshot = get_firestore_client().collection("clinics").document(clinic_id).get()
        if not snapshot.exists:
            raise KeyError(f"Clinic not found: {clinic_id}")
        return ClinicConfig.model_validate(snapshot.to_dict())

    def _list_from_firestore(self) -> list[ClinicConfig]:
        snapshots = get_firestore_client().collection("clinics").stream()
        return [ClinicConfig.model_validate(snapshot.to_dict()) for snapshot in snapshots]

