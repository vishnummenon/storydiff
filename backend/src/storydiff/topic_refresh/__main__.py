"""``python -m storydiff.topic_refresh`` — run the topic refresh SQS worker."""

from __future__ import annotations

from storydiff.topic_refresh.worker import main

if __name__ == "__main__":
    main()
