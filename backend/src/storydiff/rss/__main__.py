"""RSS feed fetcher CLI entry point.

Usage:
    python -m storydiff.rss                 # one-shot: poll all feeds once and exit
    python -m storydiff.rss --loop          # loop: poll repeatedly at configured interval
    python -m storydiff.rss --config path   # use a custom feeds.yaml
    python -m storydiff.rss --interval 600  # override poll interval (seconds)
"""

from __future__ import annotations

import argparse
import logging
import time

from storydiff.db.session import get_session_local
from storydiff.rss.config import load_feeds
from storydiff.rss.extractor import TextExtractor
from storydiff.rss.fetcher import submit_articles
from storydiff.rss.settings import load_rss_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("storydiff.rss")


def _run_once(settings_overrides: dict) -> dict[str, int]:
    settings = load_rss_settings()
    config_path = settings_overrides.get("config") or settings.feeds_config_path
    feeds = load_feeds(config_path)
    if not feeds:
        logger.warning("No valid feeds found in %s", config_path)
        return {"submitted": 0, "duplicates": 0, "errors": 0}

    extractor = TextExtractor(
        delay_seconds=settings.fetch_delay_seconds,
        user_agent=settings.user_agent,
    )

    SessionLocal = get_session_local()
    with SessionLocal() as session:
        logger.info("Polling %d feed(s)...", len(feeds))
        stats = submit_articles(feeds, extractor, settings.api_base_url, db_session=session)

    logger.info(
        "Done — submitted=%d, duplicates=%d, errors=%d",
        stats["submitted"],
        stats["duplicates"],
        stats["errors"],
    )
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="StoryDiff RSS feed fetcher")
    parser.add_argument("--loop", action="store_true", help="Poll feeds repeatedly")
    parser.add_argument("--config", type=str, help="Path to feeds.yaml")
    parser.add_argument("--interval", type=int, help="Poll interval in seconds (default: from env)")
    args = parser.parse_args()

    overrides = {"config": args.config}
    settings = load_rss_settings()
    interval = args.interval or settings.poll_interval_seconds

    if args.loop:
        logger.info("Starting RSS fetcher in loop mode (interval=%ds)", interval)
        while True:
            try:
                _run_once(overrides)
            except Exception:
                logger.error("Poll cycle failed", exc_info=True)
            logger.info("Sleeping %ds until next poll...", interval)
            time.sleep(interval)
    else:
        _run_once(overrides)


if __name__ == "__main__":
    main()
