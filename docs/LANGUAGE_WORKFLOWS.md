# Language-first care workflows and subject correction

The website simulates text transcribed from an Alexa conversation. The management
buttons are shortcuts; supported language requests use the same conversation core.
This does not mean a live Echo/Alexa+ integration has been deployed or verified.

## UI-to-language mapping

| Website control | Language example | Core behavior |
|---|---|---|
| Add companion | “Add a cat named Jeremy.” | Create/select the profile without creating a health event |
| Add/select caregiver | “I am Sam.” / “Add a caregiver named Sam.” | Create/select a local caregiver and attribute future turns |
| Select companion | “Switch to Jeremy.” | Select the cat without moving an existing observation |
| New observation | “Start a new observation.” | Start a separate event context; prior events remain |
| Care log | “Show the care log.” | Request the current cat's history |
| Request report | “Show me Jeremy's care report for the last 7 days.” | Request only that cat's report; default seven days |
| HTML/JSON download | “Download Jeremy's care report.” / “Export the report as JSON.” | Explicit download request; no automatic email or SMS |
| Photo link | “Send me the photo link.” | Display a simulated upload card for the current event |
| Refresh record/photos | “Refresh the current record.” | Reload the current event |

Photo capture and file upload remain a phone/browser step. Voice can request the
link; this simulator does not pretend that Alexa has taken or uploaded a photo.
Real SMS/email delivery and authenticated speaker identification remain separate work.
Caregiver selection/declaration is attribution, not proof of identity.

Common management expressions are routed locally. In OpenAI mode, less direct
management phrasing can be classified through a separate strict structured-output
schema. Names and action evidence are checked against the user's text. Normal
health turns keep their existing extraction path. Arbitrary wording and combined
multi-action requests are not guaranteed; current examples use one action per turn.

## Correcting a cat name is different from switching cats

Example:

1. “Mochi vomited twice.” Answer follow-up questions and optionally upload a photo.
2. “Actually I meant Jeremy, not Mochi.”
   Colloquial forms such as “No actually it is for jeremy, vomit today and
   already saw 6 times in 3 days” and “No, actually it's for Jeremy” also
   correct ownership. Lowercase names match registered names without case.
3. If Jeremy is not registered, the assistant asks whether to create Jeremy and
   move only this observation with its photos. Answer “Yes” or “No”.
4. On confirmation, the SAME event and SAME session now belong to Jeremy. Its
   details, original timestamp, reporter, and photo URLs are retained. The photo
   ownership metadata is updated too.
5. Mochi's report no longer includes this event; Jeremy's report does. Unrelated
   Mochi events are untouched. Original conversation messages are retained as
   history; an event_reassignments row records the correction.

If Jeremy is already registered, the user's explicit correction is applied to the
current event directly. A plain statement about Jeremy, without correction intent,
continues to create a separate Jeremy event rather than transferring Mochi's event.
Corrections are scoped to the active event, not all historical events for a cat.

No files or event rows are bulk-deleted. Removing the incorrect attribution is an
atomic reassignment, so photos are not orphaned and duplicates are not introduced.
Creation of an unknown target, event ownership, photo ownership, audit, and final
conversation state are committed together. Failure rolls the transaction back.
Repeated request IDs replay the original outcome rather than moving twice.

## API additions (v1.3)

Conversation status may be `awaiting_confirmation`. Clients should let the user
answer the confirmation through the same text interface. The response includes
`ui_action` and `action_payload`. On successful reassignment, these include the
old/new cat IDs and the unchanged event ID. Clients must clear stale source-cat
session mappings and update existing photo-link labels, not just append a message.

Language report/log actions return semantic UI instructions; the simulator then
fetches the corresponding read API. Historical conversation restoration does not
reopen reports or download files automatically.

`catnanny/alexa_skill/handlers.py::handle_conversation()` is a tested text-to-core
adapter that keeps backend session attributes. An actual Alexa host still needs
verified platform requests, utterance/transcription routing, response formatting,
and device/developer-console testing. Web success alone is not evidence of that.

## Verification

- `tests/test_language_actions_and_corrections.py`: unknown-target confirmation,
  same-event/photo movement, old/new reports, unrelated-event preservation,
  idempotency, cancellation, atomic rollback, language controls and Alexa adapter.
- `tests/test_openai_extraction.py`: indirect correction classification through
  the Responses API adapter with a simulated upstream response.
- `tests/frontend_behavior.test.cjs`: corrected profile, session-cache cleanup,
  and photo-card relabeling, using a local DOM test double.
- `scripts/evaluate_subject_correction.py --env-file .env --live`: opt-in small
  paid model check, with a fully separate database and sample photo. The tested
  indirect correction passed; real household data was not changed.

The browser automation policy still prevents automated visual/click verification.
The page should be tested manually for layout and actual browser interactions.

Verification on 2026-10-14: all 88 Python tests passed, all 5 JavaScript behavior
tests passed, and the isolated real-model indirect subject-correction test passed.
The local running service exposes v1.3 language management and subject correction.
Existing household records were backed up and preserved; no production event was
guessed or reassigned during implementation.
