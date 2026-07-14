from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from backend.graph.state import StepStatus


def make_step_event(
    step: str,
    status: StepStatus,
    message: str,
    *,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "step": step,
        "status": status,
        "message": message,
        "payload": payload or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def to_sse_payload(event: dict[str, Any]) -> dict[str, Any]:
    return {"event": "step", "data": json.dumps(event)}
