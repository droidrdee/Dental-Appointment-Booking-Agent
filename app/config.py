from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: Literal["local", "test", "production", "render"] = "local"
    default_clinic_id: str = "smilecare_dental"
    default_timezone: str = "Asia/Kolkata"
    admin_api_key: str = Field(default="change-me")

    google_application_credentials: str | None = None
    google_service_account_json_base64: str | None = None
    # Optional override to target a specific Google Calendar ID (useful for service accounts)
    google_calendar_id: str | None = None

    firebase_credentials_path: str | None = None
    firebase_service_account_json_base64: str | None = None
    firebase_project_id: str | None = None

    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from_number: str | None = None
    twilio_test_to_number: str | None = None
    twilio_use_test_number: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

