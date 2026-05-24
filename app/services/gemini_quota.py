"""Gemini API quota detection, retry limits, and user-facing error formatting."""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, List, Optional, TypeVar

from google.api_core import exceptions as google_exceptions
from loguru import logger

T = TypeVar("T")

QUOTA_HTTP_STATUSES = frozenset({429, 503})
QUOTA_ERROR_CODES = frozenset(
    {
        "RESOURCE_EXHAUSTED",
        "QUOTA_EXCEEDED",
        "RATE_LIMIT_EXCEEDED",
        "RATELIMITEXCEEDED",
    }
)
QUOTA_MESSAGE_KEYWORDS = (
    "quota",
    "rate limit",
    "exhausted",
    "limit exceeded",
)

# Backoff between retries (seconds); at most 2 retries => 3 total attempts.
_QUOTA_RETRY_DELAYS = (1.0, 2.0)


class QuotaExceededError(Exception):
    """Raised when the Gemini API quota is exhausted after retries."""

    def __init__(
        self,
        message: str = "The Gemini API quota has been exhausted.",
        *,
        operation: str = "",
        completed: Optional[List[str]] = None,
        remaining: Optional[List[str]] = None,
        resume_point: str = "",
    ) -> None:
        super().__init__(message)
        self.operation = operation
        self.completed = completed or []
        self.remaining = remaining or []
        self.resume_point = resume_point

    def format_user_message(self) -> str:
        completed = "\n".join(f"  - {step}" for step in self.completed) or "  - (none)"
        remaining = "\n".join(f"  - {step}" for step in self.remaining) or "  - (none)"
        resume = self.resume_point or f"Re-run after quota reset from: {self.operation or 'last failed step'}"

        return (
            "---\n"
            "⛔ QUOTA LIMIT REACHED\n\n"
            "The Gemini API quota has been exhausted for this session.\n\n"
            f"✅ Completed:\n{completed}\n"
            f"⏳ Remaining:\n{remaining}\n"
            "🕐 Next step: Wait for quota reset (usually 1 minute for per-minute "
            f"limits, or midnight PST for daily limits), then resume from:\n"
            f"   {resume}\n\n"
            f"To continue: re-run the task starting from {resume}.\n"
            "---"
        )


def _status_code(exc: BaseException) -> Optional[int]:
    for attr in ("code", "status_code", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    return None


def _collect_error_codes(exc: BaseException) -> set[str]:
    codes: set[str] = set()
    for attr in ("reason", "code", "status"):
        value = getattr(exc, attr, None)
        if value is not None:
            codes.add(str(value).upper().replace(" ", "_"))
    details = getattr(exc, "details", None) or getattr(exc, "error_details", None)
    if isinstance(details, list):
        for item in details:
            if isinstance(item, dict):
                for key in ("reason", "code", "@type"):
                    if key in item and item[key]:
                        codes.add(str(item[key]).upper().replace(" ", "_"))
            else:
                reason = getattr(item, "reason", None) or getattr(item, "code", None)
                if reason:
                    codes.add(str(reason).upper().replace(" ", "_"))
    return codes


def _message_text(exc: BaseException) -> str:
    parts: list[str] = [str(exc)]
    response = getattr(exc, "response", None)
    if response is not None:
        parts.append(str(response))
    return " ".join(parts).lower()


def is_quota_error(exc: BaseException) -> bool:
    """Return True if *exc* (or its cause chain) indicates a Gemini quota / rate limit."""
    seen: set[int] = set()
    current: Optional[BaseException] = exc

    while current is not None and id(current) not in seen:
        seen.add(id(current))

        if isinstance(
            current,
            (
                google_exceptions.ResourceExhausted,
                google_exceptions.TooManyRequests,
                google_exceptions.ServiceUnavailable,
            ),
        ):
            return True

        status = _status_code(current)
        if status in QUOTA_HTTP_STATUSES:
            return True

        if _collect_error_codes(current) & QUOTA_ERROR_CODES:
            return True

        if any(keyword in _message_text(current) for keyword in QUOTA_MESSAGE_KEYWORDS):
            return True

        current = current.__cause__ or current.__context__

    return False


async def invoke_with_quota_handling(
    coro_factory: Callable[[], Awaitable[T]],
    *,
    operation: str,
    max_retries: int = 2,
) -> T:
    """
    Invoke an async Gemini call with quota-aware retries.

    Retries at most *max_retries* times (3 total attempts when max_retries=2).
    Raises QuotaExceededError without further retries once quota is confirmed.
    """
    last_exc: Optional[BaseException] = None

    for attempt in range(max_retries + 1):
        try:
            return await coro_factory()
        except Exception as exc:
            if not is_quota_error(exc):
                raise

            last_exc = exc
            if attempt < max_retries:
                delay = _QUOTA_RETRY_DELAYS[min(attempt, len(_QUOTA_RETRY_DELAYS) - 1)]
                logger.warning(
                    "Gemini quota/rate-limit signal on {} (attempt {}/{}); retrying in {}s: {}",
                    operation,
                    attempt + 1,
                    max_retries + 1,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)
                continue

            logger.error(
                "Gemini quota exhausted on {} after {} attempts; stopping further API calls",
                operation,
                max_retries + 1,
            )
            raise QuotaExceededError(
                "The Gemini API quota has been exhausted.",
                operation=operation,
            ) from exc

    # Unreachable; satisfies type checker.
    raise QuotaExceededError(operation=operation) from last_exc


def enrich_quota_error(
    exc: QuotaExceededError,
    *,
    completed: List[str],
    remaining: List[str],
    resume_point: str,
) -> QuotaExceededError:
    """Attach pipeline progress to a quota error before returning to the client."""
    exc.completed = completed
    exc.remaining = remaining
    exc.resume_point = resume_point
    return exc
