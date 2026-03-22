"""Parse JSON from LLM output."""

from __future__ import annotations

from storydiff.analysis.json_utils import parse_json_object


def test_parse_json_object_plain() -> None:
    assert parse_json_object('{"a": 1}') == {"a": 1}


def test_parse_json_object_fenced() -> None:
    raw = '{"x": true}\n\n```json\n{"foo": "bar"}\n```'
    assert parse_json_object(raw) == {"foo": "bar"}
