# CORE Round 2 — Dental Appointment Booking Agent
## Master Implementation Plan (hand this directly to a coding agent)

**Candidate context:** Round 1 (SmileCare Dental chatbot) was already built and submitted in Node.js/Express. Round 2 is a **new, separate project** in **Python (FastAPI)**, reflecting production stack experience (FastAPI, LangGraph, LangChain). Do not reuse Round 1's code — only the concept of business data (services, hours).

**Time limit:** 48 hours. This plan is sequenced so the *pass criteria* (live deployment + all 6 features + clean architecture + a Loom that shows understanding) are secured early, with polish saved for the end.

---

## 0. How to use this document

Paste this whole file into your coding agent (Claude Code / Cursor / Codex) as the system spec, one phase at a time. Each phase has:
- **Objective** — what "done" means
- **Tasks** — concrete steps
- **Deliverable** — what should exist on disk / be verifiable after the phase
- **Rubric link** — which of the 100 points this phase protects

Do not let the agent skip ahead to deployment before Phases 1–8 are locally verified — a broken live demo costs 40 points, the single biggest line item.

---

## 1. Rubric-to-architecture mapping (read this before writing any code)

| Rubric area | Points | What actually satisfies it |
|---|---|---|
| Working end-to-end (live demo) | 40 | Public URL + webhook simulator hits it + booking appears in real Google Calendar + real SMS sent via Twilio + Firestore has the log |
| Architecture (scale to 1,000 clinics) | 20 | Every data model is scoped by `clinic_id`; conversation state stored per `call_id`/`session_id`, not in-process memory; config (calendar ID, business hours, services) is data, not hardcoded |
| Code quality & organization | 15 | Layered structure (routes → services → repositories), no 800-line files, typed models (Pydantic) |
| Documentation | 15 | README lets a stranger clone, configure `.env`, run, and understand the design in <10 min |
| Smart use of AI tools | 10 | Visible in commit messages / Loom: what you asked AI to do, what you corrected, why |

**Design principle that satisfies the "1,000 clinics" question:** treat SmileCare Dental as *tenant #1* even though only one clinic exists. Every Firestore document, every calendar lookup, every SMS template pulls from a `clinics/{clinic_id}` config record instead of hardcoded constants. This single decision earns most of the 20 architecture points and costs almost nothing extra to build now vs. later.

---

## 2. Tech stack (final)

- **Language/framework:** Python 3.11+, FastAPI, Uvicorn
- **State management:** Conversation state machine — plain Python (a small explicit state class + Firestore-backed persistence) is enough; LangGraph is optional polish if time allows in the last hours, not a Phase 1–8 dependency. **Do not let LangGraph become a blocker** — a hand-rolled state machine is simpler to explain, debug, and finish under 48 hours, and is just as valid architecturally.
- **Calendar:** Google Calendar API v3, service account auth (`google-api-python-client`, `google-auth`)
- **SMS:** Twilio Python SDK, trial account + verified test number
- **Database/logs:** Firebase Admin SDK → Firestore
- **Deployment:** Railway (simplest for FastAPI + secrets; Render is a fine backup)
- **Validation:** Pydantic v2 models throughout
- **Testing:** Pytest + `httpx.AsyncClient` for endpoint tests; a manual VAPI-payload simulator script

---

## 3. Understanding the VAPI webhook contract (researched — use this, don't guess)

