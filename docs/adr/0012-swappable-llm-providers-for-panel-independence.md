# ADR-0012: Swappable LLM providers, to make the agent panel actually independent

## Status

Proposed

Raised by the governance lane owner. **Needs a decision from the team**, because it
touches a written project constraint (see Consequences).

## Context

The governance panel runs four agents — risk, performance, compliance, audit — over the
same `TrustEvaluation`, in parallel, and preserves their disagreement rather than
blending it. `Recommendation.has_dissent` exists because a split panel is the most
useful thing on a reviewer's screen.

The strongest objection to that design is that the four are not independent judges. They
are four prompts against one base model, so they inherit that model's biases and their
errors correlate. The literature makes this point directly about multi-agent LLM systems,
and a reviewer who knows the area will raise it.

Our current answer is structural: governance is advisory, so even four agents wrong in
the same direction cannot move an autonomy limit — the evidence is computed outside any
model, enforcement is deterministic code, and a human authorizes (ADR-0001, ADR-0003,
ADR-0004). That answer is correct and it is not sufficient. It explains why correlated
error is *survivable*; it does not reduce the correlation.

Two further forces:

- The lane brief (`docs/lanes/vc.md`) says **"Do not introduce any paid API or service."**
  Gemini has a free tier via Google AI Studio. Anthropic and OpenAI do not.
- We found, while building this, that `Prompt.cache_key` was `agent.version.evidence` —
  with no model in it. Cached mode keyed that way would replay one provider's recording
  for another provider's request and look completely healthy doing it.

## Decision

**Make the LLM provider a per-agent configuration value, with Gemini as the default and
the other providers as optional extras that nothing requires.**

Concretely:

- An `LLMClient` protocol (`governance/llm/base.py`), with one implementation per
  provider: Gemini over raw HTTP, Claude via the `anthropic` SDK, OpenAI via the `openai`
  SDK. Each takes a `Prompt` and returns raw text; none of them validates or parses, so a
  new provider cannot bring a second validation path with it.
- Selection from the environment (`governance/llm/registry.py`):
  `GOVERNANCE_PROVIDER` sets the default for every agent, and
  `GOVERNANCE_PROVIDER_<AGENT>` overrides one. An unrecognised value raises rather than
  falling back, for the same reason `resolve_mode` does: a typo that quietly ran on the
  default would look exactly like a working mixed-model panel.
- Three schema dialects, because the providers genuinely differ. Gemini's `responseSchema`
  is an **OpenAPI 3.0 subset** with no `$ref` resolution and no `additionalProperties`;
  Claude's `output_config.format` and OpenAI's `response_format` both take **strict JSON
  Schema**, which requires `additionalProperties: false` and every property in `required`.
  `gemini_response_schema()` and `strict_json_schema()` both generate from the same
  Pydantic model, so the contract cannot drift between them.
- **The model goes into the recording cache key**:
  `agent.promptversion.model.evidence` (`cache_key_for`). Recordings carry `provider` and
  `model` fields as provenance.
- `anthropic` and `openai` are `[project.optional-dependencies]`. Neither is installed in
  CI, and the test suite covers both clients through injected stubs with SDK exceptions
  matched by class name.

## Consequences

**The correlated-bias objection gets a real answer rather than a survivable one.** Risk on
Claude and performance on Gemini is two models that fail differently reading the same
evidence. When they disagree, that disagreement carries information it did not carry
before.

**This is the part the team needs to rule on.** The lane brief forbids introducing a paid
API, and Claude and OpenAI are paid. The constraint is honoured in the way that seems to
match its intent — the stated reason in the brief is that the project must not cost
anything to run — and specifically:

- Gemini remains the default and needs no extra.
- The project runs end to end with all three keys blank, as it must.
- CI installs neither optional package and never calls any provider.
- Using Claude or OpenAI is opt-in, requires the developer's own key, and is never
  required to demo, test, or grade the project.

If the team reads the constraint more strictly than that, the fix is small: drop the two
optional clients and keep the seam, the registry, and the cache-key fix. Everything else
in this change stands on its own.

**A latent bug is fixed.** Recordings keyed without the model were a silent-failure path,
and silent failure is precisely what this lane exists to prevent. This is also a small
worked example of the argument the project makes: the failure was invisible in the
output and only a key change made it detectable.

**Costs.** Three request-building paths instead of one, each with its own error mapping;
three dialects to keep in step with one Pydantic model; and a recording matrix that grows
with the number of distinct models used, not with the number of scenarios. A mixed panel
needs a key for every provider it uses before it can be recorded at all.

Implemented in `governance/llm/` — `base.py`, `gemini.py`, `claude.py`,
`openai_client.py`, `registry.py`, `recording.py:cache_key_for`.

## Alternatives considered

**Keep one provider and answer the objection structurally.** This is the status quo and
it is a defensible position — the safety argument does not depend on model independence.
It lost because conceding a weakness with a structural answer is worth less than
conceding it with a mitigation, and the mitigation turned out to cost about a day.

**Let the user supply a key through the UI.** Genuinely attractive, and rejected on
scope and handling grounds: the key would cross the frontend and backend lanes, which
this lane does not own, and it would raise storage, logging, and persistence questions
eight days from the integration checkpoint. A demo that asks a reviewer to paste an API
key into a form is also a worse demo than one that works. Environment variables keep the
key on the machine that uses it.

**Use one provider but different models within it (e.g. Gemini Flash and Pro).** Cheaper
and simpler, and it does reduce correlation somewhat. It lost because models from one
family share training data and post-training, which is most of where the correlation
comes from — it would let us claim a mitigation while barely delivering one.

**Put the model in `AgentOpinion` rather than only in the recording.** This is the right
long-term shape — a reader of a `Recommendation` should be able to see which model argued
each opinion. It lost for now because `shared/` is frozen until 9 Sept and changing it
needs all four lane owners (ADR-0005). Worth revisiting after the freeze; the recording
already carries the provenance, so nothing is lost in the meantime.
