"""RSS fetcher settings from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_BACKEND_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class RssSettings:
    api_base_url: str
    poll_interval_seconds: int
    fetch_delay_seconds: float
    feeds_config_path: str
    user_agent: str


def load_rss_settings() -> RssSettings:
    load_dotenv(_BACKEND_ROOT / ".env")
    return RssSettings(
        api_base_url=os.environ.get("API_BASE_URL", "http://127.0.0.1:8000").strip(),
        poll_interval_seconds=int(os.environ.get("RSS_POLL_INTERVAL", "900").strip()),
        fetch_delay_seconds=float(os.environ.get("RSS_FETCH_DELAY", "2.0").strip()),
        feeds_config_path=os.environ.get(
            "RSS_FEEDS_CONFIG",
            str(_BACKEND_ROOT / "feeds.yaml"),
        ).strip(),
        user_agent=os.environ.get(
            "RSS_USER_AGENT",
            "StoryDiff/0.1 (+https://github.com/storydiff)",
        ).strip(),
    )
