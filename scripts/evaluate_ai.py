"""Explicit opt-in live extraction eval; does not write health events."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description="Live API evaluation (requires key; incurs API usage).")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--env-file")
    args = parser.parse_args()
    if not args.live:
        parser.error("Pass --live to explicitly run paid API requests.")
    if args.env_file:
        from dotenv import load_dotenv
        load_dotenv(args.env_file)
    from catnanny.services.ai_extraction_service import extract_turn, get_ai_settings
    from catnanny.domain.schemas import ConversationRequest
    from catnanny.domain.extraction import ExtractionError
    settings = get_ai_settings()
    if settings.provider != "openai" or not settings.api_key or not settings.model:
        parser.error("Configure CATNANNY_EXTRACTION_PROVIDER=openai, OPENAI_API_KEY and OPENAI_MODEL first.")
    root = Path(__file__).resolve().parents[1]
    cases = json.loads((root / "examples/ai_eval_cases.json").read_text(encoding="utf-8"))
    results = []
    for case in cases:
        state = {"event_id": None, "event_type": None, "details": {}, "unknown_fields": [],
                 "pending_field": None, "occurred_at": None, **case["state"]}
        try:
            event_type, updates, _, _, clarification = extract_turn(
                ConversationRequest(request_id=uuid4().hex, text=case["text"]), state, [])
            passed = (event_type == case["expected_type"] and updates == case["expected_updates"]
                      and bool(clarification) == case["clarification"])
            results.append({"name": case["name"], "passed": passed,
                            "event_type": event_type, "updates": updates, "clarification": bool(clarification)})
        except ExtractionError as exc:
            results.append({"name": case["name"], "passed": False, "error_code": exc.code})
        print(case["name"], "PASS" if results[-1]["passed"] else "FAIL")
    directory = root / "data" / "evaluations"
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"live-{uuid4().hex}.json"
    target.write_text(json.dumps({"model": settings.model, "time": datetime.now(timezone.utc).isoformat(),
                                 "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Results: {target}")
    return 0 if all(item["passed"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
