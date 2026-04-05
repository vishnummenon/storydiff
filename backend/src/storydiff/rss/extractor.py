"""Full-text article extraction using trafilatura."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from urllib.parse import urlparse

import httpx
import trafilatura

logger = logging.getLogger(__name__)


def _decode_google_news_url(url: str) -> str | None:
    """Attempt to decode the real article URL from a Google News RSS link.

    Google News RSS encodes the destination URL in a base64 blob within the path.
    The blob is a protobuf where the URL appears as a UTF-8 string starting with 'http'.
    """
    import base64

    try:
        # Extract the base64 segment from /rss/articles/<blob>?...
        path = urlparse(url).path
        if "/articles/" not in path:
            return None
        blob = path.split("/articles/")[1].split("?")[0]
        # Pad base64 and decode
        padded = blob + "=" * (-len(blob) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        # Scan decoded bytes for a URL (starts with 'http')
        text = decoded.decode("utf-8", errors="ignore")
        for candidate in text.split("\x00"):
            for part in candidate.split("\n"):
                part = part.strip()
                if part.startswith("http://") or part.startswith("https://"):
                    return part
    except Exception:
        pass
    return None


def resolve_url(url: str, user_agent: str = "StoryDiff/0.1") -> str:
    """Resolve a Google News redirect URL to the actual article URL.

    Google News RSS links use JS-based redirects that can't be followed via HTTP.
    We decode the URL from the base64-encoded path instead.
    Non-Google URLs are returned as-is.
    """
    parsed = urlparse(url)
    if "news.google.com" not in parsed.netloc:
        return url

    decoded = _decode_google_news_url(url)
    if decoded:
        logger.debug("Resolved Google News URL: %s → %s", url[:80], decoded[:80])
        return decoded

    # Fallback: try HTTP redirect
    try:
        with httpx.Client(
            follow_redirects=True,
            timeout=15.0,
            headers={"User-Agent": user_agent},
        ) as client:
            resp = client.head(url)
            final_url = str(resp.url)
            if "news.google.com" not in final_url:
                return final_url
    except Exception:
        pass

    logger.warning("Could not resolve Google News URL: %s", url[:80])
    return url


class TextExtractor:
    """Fetches article URLs and extracts body text with per-domain rate limiting."""

    def __init__(self, delay_seconds: float = 2.0, user_agent: str = "StoryDiff/0.1"):
        self._delay = delay_seconds
        self._user_agent = user_agent
        self._last_fetch: dict[str, float] = defaultdict(float)

    def _domain(self, url: str) -> str:
        return urlparse(url).netloc

    def _wait_for_domain(self, url: str) -> None:
        domain = self._domain(url)
        elapsed = time.monotonic() - self._last_fetch[domain]
        if elapsed < self._delay:
            time.sleep(self._delay - elapsed)
        self._last_fetch[domain] = time.monotonic()

    def extract(self, url: str) -> tuple[str | None, str]:
        """Fetch and extract article body text.

        Returns (extracted_text_or_None, resolved_url).
        The resolved URL should be used as the canonical article URL.
        """
        resolved = resolve_url(url, self._user_agent)
        try:
            self._wait_for_domain(resolved)
            downloaded = trafilatura.fetch_url(resolved)
            if not downloaded:
                logger.warning("Failed to download: %s", resolved)
                return None, resolved
            text = trafilatura.extract(downloaded)
            if not text:
                logger.warning("Failed to extract text: %s", resolved)
                return None, resolved
            return text, resolved
        except Exception:
            logger.warning("Extraction error for %s", resolved, exc_info=True)
            return None, resolved
