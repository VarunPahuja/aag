"""One exception hierarchy for everything that can go wrong reaching a model.

The distinction that matters to a caller is **retryable** versus **not**, because live
mode's fallback rule (due 3 Sept) is written in those terms: a transport failure or a
rate limit is worth retrying and then falling back to cached; an auth failure is a
misconfiguration that retrying will never fix, and burning the retry budget on it only
delays a clear error message.

`OpinionParseError` deliberately does not live here. A malformed response is a
*validation* failure, not a transport one, and it belongs beside the schema that
rejected it (`governance/prompts/schema.py`).
"""

from __future__ import annotations


class GovernanceLLMError(RuntimeError):
    """Base for every failure in this package."""

    #: Whether retrying the same call could plausibly succeed. Live mode reads this
    #: rather than matching on exception types, so a new subclass gets the right
    #: behaviour by declaring it instead of by being added to a tuple somewhere.
    retryable: bool = False


class GeminiTransportError(GovernanceLLMError):
    """The request did not complete: connection refused, timeout, 5xx.

    Retryable. The model may be fine and the network may not be.
    """

    retryable = True


class GeminiRateLimitError(GovernanceLLMError):
    """HTTP 429. The free tier's quota has been exceeded.

    Retryable, but only with a delay — this is the error a naive recording loop hits
    at roughly ten requests per minute, and retrying it immediately makes it worse.
    `retry_after` carries the server's own advice when it sends any.
    """

    retryable = True

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class GeminiAuthError(GovernanceLLMError):
    """HTTP 401/403. The key is missing, wrong, or not entitled to this model.

    **Not** retryable. A missing `GEMINI_API_KEY` is the common case and the message
    says so, because the alternative is a developer watching three silent retries and
    concluding the API is down.
    """

    retryable = False


class GeminiResponseError(GovernanceLLMError):
    """The call succeeded but the envelope held no usable text.

    A safety block or an empty candidate list lands here. Not retryable: the same
    prompt will be blocked the same way, and pretending otherwise hides the reason.
    """

    retryable = False


class RecordingMissError(GovernanceLLMError):
    """Cached mode was asked for a prompt that has no recording on disk.

    Not retryable, and deliberately loud. The quiet alternatives are both worse: a
    fallback to stub text makes an unrecorded prompt look like a working one, and a
    fuzzy match replays an answer to a question that was not asked.
    """

    retryable = False

    def __init__(self, message: str, cache_key: str) -> None:
        super().__init__(message)
        self.cache_key = cache_key
