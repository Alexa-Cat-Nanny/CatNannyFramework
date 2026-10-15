"""Read models for frontend pages; all queries remain scoped to the demo cat."""
import json
from datetime import datetime
from catnanny.config import DEFAULT_CAT_ID, DEFAULT_HOUSEHOLD_ID
from catnanny.storage.database import get_connection
from catnanny.services.conversation_service import ConversationNotFound, get_conversation
from catnanny.services.profile_service import owned_cat


def event_page(limit=50, offset=0, start: datetime | None = None, end: datetime | None = None, cat_id=DEFAULT_CAT_ID):
    owned_cat(cat_id)
    clauses = ["household_id=?", "cat_id=?"]
    params = [DEFAULT_HOUSEHOLD_ID, cat_id]
    for value, operator in [(start, ">="), (end, "<")]:
        if value:
            clauses.append(f"julianday(ts){operator}julianday(?)")
            params.append(value.isoformat())
    where = " AND ".join(clauses)
    with get_connection() as conn:
        conn.execute("BEGIN")
        total = conn.execute(f"SELECT COUNT(*) FROM events WHERE {where}", params).fetchone()[0]
        query = f"SELECT * FROM events WHERE {where} ORDER BY julianday(ts) DESC,event_id DESC"
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params = [*params, limit, offset]
        rows = conn.execute(query, params).fetchall()
        items = [_event_view(conn, row) for row in rows]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def _event_view(conn, row):
    progress = conn.execute("SELECT status,unknown_fields FROM event_progress WHERE event_id=?", (row["event_id"],)).fetchone()
    photos = conn.execute("SELECT photo_id,url,uploaded_at FROM photos WHERE event_id=? ORDER BY uploaded_at", (row["event_id"],)).fetchall()
    cat=owned_cat(row["cat_id"])
    return {"event_id": row["event_id"], "cat_id": row["cat_id"], "cat_name":cat.name, "reporter":row["reporter"], "event_type": row["type"],
            "occurred_at": row["ts"], "details": json.loads(row["details"]), "source": row["source"],
            "status": progress["status"] if progress else "legacy",
            "unknown_fields": json.loads(progress["unknown_fields"]) if progress else [],
            "photos": [dict(photo) for photo in photos]}


def event_detail(event_id, cat_id=None):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM events WHERE event_id=? AND household_id=?",
                           (event_id, DEFAULT_HOUSEHOLD_ID)).fetchone()
        if row is None or (cat_id and row["cat_id"]!=cat_id):
            raise ConversationNotFound("Event not found")
        return _event_view(conn, row)


def conversation_messages(session_id, limit=50, offset=0, cat_id=None):
    get_conversation(session_id,cat_id)
    with get_connection() as conn:
        if not conn.execute("SELECT 1 FROM conversation_sessions WHERE session_id=?", (session_id,)).fetchone():
            raise ConversationNotFound("Session not found")
        total = conn.execute("SELECT COUNT(*) FROM conversation_turns WHERE session_id=?", (session_id,)).fetchone()[0]
        rows = conn.execute("SELECT request_id,payload,response,recorded_at FROM conversation_turns WHERE session_id=? ORDER BY turn_id LIMIT ? OFFSET ?",
                            (session_id, limit, offset)).fetchall()
        items = [{"request_id": row["request_id"], "text": json.loads(row["payload"])["text"],
                  "submitted_details": json.loads(row["payload"])["details"],
                  "recorded_at": row["recorded_at"], "response": json.loads(row["response"])} for row in rows]
    return {"items": items, "total": total, "limit": limit, "offset": offset}
