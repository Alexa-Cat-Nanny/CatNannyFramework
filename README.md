# Cat Nanny

Cat Nanny is an Alexa-first cat care assistant for shared family pet care.

Daily product flow:

1. A user tells Alexa that Mochi vomited, skipped food, or got medicine.
2. Cat Nanny stores the event and applies conservative safety rules.
3. Alexa gives the user a photo upload link for that event.
4. The user uploads a phone photo.
5. Cat Nanny generates a vet-ready summary with event history and photo links.

Hackathon flow:

- Regular Alexa Custom Skill proves the real Echo voice experience.
- Self-hosted MCP server plus a web simulator satisfies the Alexa+ track.
- AWS Builder can be claimed by moving storage/photos/email to DynamoDB, S3, and SES.

## Day 1 Code Slice

This repo currently contains the first scaffold:

- Core models and safety rules
- SQLite repository skeleton
- Event logging service that returns an `event_id` and `upload_url`
- Photo upload endpoint
- Vet summary endpoint
- MCP tool wrapper skeleton
- Alexa handler adapter skeleton
- Alexa interaction model draft
- Team handoff docs

## Run Locally

Install Python 3.11+ first, then:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload
```

Create an event from PowerShell:

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/events" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{"event_type":"vomit","details":{"content":"food"},"source":"manual"}'
```

Open the returned `upload_url` on a phone or browser to attach a photo.

If you want to use real curl on Windows, call `curl.exe` explicitly:

```powershell
curl.exe -X POST "http://localhost:8000/events" `
  -H "Content-Type: application/json" `
  -d "{\"event_type\":\"vomit\",\"details\":{\"content\":\"food\"},\"source\":\"manual\"}"
```

## Docs

- `docs/ARCHITECTURE.md`: technical architecture and scope boundaries
- `docs/DAY1_HANDOFF.md`: what to tell teammates before splitting work
- `docs/DEMO_SCRIPT.md`: final demo video outline
