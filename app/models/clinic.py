from typing import Annotated

from pydantic import BaseModel, Field

TimeString = Annotated[str, Field(pattern=r"^\d{2}:\d{2}$")]


class ServiceConfig(BaseModel):
    name: str
    duration_minutes: int = Field(default=60, ge=15, le=240)
    aliases: list[str] = Field(default_factory=list)


class OperatingHours(BaseModel):
    open: TimeString | None = None
    close: TimeString | None = None
    closed: bool = False


class ClinicConfig(BaseModel):
    clinic_id: str
    name: str
    timezone: str
    operating_hours: dict[str, OperatingHours]
    services: list[ServiceConfig]
    phone: str
    email: str
    google_calendar_id: str

