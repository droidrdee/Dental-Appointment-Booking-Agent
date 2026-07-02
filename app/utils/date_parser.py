from datetime import datetime, time, timedelta

import pytz
from dateutil import parser

from app.models.clinic import ClinicConfig, OperatingHours


def parse_requested_datetime(
    text: str,
    clinic: ClinicConfig,
    now: datetime | None = None,
) -> datetime:
    timezone = pytz.timezone(clinic.timezone)
    reference = now or datetime.now(timezone)
    if reference.tzinfo is None:
        reference = timezone.localize(reference)
    else:
        reference = reference.astimezone(timezone)

    normalized = text.strip().lower()
    default = reference.replace(hour=9, minute=0, second=0, microsecond=0)

    if "tomorrow" in normalized:
        base = reference + timedelta(days=1)
        cleaned = normalized.replace("tomorrow", "").strip() or "9am"
        parsed_time = parser.parse(cleaned, default=default)
        parsed = base.replace(
            hour=parsed_time.hour,
            minute=parsed_time.minute,
            second=0,
            microsecond=0,
        )
    elif "today" in normalized:
        cleaned = normalized.replace("today", "").strip() or "9am"
        parsed = parser.parse(cleaned, default=default)
    else:
        parsed = parser.parse(normalized, default=default)

    if parsed.tzinfo is None:
        return timezone.localize(parsed)
    return parsed.astimezone(timezone)


def is_within_operating_hours(dt: datetime, clinic: ClinicConfig) -> bool:
    local_dt = dt.astimezone(pytz.timezone(clinic.timezone))
    weekday = local_dt.strftime("%A").lower()
    hours = clinic.operating_hours.get(weekday)

    if not hours or hours.closed:
        return False
    if not hours.open or not hours.close:
        return False

    opens = _parse_time(hours.open)
    closes = _parse_time(hours.close)
    appointment_time = local_dt.time().replace(second=0, microsecond=0)

    return opens <= appointment_time < closes


def describe_hours(hours: OperatingHours) -> str:
    if hours.closed or not hours.open or not hours.close:
        return "closed"
    return f"{hours.open} to {hours.close}"


def _parse_time(value: str) -> time:
    hour, minute = value.split(":")
    return time(hour=int(hour), minute=int(minute))

