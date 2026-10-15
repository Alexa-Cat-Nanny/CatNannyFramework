# Simulator guide / 多猫照护模拟器用法

> Update: language equivalents and current-event name correction are now implemented.
> See `LANGUAGE_WORKFLOWS.md` for v1.3 semantics and the distinction between web
> simulation and an actual Alexa deployment.

Open `http://localhost:8000/simulator`. The interface, questions, validation messages, and new system replies default to English. User messages retain their original language. Historical system replies are displayed with English question equivalents where available; original stored messages are preserved.

## Three concepts

- **Observation**: one episode, such as Mochi vomiting. Follow-up answers and later corrections update this same event; its photos stay attached to it.
- **Care log**: the selected cat's complete event history, with the first reporter, observation details, and photos.
- **Care report**: a requested summary of one cat's log. The default is a rolling seven days. It is fetched only when the user requests it; there is no automatic sending or scheduled report.

## Cats and identity

Add cats under **Your companions**. Names must be distinct within the local household so spoken/text names can be matched. Clicking a profile scopes the view and provides explicit subject context. The initial automatically highlighted profile does not silently identify a new conversation's subject.

Registered cat names are recognized case-insensitively in text. For example, `Mochi vomited twice` goes to Mochi. If no cat has been confirmed, `My cat vomited twice` first asks which cat; replying `Mochi` preserves the original observation and then extracts its details.

An explicit registered name overrides the active subject. Naming Jeremy while talking about Mochi starts a separate Jeremy conversation/event, preserving Mochi's previous data and context. Mentioning two registered cats triggers clarification rather than mixing observations. Explicit unfamiliar names in common supported phrases trigger a request to add or select a profile; this safeguard is not general-purpose name recognition. Do not assume arbitrary aliases or all unfamiliar-name constructions are recognized.

Once a subject is confirmed, short answers use that cat's conversation context. **New observation** starts a separate episode while retaining the confirmed subject. Selecting another profile restores that cat's most recently active local conversation when available. Prior episodes remain in its care log.

## Caregivers

Choose who is caring today or add a caregiver name. Supported language declarations such as `I am Sam` can also create/select the caregiver. Each turn records that caregiver's ID/name; the event keeps the original reporter. A different caregiver can answer follow-up questions without overwriting the original reporter. Attribution is explicitly selected or declared, not inferred from voice biometrics or authenticated identity.

This is a shared local-household demonstration, not an authenticated multi-user service. Selection provides attribution and cat filtering, not access control or verified identity.

## Photos and reports

The chat displays a **simulated text message** card. Its upload page resolves the event's actual cat, rather than a fixed demo name. Photos attach by event ID and are visible in that cat's log and report. No SMS/email is sent.

**Request care report** opens a table with time, observations/symptoms, caregiver, status, and inline photo thumbnails. The user may explicitly choose seven, thirty, or ninety days. **Download report with photos** creates a standalone English HTML file, embedding the photo bytes rather than requiring the recipient to access localhost. JSON export remains available. Nothing is sent to a vet or user email address automatically.

Times use the observation time if supplied to the API, otherwise the original logging time. Natural-language dates are not yet parsed. Reports include incomplete observations, labeled **Needs detail**. Care logs include older legacy events, labeled **Logged**.

## API behavior (v1.3)

See `TEAM_HANDOFF_CURRENT_CN.md` for the complete current API list and `LANGUAGE_WORKFLOWS.md` for management actions, `awaiting_confirmation`, `ui_action`, and current-event reassignment. Explicit correction differs from simply naming another cat for a new observation.

- `GET /cats`, `POST /cats`, `GET /cats/{cat_id}`: cat profiles.
- `GET /caregivers`, `POST /caregivers`: local caregiver profiles.
- `POST /conversations/turns`: optional `cat_id` for explicit context and `caregiver_id` for attribution. Omit cat_id to let text/session context resolve the subject. New `awaiting_cat` status means no subject is confirmed yet.
- Conversation responses include `cat_id`, `cat_name`, `caregiver_id`, and `caregiver_name`. The first two can be null while asking for a subject. An explicit cat switch can return a new session ID; clients must retain the returned ID.
- `GET /events?cat_id=...`, `GET /events/{event_id}?cat_id=...`: selected cat's events. The optional cat filter on detail enforces consistency.
- `GET /conversations/{id}?cat_id=...`, `GET /conversations/{id}/messages?cat_id=...`: optional cat consistency checks.
- `GET /reports/vet-summary?cat_id=...`: seven-day default; explicit start/end retain half-open date semantics. Legacy clients that omit cat_id still query the demo cat, but a new unscoped conversation does not silently assign it.

Database migration `002_caregivers.sql` adds a caregiver table. Cat profiles reuse the existing cats table, and event/turn relationships remain intact. Existing records and uploaded photos are not removed or renamed.

## Verification

Python tests: `./.venv/Scripts/python.exe -m pytest tests -q`.
JavaScript behavior tests (Node): `node --test tests/frontend_behavior.test.cjs`.
Tests use independent local SQLite databases and simulated AI, with no API charges or SMS/email delivery. JavaScript tests use a local DOM test double, not a live browser. Automated browser access was blocked by the browser tool's URL policy; visual layout and real browser clicks still require manual verification.