VAPI does **not** send a simple `{message: "book me an appointment"}` payload. Its server webhook (`POST /server` on your side, configured as your assistant's Server URL) sends a JSON body shaped like:

```json
{
  "message": {
    "type": "tool-calls",
    "call": { "id": "call_abc123", "customer": { "number": "+911234567890" } },
    "toolCallList": [
      {
        "id": "toolcall_xyz",
        "name": "collect_booking_info",
        "arguments": { "field": "service", "value": "Root Canal" }
      }
    ]
  }
}
```

Key `message.type` values relevant to this assignment:
- **`assistant-request`** — VAPI asks your server which assistant/config to use for an inbound call. Must respond within ~7.5s.
- **`tool-calls`** — the assistant (LLM) decided to call one of your defined "tools" (functions) mid-conversation, e.g. `save_patient_name`, `select_service`, `pick_datetime`, `confirm_booking`. **This is the mechanism you use to drive the multi-turn flow.** You respond with:
  ```json
  { "results": [ { "toolCallId": "toolcall_xyz", "result": "Got it, what service would you like?" } ] }
  ```
- **`status-update`** — call lifecycle events (started, ended, etc.)
- **`end-of-call-report`** — fires once, with the full transcript/summary when the call ends. Good secondary trigger for a final Firestore log write.

**Architecture decision:** simulate a real VAPI assistant with 4 custom tools mapped to your 4 conversation stages:
1. `collect_patient_name`
2. `collect_service`
3. `collect_datetime`
4. `confirm_and_book`

Since you won't have a live VAPI phone number, you'll **simulate** these webhook calls with a test script/Postman collection that POSTs realistic `tool-calls` payloads in sequence, using a consistent `call.id` to represent one caller's session — mirroring exactly what real VAPI would send. Document this clearly in the README as "simulated VAPI webhook, real payload shape" since the brief explicitly says to simulate the format.

Also implement `assistant-request` minimally (return a static assistant config) — it's low effort and shows you read the actual docs rather than inventing a shape.

---

## 4. Project structure

```
dental-booking-agent/
├── app/
│   ├── main.py                     # FastAPI app instantiation, router mounting
│   ├── config.py                   # env var loading (Pydantic Settings)
│   ├── routes/
│   │   ├── webhook.py              # POST /webhook/vapi
│   │   ├── admin.py                # GET /admin/bookings, /admin/conversations/{call_id}
│   │   └── health.py               # GET /health
│   ├── models/
│   │   ├── conversation.py         # ConversationState, Stage enum, TurnLog
│   │   ├── booking.py              # Booking, BookingStatus
│   │   └── clinic.py               # ClinicConfig (multi-tenant shape)
│   ├── services/
│   │   ├── vapi_service.py         # parses VAPI payloads, builds tool responses
│   │   ├── conversation_service.py # state machine transitions, slot extraction
│   │   ├── calendar_service.py     # Google Calendar API wrapper
│   │   ├── sms_service.py          # Twilio wrapper
│   │   └── intent_service.py       # mock/simple NLU: name/date/service extraction
│   ├── repositories/
│   │   ├── firestore_client.py     # Firebase Admin init (singleton)
│   │   ├── conversation_repo.py    # CRUD for conversation state in Firestore
│   │   └── booking_repo.py         # CRUD for bookings in Firestore
│   ├── utils/
│   │   ├── date_parser.py          # "tomorrow at 3pm" → ISO datetime, with clinic tz
│   │   ├── validators.py
│   │   └── logger.py
│   └── data/
│       └── clinics.json            # seed data: SmileCare Dental config (services, hours, tz)
├── tests/
│   ├── test_webhook.py
│   ├── test_conversation_service.py
│   ├── test_calendar_service.py    # mocks Google API
│   └── simulate_call.py            # scripted multi-turn VAPI payload sequence
├── scripts/
│   └── seed_firestore.py           # loads clinics.json into Firestore once
├── .env.example
├── .gitignore
├── requirements.txt
├── Procfile / railway.json
└── README.md
```

**Rubric link:** this structure alone directly satisfies "Code quality and organization — not a single 800-line file" (15 pts) and materially supports the 20-pt architecture score.

---

## 5. Data model (Firestore collections)

```
clinics/{clinic_id}
  name, timezone, operating_hours, services[], phone, email, calendar_id

conversations/{call_id}
  clinic_id, caller_number, stage, slots: { patient_name, service, datetime },
  created_at, updated_at, turns: [ {role, message, timestamp} ]   # or subcollection if it grows

bookings/{booking_id}
  clinic_id, call_id, patient_name, service, start_time, end_time,
  google_event_id, sms_sid, status (confirmed/failed), created_at
```

Using `call_id` as the conversation key (not a random session token) mirrors how VAPI actually identifies a call — this is a detail worth mentioning in the Loom as evidence of understanding the real webhook contract, not just building a generic chatbot.

**Stage enum** (drives the state machine):
```
AWAITING_NAME → AWAITING_SERVICE → AWAITING_DATETIME → AWAITING_CONFIRMATION → BOOKED
```
Each incoming `tool-calls` webhook is routed based on the conversation's current `stage`, extracts/validates the relevant slot, and either advances the stage or re-prompts on invalid input (e.g., booking outside operating hours, unknown service name).

---

## Phase 0 — Research & account setup (do this first, ~1–2 hrs)

**Objective:** every external credential exists and is verified working *before* writing business logic, so integration isn't blocked at hour 40.

**Tasks:**
1. Google Cloud: create a project → enable Google Calendar API → create a **service account** → download JSON key → share your personal test Google Calendar with the service account email (Editor access). Verify with a 5-line throwaway script that you can insert an event.
2. Twilio: create trial account → verify your own phone number as the test recipient (trial accounts can only SMS verified numbers) → note Account SID, Auth Token, and the Twilio trial phone number. Verify with a throwaway script that you can send one SMS.
3. Firebase: create a project → enable Firestore (native mode) → generate a service account key for Firebase Admin SDK. Verify with a throwaway script that you can write/read one document.
4. Re-read VAPI docs sections: **Server URL**, **Server Message → tool-calls**, **Server authentication**. Confirm the payload shapes in Section 3 above against `https://docs.vapi.ai/api-reference/webhooks/server-message`.
5. Create Railway account, link GitHub (don't deploy yet — just confirm access).

**Deliverable:** a `scripts/verify_integrations.py` (or three tiny standalone scripts) proving Calendar, Twilio, and Firestore each work in isolation, plus a `.env` populated with real test credentials (never committed).

**Rubric link:** protects the 40-pt live-demo score by front-loading the riskiest unknowns.

---

## Phase 1 — Project scaffolding

**Tasks:**
1. `git init`, initial commit, `.gitignore` (`.env`, `__pycache__/`, `*.pyc`, service-account JSON files, `venv/`).
2. Create the folder structure from Section 4.
3. `requirements.txt`: `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `google-api-python-client`, `google-auth`, `twilio`, `firebase-admin`, `python-dotenv`, `pytest`, `httpx`, `python-dateutil`, `pytz`.
4. `app/config.py` using `pydantic-settings` to load all env vars (Google creds path, Twilio SID/token/number, Firebase creds path, default clinic ID, timezone).
5. Minimal `app/main.py` with `/health` returning `{"status": "ok"}`. Run locally, confirm it boots.
6. Commit: "Project scaffolding + health check."

**Deliverable:** `uvicorn app.main:app --reload` runs; `GET /health` returns 200 locally.

**Rubric link:** Project setup & Git initialization pattern from Round 1 carried forward as a habit — supports code quality (15) and shows good AI-assisted workflow via clean incremental commits (10).

---

## Phase 2 — Business data & clinic model (multi-tenant foundation)

**Tasks:**
1. `app/models/clinic.py`: `ClinicConfig` Pydantic model (id, name, timezone, operating_hours per weekday, services list, phone, email, google_calendar_id).
2. `app/data/clinics.json`: seed SmileCare Dental as `clinic_id: "smilecare_dental"` using the business context from the Round 1 doc (Mon–Fri 10AM–7PM, 4 services, phone, email).
3. `scripts/seed_firestore.py`: loads this JSON into the `clinics/` Firestore collection once.
4. A tiny `clinic_repo.py` (or fold into config) to fetch clinic config by `clinic_id` — this is what every other service will call instead of hardcoding "SmileCare Dental" strings.

**Deliverable:** running the seed script populates Firestore with one clinic document you can view in the Firebase console.

**Rubric link:** this is the single biggest lever for the 20-pt "scalable to 1,000 clinics" score — call it out explicitly in the Loom.

---

## Phase 3 — Conversation state machine (the core of the assignment)

**Tasks:**
1. `app/models/conversation.py`: `Stage` enum (as in Section 5), `ConversationState` Pydantic model, `TurnLog` model.
2. `app/repositories/conversation_repo.py`: `get_or_create(call_id, clinic_id)`, `update(call_id, ...)`, `append_turn(call_id, turn)` — all against Firestore.
3. `app/services/conversation_service.py`: pure logic, no HTTP/Firestore imports directly — takes current state + new input, returns (new_state, reply_text). This separation is what makes the code testable and defensible in the Loom ("business logic isn't coupled to the webhook transport").
4. Slot extraction per stage:
   - `AWAITING_NAME`: take raw text as name (light validation — non-empty, no digits-only).
   - `AWAITING_SERVICE`: fuzzy-match against the clinic's services list (simple substring/closest-match is fine — mention in Loom that a production version would use embeddings or the LLM's own structured output).
   - `AWAITING_DATETIME`: use `date_parser.py` (dateutil + pytz) to resolve "tomorrow 3pm" etc. into an ISO datetime in the clinic's timezone; reject anything outside operating hours and re-prompt.
   - `AWAITING_CONFIRMATION`: yes/no.
5. Unit tests in `tests/test_conversation_service.py` for each stage transition, including invalid-input re-prompt paths.

**Deliverable:** `pytest tests/test_conversation_service.py` all green — the state machine works fully in isolation before touching webhooks.

**Rubric link:** Intent handling (15) + Business logic implementation (20 — from Round 1's framing, now mapped to "multi-turn conversation state," 20 pts here too) + Architecture (state persisted per call_id, not in memory — directly answers "how does this scale").

---

## Phase 4 — Webhook intake endpoint (VAPI format)

**Tasks:**
1. `app/services/vapi_service.py`: parse incoming `message.type`; for `tool-calls`, extract `call.id`, `toolCallList[].id`, `toolCallList[].arguments`; build the `{"results": [{"toolCallId", "result"}]}` response shape.
2. `app/routes/webhook.py`: `POST /webhook/vapi` — routes by `message.type`:
   - `assistant-request` → return a minimal static assistant config (proves you understood this event exists, low effort).
   - `tool-calls` → load/create conversation state for `call.id`, feed the tool's arguments through `conversation_service`, persist the updated state, log the turn, return the VAPI-shaped tool result.
   - `end-of-call-report` → write the full transcript/summary to the conversation doc, mark it closed.
   - anything else → `200 {"received": true}` (never 4xx/5xx on unknown types — VAPI expects acknowledgment).
3. Input validation with Pydantic — malformed payloads return 400 with a clear error, not a stack trace.
4. `tests/simulate_call.py`: a script that fires a realistic sequence of 4 `tool-calls` payloads (name → service → datetime → confirm) at `/webhook/vapi` using one consistent `call.id`, printing each response — this becomes both your test tool and your Loom demo script.

**Deliverable:** running `simulate_call.py` against local server drives a conversation from start to `BOOKED` stage purely through webhook calls, matching real VAPI payload shape.

**Rubric link:** Webhook intake requirement (part of the 40-pt live-demo core) + shows independent API research (part of the 10-pt AI-tool-usage score, since this is exactly the kind of unfamiliar-API research the brief calls out).

---

## Phase 5 — Google Calendar integration (real, not mocked)

**Tasks:**
1. `app/services/calendar_service.py`: service-account auth via `google-auth`; `create_event(clinic_config, booking)` inserts a real event into the clinic's `google_calendar_id`, with title (`"{service} - {patient_name}"`), description, start/end (default 30–60 min slot), and timezone.
2. Wire into `conversation_service`: on `AWAITING_CONFIRMATION` → yes, call `calendar_service.create_event`, get back the `event_id`.
3. Handle and surface calendar API failures gracefully (network error, invalid calendar ID) — return a spoken-friendly error via the tool result, don't crash the webhook.
4. `tests/test_calendar_service.py`: mock the Google API client, verify correct payload construction (don't hit the real API in CI).

**Deliverable:** running `simulate_call.py` end-to-end produces a real, visible event on your test Google Calendar.

**Rubric link:** Core requirement #3 (real calendar booking) — part of the 40-pt live-demo gate; this is a **pass/fail** item, not partial credit.

---

## Phase 6 — Twilio SMS confirmation

**Tasks:**
1. `app/services/sms_service.py`: Twilio client wrapper, `send_confirmation(to_number, booking)` with a templated message ("Hi {name}, your {service} appointment at SmileCare Dental is confirmed for {datetime}. Reply to reschedule.").
2. Wire into `conversation_service`/webhook flow: fires immediately after successful calendar booking.
3. Handle Twilio failures without crashing the booking flow — a failed SMS shouldn't undo a successful calendar booking; log the failure and continue (mention this tradeoff explicitly in the Loom).
4. Use `call.customer.number` from the VAPI payload as the SMS recipient when available; fall back to a configured test number for the simulator.

**Deliverable:** running `simulate_call.py` results in a real SMS landing on your verified Twilio test number.

**Rubric link:** Core requirement #4 — same pass/fail weight inside the 40-pt live-demo score.

---

## Phase 7 — Firestore conversation & booking logging

**Tasks:**
1. `app/repositories/booking_repo.py`: `create(booking)`, `list_by_clinic(clinic_id)`, `get(booking_id)`.
2. Every webhook turn already appends to `conversations/{call_id}.turns[]` (built in Phase 3/4) — confirm this is actually persisting, not just in-memory.
3. On successful booking, write a `bookings/{booking_id}` document capturing the Calendar `event_id` and Twilio `sms_sid` for traceability (useful for admin API + debugging).

**Deliverable:** after `simulate_call.py`, Firestore console shows one `conversations` doc with 4 turns and one `bookings` doc, both scoped to `clinic_id: "smilecare_dental"`.

**Rubric link:** Core requirement #5 — same pass/fail weight; also directly supports the 15-pt documentation/architecture story ("full audit trail per caller").

---

## Phase 8 — Admin REST API

**Tasks:**
1. `app/routes/admin.py`:
   - `GET /admin/clinics/{clinic_id}/bookings` — list all bookings for a clinic (this is the multi-tenant-aware version of "view all bookings").
   - `GET /admin/clinics/{clinic_id}/conversations` — list conversation summaries.
   - `GET /admin/conversations/{call_id}` — full conversation history/state for one caller/session (matches the brief's exact wording).
2. Pagination via simple `limit`/`offset` query params (even a basic version signals scale-awareness).
3. Basic API-key header check (`X-Admin-Key`) so the admin API isn't wide open on a public URL — small effort, real credit under "sound architecture."

**Deliverable:** `curl` against the deployed admin endpoints returns real booking/conversation data.

**Rubric link:** Core requirement #6 — pass/fail inside the 40-pt score; the API-key touch also strengthens the 20-pt architecture score.

---

## Phase 9 — Validation, error handling, resilience

**Tasks:**
1. Global FastAPI exception handler → consistent JSON error shape, never leaks stack traces.
2. Pydantic validation on every request body; 422 on bad input.
3. Idempotency guard: if the same `call.id` + stage is hit twice (VAPI/webhooks can retry), don't double-book or double-SMS — check current stage before acting.
4. Timeouts/retries around external calls (Calendar, Twilio) so one slow provider doesn't hang the webhook past VAPI's response expectations.
5. Structured logging (`utils/logger.py`) — every webhook hit logs `call_id`, `stage`, `type`, duration.

**Deliverable:** deliberately POST malformed/duplicate payloads via `simulate_call.py` variants and confirm graceful handling (no 500s, no duplicate bookings).

**Rubric link:** Error handling & validation was 10 pts in Round 1's rubric and remains an explicit dimension of "clean, defensible architecture" here (part of the 20-pt architecture + 15-pt code quality scores).

---

## Phase 10 — Automated tests

**Tasks:**
1. `tests/test_webhook.py`: full `assistant-request` → `tool-calls` (×4) → `end-of-call-report` sequence via `httpx.AsyncClient`, with Calendar/Twilio mocked, asserting final Firestore state (or a repo-layer mock).
2. Keep `tests/simulate_call.py` as the **real-integration** smoke test (hits actual Google/Twilio/Firestore) — run manually before each deployment, not in CI.
3. `pytest` should pass cleanly with mocks; note in README which tests are unit (mocked, safe for CI) vs. integration (real, costs a real SMS).

**Deliverable:** `pytest` green locally.

**Rubric link:** Code quality (15) — visible test discipline is one of the clearest "not just assembled it" signals for the AI-tool-usage score too.

---

## Phase 11 — Deployment (Railway)

**Tasks:**
1. `Procfile` or `railway.json`: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
2. Set all env vars (Google service account JSON as a base64-encoded env var or Railway's file-mount secret, Twilio creds, Firebase creds, admin API key) in Railway's dashboard — never commit secrets.
3. Deploy, confirm `GET https://<your-app>.up.railway.app/health` returns 200 publicly.
4. Run `simulate_call.py` **against the live URL** (not localhost) — this is what actually satisfies "reachable via a public URL" and the 40-pt live-demo criterion. Confirm calendar event, SMS, and Firestore doc all land for real.
5. Point a real VAPI assistant's Server URL at this deployed endpoint if you have time/access, as extra credibility (optional, not required by the brief).

**Deliverable:** a public URL where the full flow works end-to-end, verified live, not just locally.

**Rubric link:** this phase alone gates the entire 40-pt "working end-to-end (live demo)" line.

---

## Phase 12 — README & documentation

**Tasks:** Write a README with:
1. One-paragraph architecture summary + a simple diagram (ASCII or Mermaid) of: VAPI webhook → FastAPI routes → conversation service (state machine) → Calendar/Twilio/Firestore.
2. Setup instructions: clone, `pip install -r requirements.txt`, `.env` from `.env.example`, how to get each of the 3 credentials (Google service account, Twilio trial, Firebase Admin key).
3. How to run locally, how to run `simulate_call.py`, how to run tests.
4. API reference: every route, method, expected payload shape, example curl.
5. **Explicit "Design Decisions & Tradeoffs" section** — this is what the rubric's Note on Approach is fishing for. Cover: why a hand-rolled state machine over LangGraph (simplicity/debuggability under time pressure), why `clinic_id` scoping everywhere (multi-tenant readiness), what you'd add with more time (retry queues for SMS failures, real NLU instead of substring matching, per-clinic rate limiting, auth on the admin API beyond a single shared key).
6. Known limitations, explicitly listed (better to name them than have them discovered).

**Deliverable:** a stranger could clone the repo and be running it in under 10 minutes without asking you anything.

**Rubric link:** Documentation is a dedicated 15-pt line item — don't leave this to the last 10 minutes.

---

## Phase 13 — Loom video (2 minutes, scripted)

**Tasks:** Record covering, in order:
1. (15s) What you built, one sentence.
2. (45s) Architecture: walk through the diagram from the README — webhook → state machine → integrations — and *why* you structured conversation state as `call_id`-keyed Firestore documents instead of in-memory (survives restarts, horizontally scalable, one clinic's traffic never touches another's).
3. (30s) How this scales to 1,000 clinics: `clinic_id` on every document, config-driven business data instead of hardcoded constants, admin API already clinic-scoped.
4. (20s) Tradeoffs made under the time limit: name 2–3 honestly (e.g., substring service-matching instead of real NLU, no retry queue on SMS failure, single shared admin API key instead of per-clinic auth).
5. (10s) Live demo: hit the deployed `/webhook/vapi` (or show `simulate_call.py` output against the live URL), then show the resulting Calendar event, SMS, and Firestore doc on screen.

**Deliverable:** Loom link ready to submit.

**Rubric link:** Directly graded (part of "Smart use of AI tools," 10 pts) and is also explicitly named as a pass/fail requirement — "a Loom video that makes it clear you understand what you built."

---

## Phase 14 — Final submission checklist

- [ ] Public Railway URL live and returns 200 on `/health`
- [ ] `simulate_call.py` run **against the live URL** produces: Calendar event ✅, SMS received ✅, Firestore `conversations` + `bookings` docs ✅
- [ ] All 6 core features functioning: webhook intake, multi-turn state, calendar booking, SMS, Firestore logging, admin API
- [ ] GitHub repo public (or shared) with visible incremental commit history — not one giant commit
- [ ] README complete per Phase 12
- [ ] Loom recorded and linked
- [ ] `.env`, service-account JSON files, and secrets confirmed **not** committed (`git log --all --full-history -- .env` should be empty)
- [ ] `pytest` passes clean

---

## Appendix A — Prompt block to hand a coding agent per phase

When you hand this file to Claude Code/Cursor/Codex, prefix each phase with something like:

> "We're on Phase N of the plan below. Implement only this phase. Don't touch files outside its scope. After implementing, tell me exactly how to verify the Deliverable, and run any tests yourself first."

This keeps the agent from sprawling across phases and matches how the brief wants you to demonstrate deliberate, incremental use of AI tools (visible in commit history).

## Appendix B — Things that will cost you points if skipped

1. Hardcoding "SmileCare Dental" as a string anywhere instead of pulling from clinic config — kills the architecture score even if everything else works.
2. Mocking Google Calendar or Twilio "to save time" — the brief says explicitly **no mocked calendar logic**; this is graded as pass/fail, not partial credit.
3. Testing only against `localhost` and never actually verifying the deployed URL — the 40-pt criterion is about the **live** demo.
4. A README that explains what the code does but not *why* you made the decisions you did — the rubric explicitly rewards judgment/tradeoff articulation over checklist completion.
