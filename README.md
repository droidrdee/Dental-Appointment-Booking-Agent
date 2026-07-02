# Dental Appointment Booking Agent

FastAPI backend for a VAPI-style dental receptionist. It accepts simulated VAPI webhooks, tracks a multi-turn booking flow in Firestore, creates confirmed appointments in Google Calendar, sends Twilio SMS confirmations, and exposes an admin API for bookings and conversations.

## Architecture

```text
VAPI webhook
  -> FastAPI /webhook/vapi
  -> ConversationService state machine
  -> Firestore conversations/{call_id}
  -> Google Calendar + Twilio on confirmation
  -> Firestore bookings/{booking_id}

Admin API
  -> X-Admin-Key auth
  -> clinic-scoped bookings and conversations
```

The project treats SmileCare Dental as one tenant from day one. Clinic configuration lives in `app/data/clinics.json` and every persisted booking/conversation is scoped by `clinic_id`.

## Setup

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Fill `.env` with:

- `FIREBASE_CREDENTIALS_PATH` or `FIREBASE_SERVICE_ACCOUNT_JSON_BASE64`
- `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_SERVICE_ACCOUNT_JSON_BASE64`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`
- `TWILIO_TEST_TO_NUMBER` for local simulator SMS fallback
- `ADMIN_API_KEY`

Seed clinic data after Firebase is configured:

```bash
.venv/bin/python scripts/seed_firestore.py
```

Verify real external integrations:

```bash
.venv/bin/python scripts/verify_integrations.py
```

## Run

```bash
.venv/bin/python -m uvicorn app.main:app --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Simulate a VAPI call:

```bash
.venv/bin/python tests/simulate_call.py --base-url http://127.0.0.1:8000
```

Run tests:

```bash
.venv/bin/python -m pytest
```

## API

`POST /webhook/vapi`

Handles:

- `assistant-request`
- `tool-calls`
- `end-of-call-report`
- unknown events with `{"received": true}`

Tool-call payload shape:

```json
{
  "message": {
    "type": "tool-calls",
    "call": { "id": "call_123", "customer": { "number": "+911234567890" } },
    "toolCallList": [
      {
        "id": "tool_1",
        "name": "collect_patient_name",
        "arguments": { "value": "Asha Patel" }
      }
    ]
  }
}
```

Admin endpoints require `X-Admin-Key`:

```bash
curl -H "X-Admin-Key: $ADMIN_API_KEY" \
  http://127.0.0.1:8000/admin/clinics/smilecare_dental/bookings

curl -H "X-Admin-Key: $ADMIN_API_KEY" \
  http://127.0.0.1:8000/admin/clinics/smilecare_dental/conversations

curl -H "X-Admin-Key: $ADMIN_API_KEY" \
  http://127.0.0.1:8000/admin/conversations/call_123
```

## Design Decisions

- Firestore state is keyed by VAPI `call.id`, so the flow survives restarts and can scale horizontally.
- `clinic_id` is present on clinic, conversation, and booking data, so adding clinics is a data/config change rather than a code rewrite.
- The state machine is plain Python instead of LangGraph to keep the core flow testable and easy to explain under the assignment timeline.
- Calendar failures do not crash the webhook. A failed booking record is stored and the caller is asked to retry confirmation.
- SMS failures do not roll back a successful calendar booking. The SMS error is stored on the booking for follow-up.

## Deployment

Railway can run the included `Procfile` or `railway.json`:

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set all `.env` values in Railway secrets. For service account JSON, prefer the base64 env vars so secrets are not committed.

## Known Limitations

- Service matching is simple alias/fuzzy matching, not production NLU.
- Admin auth is one shared API key, not per-clinic users.
- Provider retries are synchronous; production should use a queue for Calendar/SMS retries.
- Tests mock external providers; `scripts/verify_integrations.py` is the real integration smoke test.

