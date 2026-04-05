"""Feed configuration loader — reads feeds.yaml and validates entries."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FeedConfig(BaseModel):
    """Single RSS feed definition."""

    url: str
    outlet_slug: str
    category: str | None = None
    label: str | None = None
    source_map: dict[str, str] = Field(default_factory=dict)


class FeedsFile(BaseModel):
    """Top-level feeds.yaml schema."""

    feeds: list[FeedConfig]


def load_feeds(config_path: str | Path) -> list[FeedConfig]:
    """Load and validate feed definitions from a YAML file.

    Entries missing required fields are logged and skipped.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Feeds config not found: {path}")

    raw = yaml.safe_load(path.read_text())
    if not raw or "feeds" not in raw:
        raise ValueError(f"Feeds config must contain a 'feeds' key: {path}")

    valid: list[FeedConfig] = []
    for i, entry in enumerate(raw["feeds"]):
        try:
            valid.append(FeedConfig.model_validate(entry))
        except Exception as exc:
            logger.error("Skipping feed entry %d: %s", i, exc)

    return valid
