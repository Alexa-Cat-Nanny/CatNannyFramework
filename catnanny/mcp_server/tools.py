from typing import Any

from catnanny.services.event_service import log_health_event as log_event
from catnanny.services.report_service import build_vet_summary


def log_health_event(event_type: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """MCP tool: record a cat health observation and return follow-up guidance."""
    return log_event(event_type=event_type, details=details, source="mcp")


def get_vet_summary() -> dict[str, Any]:
    """MCP tool: return a vet-ready summary from stored Cat Nanny events."""
    return build_vet_summary()


def list_tools() -> list[dict[str, str]]:
    return [
        {
            "name": "log_health_event",
            "description": "Record vomiting, appetite, litter box, or energy observations for the user's cat.",
        },
        {
            "name": "get_vet_summary",
            "description": "Build a vet-ready timeline with event counts and linked photos.",
        },
    ]
