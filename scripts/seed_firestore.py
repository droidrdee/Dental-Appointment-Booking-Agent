from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.repositories.clinic_repo import ClinicRepository
from app.repositories.firestore_client import get_firestore_client


def main() -> None:
    db = get_firestore_client()
    clinics = ClinicRepository(use_firestore=False).list()

    for clinic in clinics:
        db.collection("clinics").document(clinic.clinic_id).set(
            clinic.model_dump(mode="json")
        )
        print(f"Seeded clinic: {clinic.clinic_id}")


if __name__ == "__main__":
    main()
