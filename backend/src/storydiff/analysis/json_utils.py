"""Parse JSON from LLM responses (strip fences, take first object)."""

from __future__ import annotations

import json
import re
from typing import Any


def parse_json_object(text: str) -> dict[str, Any]:
    """Extract a single JSON object from model output."""
    raw = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fence:
        raw = fence.group(1).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model output")
    return json.loads(raw[start : end + 1])
