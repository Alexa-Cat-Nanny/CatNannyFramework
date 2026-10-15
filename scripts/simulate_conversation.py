"""Run a local scenario through the same service as the HTTP endpoint."""
import argparse
import json
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from catnanny.domain.schemas import ConversationRequest
from catnanny.services.conversation_service import process_turn
from catnanny.storage.database import init_db


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=["vomit", "appetite", "unknown"], default="vomit")
    args = parser.parse_args()
    init_db()
    scenarios = json.loads((Path(__file__).resolve().parents[1] / "examples/conversations.json").read_text(encoding="utf-8"))
    session_id = None
    for text in scenarios[args.scenario]:
        response = process_turn(ConversationRequest(cat_id="mochi", request_id=uuid4().hex, session_id=session_id, text=text))
        session_id = response["session_id"]
        print(json.dumps({"user": text, "response": response}, ensure_ascii=False, indent=2))
    assert response["status"] == "completed", "Scenario did not finish"
    print("PASS: conversation completed; event is persisted.")


if __name__ == "__main__":
    main()
