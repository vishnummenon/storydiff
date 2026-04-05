"""Unit tests for the analysis worker Lambda handler."""

from __future__ import annotations

import json
from unittest.mock import patch

from storydiff.analysis.lambda_handler import lambda_handler

_MODULE = "storydiff.analysis.lambda_handler.process_article_analysis_swallow"


def _make_event(*records: dict) -> dict:
    return {"Records": list(records)}


def _make_record(body: object, message_id: str = "msg-1") -> dict:
    return {
        "messageId": message_id,
        "body": json.dumps(body) if not isinstance(body, str) else body,
    }


def _valid_payload(article_id: int = 42) -> dict:
    return {"event_type": "article.analyze", "article_id": article_id}


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_successful_record_returns_empty_failures():
    event = _make_event(_make_record(_valid_payload()))
    with patch(_MODULE, return_value={"ok": True}) as mock_process:
        result = lambda_handler(event, None)
    mock_process.assert_called_once_with(42)
    assert result == {"batchItemFailures": []}


def test_successful_record_passes_correct_article_id():
    event = _make_event(_make_record(_valid_payload(article_id=99)))
    with patch(_MODULE, return_value={"ok": True}) as mock_process:
        lambda_handler(event, None)
    mock_process.assert_called_once_with(99)


# ---------------------------------------------------------------------------
# Processing failure
# ---------------------------------------------------------------------------

def test_ok_false_adds_message_id_to_failures():
    event = _make_event(_make_record(_valid_payload(), message_id="msg-fail"))
    with patch(_MODULE, return_value={"ok": False, "error": "boom"}):
        result = lambda_handler(event, None)
    assert result == {"batchItemFailures": [{"itemIdentifier": "msg-fail"}]}


def test_exception_in_processing_adds_message_id_to_failures():
    event = _make_event(_make_record(_valid_payload(), message_id="msg-exc"))
    with patch(_MODULE, side_effect=RuntimeError("unexpected")):
        result = lambda_handler(event, None)
    assert result == {"batchItemFailures": [{"itemIdentifier": "msg-exc"}]}


# ---------------------------------------------------------------------------
# Malformed messages
# ---------------------------------------------------------------------------

def test_invalid_json_body_adds_message_id_to_failures():
    record = {"messageId": "msg-bad-json", "body": "not-json{"}
    event = _make_event(record)
    with patch(_MODULE) as mock_process:
        result = lambda_handler(event, None)
    mock_process.assert_not_called()
    assert result == {"batchItemFailures": [{"itemIdentifier": "msg-bad-json"}]}


def test_missing_article_id_adds_message_id_to_failures():
    payload = {"event_type": "article.analyze"}  # no article_id
    event = _make_event(_make_record(payload, message_id="msg-no-id"))
    with patch(_MODULE) as mock_process:
        result = lambda_handler(event, None)
    mock_process.assert_not_called()
    assert result == {"batchItemFailures": [{"itemIdentifier": "msg-no-id"}]}


def test_wrong_event_type_adds_message_id_to_failures():
    payload = {"event_type": "topic.refresh", "topic_id": 1}
    event = _make_event(_make_record(payload, message_id="msg-wrong-type"))
    with patch(_MODULE) as mock_process:
        result = lambda_handler(event, None)
    mock_process.assert_not_called()
    assert result == {"batchItemFailures": [{"itemIdentifier": "msg-wrong-type"}]}


# ---------------------------------------------------------------------------
# Partial batch failure — only failed records appear in failures
# ---------------------------------------------------------------------------

def test_partial_batch_failure_only_failed_record_reported():
    good = _make_record(_valid_payload(article_id=1), message_id="msg-good")
    bad = _make_record(_valid_payload(article_id=2), message_id="msg-bad")
    event = _make_event(good, bad)

    def side_effect(article_id: int) -> dict:
        if article_id == 2:
            return {"ok": False, "error": "fail"}
        return {"ok": True}

    with patch(_MODULE, side_effect=side_effect):
        result = lambda_handler(event, None)

    assert result == {"batchItemFailures": [{"itemIdentifier": "msg-bad"}]}
