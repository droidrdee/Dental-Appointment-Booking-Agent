import base64
import json
from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import Client

from app.config import get_settings


@lru_cache
def get_firestore_client() -> Client:
    settings = get_settings()

    if not firebase_admin._apps:
        cred = None
        if settings.firebase_service_account_json_base64:
            cred = _load_certificate_from_base64(
                settings.firebase_service_account_json_base64
            )
        if cred is None and settings.firebase_credentials_path:
            cred = credentials.Certificate(settings.firebase_credentials_path)
        if cred is None:
            raise RuntimeError(
                "Firestore credentials are not configured. Set "
                "FIREBASE_CREDENTIALS_PATH or FIREBASE_SERVICE_ACCOUNT_JSON_BASE64."
            )

        firebase_admin.initialize_app(
            cred,
            {"projectId": settings.firebase_project_id}
            if settings.firebase_project_id
            else None,
        )

    return firestore.client()


def _load_certificate_from_base64(value: str):
    try:
        raw_json = base64.b64decode(value.encode("utf-8")).decode("utf-8")
        data = json.loads(raw_json)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            return None
    return credentials.Certificate(data)
