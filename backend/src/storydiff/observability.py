"""Netra observability init helper."""

from __future__ import annotations

import os


def init_netra(service_name: str) -> None:
    """Initialize Netra tracing if NETRA_API_KEY is set.

    The import is deferred so the app starts normally when netra-sdk is absent
    or NETRA_API_KEY is not configured.
    """
    key = os.environ.get("NETRA_API_KEY", "").strip()
    if not key:
        return
    try:
        from netra import Netra  # noqa: PLC0415

        Netra.init(app_name=service_name)
    except Exception:
        pass  # Never block startup due to observability
