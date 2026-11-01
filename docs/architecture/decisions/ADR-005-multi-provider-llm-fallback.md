# ADR-005: Multi-Provider LLM Abstraction and Intelligent Circuit-Breaker Fallback

## Status
ACCEPTED

## Context
Module C (LLM Integration) and Challenge 1 (Intelligent Model Fallback) mandate integrating at least two distinct LLM providers (e.g., Anthropic Claude and OpenAI) and implementing automatic failover when the primary provider encounters rate limits (HTTP 429), server errors (HTTP 5xx), or timeouts.

External LLM APIs exhibit real-world unreliability:
- Anthropic or OpenAI may experience regional API outages or elevated error rates.
- Concurrency bursts can trigger rate limits on production API keys.
- Network latency spikes can cause HTTP client timeouts.

The platform must guarantee uninterrupted service to users without coupling application business logic to any single vendor's SDK.

## Decision
We implement a **Provider-Agnostic LLM Abstraction** with an **Intelligent Circuit-Breaker Fallback Router**:

1. **Common Interface (`BaseLLMClient`):** Defines standard asynchronous methods:
   - `generate(prompt, system_instruction, temperature, max_tokens) -> LLMResponse`
   - `generate_stream(...) -> AsyncIterator[str]`
   - `generate_structured(..., schema: Type[BaseModel]) -> BaseModel`
2. **Provider Adapters:**
   - `AnthropicClient`: Primary provider utilizing Claude 3.5 Sonnet (and Claude 3 Haiku for light summarization).
   - `OpenAIClient`: Secondary fallback provider utilizing GPT-4o (and GPT-4o-mini).
3. **Fallback Router (`LLMFallbackRouter`):**
   - Intercepts all generation requests from RAG and Agent services.
   - Dispatches to the Primary Provider (Anthropic).
   - If the primary provider succeeds, returns the result and logs token metrics.
   - If the primary provider raises a fallback-triggering exception (`RateLimitError`, `APIConnectionError`, `InternalServerError`, `TimeoutError`), the router catches the exception, increments an error counter, logs a structured fallback audit event, and immediately re-executes the identical payload against the Secondary Provider (OpenAI).
4. **Retry vs. Fallback Distinction:**
   - *Transient Network Flakes (Socket Drop / TCP RST):* Retried up to 2 times on the *same* provider with exponential jitter backoff (100ms, 400ms).
   - *Rate Limits (429) & Provider Outages (5xx):* Do NOT retry the same broken provider; trigger immediate *fallback* to the alternative provider.
5. **Token & Cost Accounting:** Every call captures prompt tokens, completion tokens, model name, latency in milliseconds, and calculated cost in USD, persisted into `llm_usage_logs`.

## Alternatives Considered
- **Direct OpenAI SDK Calls in Route Handlers:**
  - *Pros:* Fast initial coding.
  - *Cons:* Vendor lock-in, zero fallback capability, violates Module C requirements.
- **LiteLLM Proxy:**
  - *Pros:* Multi-provider translation.
  - *Cons:* Adds an external daemon/dependency, abstracts away internal error handling, and obscures candidate code ownership during live evaluation.

## Rationale
Writing lightweight provider adapters using official SDKs (`anthropic` and `openai`) wrapping a clean Pydantic-based `LLMResponse` interface guarantees 100% code ownership, zero mystery dependencies, and seamless adaptability during the live technical verification (where reviewers may ask to introduce a new provider or adjust fallback triggers).

## Consequences
- **Positive:**
  - High availability: Platform remains operational even during full provider outages.
  - Clean separation: RAG and Agent modules interact only with `BaseLLMClient`, completely decoupled from specific vendor SDKs.
  - Unified token, cost, and latency observability.
- **Negative:**
  - Requires maintaining provider adapters when upstream SDKs update.
  - Slightly different prompt formatting nuances between Claude (prefers XML) and OpenAI (prefers JSON schema) must be reconciled by the router.

