from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any


logger = logging.getLogger("job_agent.pipeline")


def log_event(level: int, event: str, **fields: Any) -> None:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    logger.log(level, json.dumps(payload, default=str))
