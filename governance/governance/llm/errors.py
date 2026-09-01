"""One exception hierarchy for everything that can go wrong reaching a model.

Provider-neutral on purpose. Three providers raise three different SDK exception
families, and the caller should not have to know which one it got — the distinction
that matters is **retryable or not**, because live mode's fallback rule is
written in those terms. A transport failure or a rate limit is worth retrying and then
falling back to cached; an auth failure is a misconfiguration that retrying will never
fix, and burning the retry budget on it only delays a clear error message.

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

    #: Which provider raised it. Set by the client so an error message in a mixed-model
    #: panel says which of the three failed.
    provider: str = "unknown"


class LLMTransportError(GovernanceLLMError):
    """The request did not complete: connection refused, timeout, 5xx.

    Retryable. The model may be fine and the network may not be.
    """

    retryable = True


class LLMRateLimitError(GovernanceLLMError):
    """Quota exceeded — HTTP 429 or the provider's equivalent.

    Retryable, but only with a delay. This is the error a naive recording loop hits on
    Gemini's free tier at roughly ten requests per minute, and retrying it immediately
    makes it worse. `retry_after` carries the server's own advice when it sends any.
    """

    retryable = True

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class LLMAuthError(GovernanceLLMError):
    """The key is missing, wrong, or not entitled to this model.

    **Not** retryable. A missing key is the common case and the message names the
    variable, because the alternative is a developer watching three silent retries and
    concluding the API is down.
    """

    retryable = False


class LLMResponseError(GovernanceLLMError):
    """The call succeeded but the envelope held no usable text.

    A safety block, a refusal, or an empty candidate list lands here. Not retryable: the
    same prompt will be blocked the same way, and pretending otherwise hides the reason.
    """

    retryable = False


class ProviderUnavailableError(GovernanceLLMError):
    """A provider was selected whose optional SDK is not installed.

    Not retryable, and separate from an auth error because the fix is different: this
    one is `pip install`, not a key. Gemini needs no extra, which is why it is the
    default.
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


class RecordingStaleError(GovernanceLLMError):
    """The recording was made from different prompt text than the one being replayed.

    The cache key carries the prompt *version*, not its text, so editing a `.v1.md` file
    without bumping to `v2` leaves the key pointing at a recording of the older wording.
    Nothing about the replay looks wrong: right agent, right evidence, right model,
    plausible reasoning — produced by a prompt that no longer exists in the repo.

    Loud, and not retryable. Either bump the prompt version and re-record, or revert the
    edit. Both are cheap; a demo whose reasoning came from text nobody can read is not.
    """

    retryable = False

    def __init__(self, message: str, cache_key: str, *, expected: str, found: str) -> None:
        super().__init__(message)
        self.expected = expected
        self.found = found
        self.cache_key = cache_key
