from app.repositories.clinic_repo import ClinicRepository


def test_loads_smilecare_clinic_config() -> None:
    clinic = ClinicRepository().get("smilecare_dental")

    assert clinic.name == "SmileCare Dental"
    assert clinic.timezone == "Asia/Kolkata"
    assert clinic.operating_hours["monday"].open == "10:00"
    assert len(clinic.services) == 4


def test_services_include_aliases_for_matching_later() -> None:
    clinic = ClinicRepository().get("smilecare_dental")
    aliases = {alias for service in clinic.services for alias in service.aliases}

    assert "rct" in aliases
    assert "cavity" in aliases

