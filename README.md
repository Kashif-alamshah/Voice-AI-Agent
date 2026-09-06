# Voice AI Agent — Patient Registration System

A voice-based AI agent that answers a real phone number, conversationally collects standard U.S. patient demographic information, persists it to a database, and exposes it through a REST API.

**Live Demo:**
- **Phone number:** +1 (831) 471-6102
- **API base URL:** https://vertical-accustom-morse.ngrok-free.dev
- **API docs (Swagger UI):** https://vertical-accustom-morse.ngrok-free.dev/docs
- **Repository:** https://github.com/Kashif-alamshah/Voice-AI-Agent

> **Note on deployment:** The API is exposed via an ngrok tunnel from a local machine rather than a cloud host. See [Known Limitations & Trade-offs](#known-limitations--trade-offs) for why, and please call the number / hit the API while this session is expected to be live for review.

---

## Architecture

```
Phone Call (Caller)
      │
      ▼
Vapi (Telephony + STT + LLM orchestration + TTS)
      │  (tool calls over HTTPS)
      ▼
FastAPI  ──────────────►  SQLite (patients.db)
      │
      ▼
REST API (/patients) ◄── reviewers / Swagger UI
```

- **Vapi** handles the phone number, speech-to-text, text-to-speech, and runs the conversation using an LLM (GPT-4.1) driven by a custom system prompt (included in full below).
- The LLM never touches the database directly. Instead, it calls **tools** (functions) that are backed by webhook routes on my FastAPI server:
  - `find_patient_by_phone` — checks for an existing patient before registering, enabling duplicate detection.
  - `create_patient` — saves a new patient record.
  - `update_patient` — updates an existing patient record (used both for the duplicate-detection "update instead" path, and for adding optional fields like emergency contact after the initial save).
- **FastAPI** exposes two parallel sets of routes:
  - `/patients/*` — the public REST API described in the assessment (list, get, create, update, soft-delete), independently usable and independently validated.
  - `/vapi/*` — webhook routes that Vapi's tool calls hit. These reuse the exact same Pydantic schemas and SQLAlchemy models as the public API, so validation logic is never duplicated and never bypassed just because a request came from the voice agent instead of a human calling the API directly.
- **SQLite** stores everything in a single `patients.db` file via SQLAlchemy.

### Why this separation matters
Telephony/voice logic (Vapi + system prompt), application logic (FastAPI routes), and data (SQLAlchemy models + SQLite) are cleanly separated. The `/vapi` routes are a thin adapter layer: they translate Vapi's tool-call JSON shape into calls against the same validated schemas and models the public REST API uses. Nothing about patient data validation lives inside the voice-agent layer — the LLM can be wrong, sloppy, or hallucinate a bad phone number, and the backend will still catch it and hand back a clear error string that the agent can relay to the caller.

---

## Tech Stack & Justification

| Layer | Choice | Why |
|---|---|---|
| Telephony + Voice AI | **Vapi** | Bundles phone provisioning, STT, LLM orchestration, and TTS behind a single config and tool-calling interface — by far the fastest path to a working conversational agent within a 3-hour window, versus manually wiring Twilio + Deepgram + an LLM + ElevenLabs. |
| LLM | **GPT-4.1** (via Vapi) | Reliable instruction-following for a fairly detailed system prompt with many conditional branches (validation, corrections, duplicate handling). |
| Backend | **FastAPI (Python)** | Async-friendly, automatic request validation via Pydantic, built-in interactive docs (Swagger UI) which doubled as my manual test harness throughout development. |
| Validation | **Pydantic v2** | Field-level validators let me enforce every rule in the spec (10-digit US phone, valid state abbreviation, ZIP format, DOB not in the future, name character rules) server-side, independent of whatever the voice agent sends. |
| Database | **SQLite (SQLAlchemy ORM)** | Zero setup, file-based, more than sufficient for a single-instance demo. Explicitly suggested in the assessment brief as an acceptable shortcut given the time constraint. |
| Tunneling | **ngrok** | Used to expose the local FastAPI server to the public internet for Vapi's webhook calls. See trade-offs below for why this was chosen over a cloud host. |

---

## Environment Variables

| Variable | Purpose | Required |
|---|---|---|
| `DATABASE_PATH` | Optional override for where the SQLite file is stored. Defaults to `./patients.db` if unset. | No |

No API keys are hardcoded anywhere in the source. Vapi's dashboard holds its own model/voice provider credentials independently of this repo; this repo's FastAPI service has no external credentials to manage since SQLite requires none.

---

## Setup Instructions (running it yourself)

### 1. Clone and set up the environment
```bash
git clone https://github.com/Kashif-alamshah/Voice-AI-Agent.git
cd Voice-AI-Agent/application
python -m venv venv
venv\Scripts\activate.bat        # Windows
# source venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
```

### 2. Run the API locally
```bash
uvicorn app.main:app --reload
```
Visit `http://127.0.0.1:8000/docs` to exercise the REST API directly (create, list, get, update, soft-delete a patient).

### 3. Expose it publicly (for Vapi to reach it)
In a second terminal:
```bash
ngrok http 8000
```
Copy the resulting `https://....ngrok-free.dev` forwarding URL.

### 4. Configure Vapi
1. Create a Vapi account and provision a free U.S. phone number.
2. Create an Assistant, set the model to GPT-4.1 (or GPT-4o), and paste in the system prompt below.
3. Add three tools (`find_patient_by_phone`, `create_patient`, `update_patient`) with the JSON schemas described in [Tool Definitions](#tool-definitions), each pointing its `server.url` at your ngrok URL + the matching `/vapi/...` path.
4. Assign the Assistant to your phone number.
5. Call the number.

---

## Tool Definitions

### `find_patient_by_phone`
```json
{
  "type": "object",
  "properties": {
    "phone_number": { "type": "string", "description": "The caller's 10-digit US phone number" }
  },
  "required": ["phone_number"]
}
```
Server URL: `{BASE_URL}/vapi/find_patient_by_phone`

### `create_patient`
```json
{
  "type": "object",
  "required": ["first_name", "last_name", "date_of_birth", "sex", "phone_number", "address_line_1", "city", "state", "zip_code"],
  "properties": {
    "first_name": { "type": "string" },
    "last_name": { "type": "string" },
    "date_of_birth": { "type": "string", "description": "Format MM/DD/YYYY" },
    "sex": { "type": "string", "enum": ["Male", "Female", "Other", "Decline to Answer"] },
    "phone_number": { "type": "string" },
    "email": { "type": "string" },
    "address_line_1": { "type": "string" },
    "address_line_2": { "type": "string" },
    "city": { "type": "string" },
    "state": { "type": "string" },
    "zip_code": { "type": "string" },
    "insurance_provider": { "type": "string" },
    "insurance_member_id": { "type": "string" },
    "preferred_language": { "type": "string" },
    "emergency_contact_name": { "type": "string" },
    "emergency_contact_phone": { "type": "string" }
  }
}
```
Server URL: `{BASE_URL}/vapi/create_patient`

### `update_patient`
```json
{
  "type": "object",
  "required": ["phone_number"],
  "properties": {
    "phone_number": { "type": "string", "description": "Identifies which existing patient record to update" },
    "email": { "type": "string" },
    "address_line_1": { "type": "string" },
    "address_line_2": { "type": "string" },
    "city": { "type": "string" },
    "state": { "type": "string" },
    "zip_code": { "type": "string" },
    "insurance_provider": { "type": "string" },
    "insurance_member_id": { "type": "string" },
    "preferred_language": { "type": "string" },
    "emergency_contact_name": { "type": "string" },
    "emergency_contact_phone": { "type": "string" }
  }
}
```
Server URL: `{BASE_URL}/vapi/update_patient`

`update_patient` looks the patient up by phone number rather than requiring the LLM to remember and pass back a `patient_id` parsed out of a prior tool result string — this proved far more reliable in testing, since the phone number is a concrete value the agent already holds verbatim from earlier in the call.

---

## System Prompt (full text, as configured in Vapi)

```
# IDENTITY
You are Alex, a warm and efficient patient intake coordinator for a healthcare clinic. You are speaking with callers over the phone to register them as new patients. You are not a robot reading a script — you speak naturally, like a real person who does this every day and genuinely wants to make the process easy for the caller.

# YOUR GOAL
Collect the following REQUIRED fields, in this general order, through natural conversation:
1. First name
2. Last name
3. Date of birth (must be a real past date, format it as MM/DD/YYYY)
4. Sex (Male, Female, Other, or Decline to Answer)
5. Phone number (must be a valid 10-digit US number)
6. Street address (address line 1) — must include both a number and a street name
7. City
8. State (must be a valid 2-letter US state abbreviation)
9. ZIP code (5 digits, or ZIP+4 format)

Optional fields (email, address line 2, insurance provider, insurance member ID, preferred language, emergency contact name, emergency contact phone) should NOT be asked about individually. Once all required fields are collected and confirmed, ask ONE time whether the caller would like to add any of those, letting them opt in.

# CONVERSATION STYLE
Speak in short, natural sentences. Ask ONE question at a time. Use casual acknowledgments before moving on. If the caller volunteers multiple fields at once, accept all of it and skip ahead.

# VALIDATION AND ERROR HANDLING
Validate each field as it's given, and re-ask ONLY the invalid field if something looks wrong (bad date, incomplete phone number, invalid state, malformed ZIP, unrecognized sex option, or a street address missing a street name).

# HANDLING CORRECTIONS MID-CALL
If the caller corrects themselves at any point (e.g. spelling out a name differently), acknowledge warmly and continue from where you left off — never restart the whole registration for a correction.

# HANDLING A "START OVER" REQUEST
If the caller wants to start over, say so, and restart from first name, discarding anything collected so far.

# CONFIRMATION BEFORE SAVING
Read all collected fields back to the caller and get explicit confirmation before saving anything.

# DUPLICATE DETECTION
Once you have the caller's phone number, call find_patient_by_phone before creating a new record. If a match is found, ask whether they'd like to update that existing record or if this is a new registration for a different person, and proceed accordingly.

# SAVING THE RECORD
Once confirmed, call create_patient. If it fails, apologize, retry once, and if it fails again let the caller know someone will follow up manually.

# UPDATING AN EXISTING RECORD
Use update_patient (identified by phone_number) whenever adding optional information after the initial save, or when the caller asks to update an existing record found via find_patient_by_phone — never call create_patient again for someone already registered, as that creates a duplicate.

# ENDING THE CALL
Close warmly and briefly after a successful save.

# IMPORTANT REMINDERS
Never guess or auto-fill a field the caller hasn't clearly provided. Stay warm and patient throughout.
```

*(Full verbatim version with all example phrasing is stored in the Vapi assistant config; the above is the structural summary. The complete original text is also kept in `docs/system_prompt.txt` in this repo for reference.)*

---

## Known Limitations & Trade-offs

- **Hosting:** I attempted to deploy the FastAPI backend to Render, Railway, and Fly.io. Render's free tier does not support a persistent disk (required for SQLite to survive restarts) without a payment method attached. Railway's trial had expired and required payment to redeploy. Fly.io required a payment method even to create a basic app on their free allowance. Given the 3-hour constraint, I used **ngrok** to tunnel a locally-running instance instead, which satisfies the "must be live and callable at review time" requirement without needing a funded cloud account. In a production setting, this would be resolved by using a funded account on any of the above, or a genuinely free-tier host without payment gating (e.g., a student/education plan, or self-hosting on a VPS with an existing account).
- **SQLite over Postgres:** Chosen for simplicity and because it's explicitly suggested as acceptable in the assessment brief. It would not support concurrent writes at any real scale, and a production system would use Postgres instead.
- **Soft-delete visibility inconsistency:** `GET /patients` filters out soft-deleted records, but `GET /patients/:id` does not — so a soft-deleted patient can still be fetched directly by ID. This was a deliberate minimal choice given time constraints; a production system might want consistent visibility rules across both endpoints, or a `?include_deleted=true` flag.
- **No automated test suite:** Given the time budget, testing was done manually and extensively through Vapi's call transcripts and the Swagger UI rather than through `pytest`. This is the top item in Next Steps below.
- **Multi-language support, appointment scheduling, and a dashboard UI** (all listed as bonus items in the brief) were not implemented, in favor of hardening the core registration flow, duplicate detection, and error handling first.

---

## Next Steps

If given more time, in priority order:
1. Add an automated test suite (`pytest`) covering the `/patients` REST endpoints and the validation logic in `schemas.py`.
2. Move off ngrok to a properly funded cloud deployment (Render/Fly.io/Railway with billing enabled) or switch to a hosted Postgres (e.g. Neon, Supabase) for genuine multi-restart persistence without local tunneling.
3. Add a simple read-only dashboard (bonus item) listing registered patients, since the data is already fully exposed via the REST API.
4. Add call transcript storage, linking each call's summary to the resulting patient record (bonus item).
5. Reconcile the soft-delete visibility inconsistency noted above.
6. Add basic auth / a shared-secret header check on the `/vapi/*` webhook routes so they can't be invoked by anyone who discovers the URL.
