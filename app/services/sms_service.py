from twilio.rest import Client

from app.config import Settings, get_settings
from app.models.booking import Booking
from app.models.clinic import ClinicConfig


class SmsService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def send_confirmation(
        self,
        to_number: str | None,
        clinic: ClinicConfig,
        booking: Booking,
    ) -> str:
        recipient = to_number or self.settings.twilio_test_to_number
        if not recipient:
            raise RuntimeError("No SMS recipient available.")
        if not all(
            [
                self.settings.twilio_account_sid,
                self.settings.twilio_auth_token,
                self.settings.twilio_from_number,
            ]
        ):
            raise RuntimeError("Twilio credentials are not configured.")

        client = Client(
            self.settings.twilio_account_sid,
            self.settings.twilio_auth_token,
        )
        message = client.messages.create(
            body=build_confirmation_message(clinic, booking),
            from_=self.settings.twilio_from_number,
            to=recipient,
        )
        return str(message.sid)


def build_confirmation_message(clinic: ClinicConfig, booking: Booking) -> str:
    when = booking.start_time.strftime("%A, %d %B %Y at %I:%M %p")
    return (
        f"Hi {booking.patient_name}, your {booking.service} appointment at "
        f"{clinic.name} is confirmed for {when}. Reply to reschedule."
    )

