"""Tests for Gemini quota detection and error formatting."""

import pytest
from google.api_core import exceptions as google_exceptions

from app.services.gemini_quota import (
    QuotaExceededError,
    enrich_quota_error,
    is_quota_error,
)


def test_is_quota_error_resource_exhausted():
    assert is_quota_error(google_exceptions.ResourceExhausted("quota exceeded"))


def test_is_quota_error_http_429():
    exc = Exception("Too Many Requests")
    exc.status_code = 429  # type: ignore[attr-defined]
    assert is_quota_error(exc)


def test_is_quota_error_message_keywords():
    assert is_quota_error(Exception("User rate limit exceeded, please retry"))


def test_is_quota_error_wrapped_chain():
    inner = google_exceptions.ResourceExhausted("RESOURCE_EXHAUSTED")
    outer = RuntimeError("LLM call failed")
    outer.__cause__ = inner
    assert is_quota_error(outer)


def test_is_quota_error_non_quota():
    assert not is_quota_error(ValueError("invalid JSON in response"))


def test_format_user_message_includes_resume():
    err = enrich_quota_error(
        QuotaExceededError(operation="analyze_input"),
        completed=["User message stored"],
        remaining=["Symptom analysis", "Response generation"],
        resume_point="POST /api/v1/chat with session_id=abc",
    )
    text = err.format_user_message()
    assert "QUOTA LIMIT REACHED" in text
    assert "User message stored" in text
    assert "Symptom analysis" in text
    assert "POST /api/v1/chat with session_id=abc" in text
