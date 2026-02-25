# Objective
Define a practical strategy to make the nutrition microservice resilient when:

- FatSecret MCP tools misbehave (e.g. `search_foods` returning irrelevant results)
- The parser/agent returns valid JSON but resolution fails
- Runtime logging to FatSecret is blocked temporarily

And, in parallel, define a reusable foundation for:

- token usage tracking (input/output/reasoning/cache)
- approximate cost calculation per model/provider
- LLM call tracing/observability across projects (not just this one)

This document is intentionally separate from `implementation-plan.md` because it addresses runtime reliability, degraded modes, and platform concerns (LLMOps/cost/tracing).

# Context (Why this file exists)
Real transcript evidence shows that even with a strong model/agent:

1. MCP runtime failures still happen (transport, schema mismatch, bad IDs, tool behavior anomalies)
2. A "smart" model can loop or improvise unsafe fallbacks when the underlying system is unhealthy
3. Deterministic architecture reduces cost/error, but it does not remove the need for:
   - health checks
   - degraded modes
   - observability
   - audit trails

Conclusion:
- We should not depend on "more model intelligence" to solve runtime instability.
- We should build explicit runtime reliability and tracing mechanisms.

# Problem Classes Observed (from recent operations)
## A. Tool Behavior Anomalies
- `search_foods` returning irrelevant coconut/unrefined oil results regardless of query.
- This breaks any resolver pipeline that assumes `search_foods` is healthy.

## B. Schema/Argument Drift or Wrong Invocation
- `add_food_entry` failures with `Cannot read properties of undefined (reading 'toString')`.
- Often caused by missing or incorrectly named params in tool invocation.
- Deterministic contracts reduce this, but runtime validation is still required.

## C. ID Validity / Cross-Endpoint Assumptions
- IDs inferred from historical/recent endpoints may not always be directly valid for a different workflow if resolution is incomplete or data was interpreted incorrectly.

## D. Encoding / Platform Issues
- Windows PowerShell piping with non-ASCII names (`Rúcula`, `Canónigos`) broke without UTF-8 + `$OutputEncoding`.
- This is not an LLM problem; it is an execution environment problem.

# Key Design Principle
## Runtime must be robust under partial failures
The system should support:

- `Happy path`: parse -> resolve -> persist to FatSecret
- `Degraded path`: parse -> estimate/store locally (pending sync) when FatSecret is unavailable or confidence is low

This avoids blocking user capture (zero-friction UX) just because the persistence layer is unhealthy.

# Proposed Reliability Strategy (Layered)
## Layer 1: Deterministic Contracts (already planned)
- Minimal parser JSON schema
- Normalizer validation
- Resolver confidence scoring
- MCP executor typed requests/responses

## Layer 2: Tool Health Checks (new)
Before full write flows, periodically run lightweight health checks:

### Health checks for FatSecret MCP (recommended)
1. `discovery` works and returns expected core tools
2. `get_saved_meals` responds successfully (auth + private read health)
3. `get_user_food_entries` for today responds successfully (auth + diary read health)
4. `search_foods` sanity query returns plausible results (not same irrelevant set repeatedly)

### `search_foods` sanity heuristic (V1)
For a fixed query like `banana`:
- Check top-N results contain at least one token overlap (`banana`, `platano`, etc.)
- If not, mark `SEARCH_FOODS_UNHEALTHY`

This is cheap and catches obvious regressions.

## Layer 3: Degraded Modes / Fallback Paths (new)
When core persistence fails, preserve user value by storing intent and estimates locally.

### Degraded Mode Matrix (V1)
1. `search_foods` unhealthy
   - Combo flows: still work if combo items already have valid IDs/servings in Saved Meals
   - Single-food flows: fallback to local alias catalog/recent foods cache; else pending local record

2. `add_food_entry` write failure
   - Store pending local record + trace error + retry suggestion
   - Return explicit "captured but not synced" status

3. Resolver ambiguity (low confidence)
   - Store draft/pending record requiring user confirmation (do not write to FatSecret)

4. Parser failure
   - Retry same model once
   - Retry fallback model (optional)
   - If still failing, store raw note pending manual processing

## Layer 4: Local Pending Store (new, highly recommended)
Add a local persistence layer for "captured but not synced" nutrition events.

### Why this is important
- Preserves zero-friction capture
- Decouples user input success from FatSecret availability
- Enables delayed reconciliation
- Supports photo/vision estimates even if exact match to FatSecret fails

### Pending record types (V1)
- `pending_nutrition_log` (parsed + estimated macros optional)
- `pending_resolution` (resolved partially, missing IDs/servings)
- `pending_fatsecret_sync` (fully resolved plan, write failed)

# Fallback Strategy for Photo/Multimodal (Your idea, formalized)
Your idea is good and should be first-class:

## Fallback: "Estimate-first, sync-later"
If image/text parsing is successful but FatSecret resolution/persistence fails:
- Use image/LLM (or deterministic estimation module) to estimate macros
- Store in local DB as a temporary nutrition event
- Mark status:
  - `estimated_only`
  - `pending_fatsecret_sync`
  - `needs_review`

### UX response example
"He guardado la comida de forma local con macros estimadas (pendiente de sincronizar con FatSecret cuando el servicio vuelva a estar estable)."

This keeps the user workflow intact while preserving auditability.

# Recommended Runtime States (Explicit)
Every request should end in one of these states:

- `synced_to_fatsecret`
- `captured_pending_sync`
- `captured_pending_review`
- `failed_not_captured` (rare, should be minimized)

This state model is more important than "did the LLM succeed".

# Token Tracking & Cost Accounting (Reusable Core)
## Goal
Build a provider-agnostic token/cost tracking module reusable across:
- GymTrack
- Nutrition microservice
- future AI workflows

## Design Principle
Do not depend solely on vendor dashboards. Record your own per-call usage and estimated cost at runtime.

## What to track per LLM call (minimum)
- `project`
- `environment`
- `service_name`
- `feature_name` (e.g. `nutrition_parse`, `workout_extraction`)
- `provider` (OpenAI/OpenRouter/Google/etc.)
- `model_name`
- `request_id`
- `session_id` / `user_id` (if available, privacy-safe)
- `started_at`, `duration_ms`
- token usage:
  - `input_tokens`
  - `output_tokens`
  - `reasoning_tokens` (if available)
  - `cached_input_tokens` (if provider reports)
  - `audio_tokens` / `image_tokens` (if provider reports usage that way)
- `success`
- `error_code`
- `retry_count`
- `prompt_version`

## Pricing Table (versioned)
Create a versioned pricing catalog so cost estimates are reproducible.

### Table: `llm_model_pricing`
Fields (recommended):
- `id`
- `provider`
- `model_name`
- `effective_from` (datetime)
- `effective_to` (nullable)
- `currency` (`USD`)
- `input_per_million`
- `output_per_million`
- `reasoning_per_million` (nullable)
- `cached_input_per_million` (nullable)
- `image_input_per_million` (nullable, optional)
- `notes`
- `source_url`
- `source_checked_at`

### Table: `llm_call_log`
Fields:
- `id`
- `timestamp`
- `project`
- `service_name`
- `feature_name`
- `provider`
- `model_name`
- `request_id`
- `trace_id` (for observability correlation)
- `input_tokens`
- `output_tokens`
- `reasoning_tokens`
- `cached_input_tokens`
- `total_estimated_cost_usd`
- `raw_usage_json` (provider payload)
- `success`
- `error_code`
- `latency_ms`

### Optional rollup table: `llm_cost_daily_rollup`
- `date`
- `project`
- `service_name`
- `model_name`
- `calls`
- `input_tokens`
- `output_tokens`
- `estimated_cost_usd`

## Cost Formula (V1)
Use a deterministic calculator:

```text
cost = (input_tokens / 1_000_000) * input_per_million
     + (output_tokens / 1_000_000) * output_per_million
     + (reasoning_tokens / 1_000_000) * reasoning_per_million (if priced separately)
     + (cached_input_tokens / 1_000_000) * cached_input_per_million (if available)
```

If a field is unavailable:
- store `null`
- estimate with available fields only
- mark `cost_estimate_completeness` (`full` / `partial`)

## Reusable Package / Module Proposal
Build this once as a shared utility, then import into projects.

Suggested module name:
- `shared_llm_telemetry`

Core components:
1. `usage_extractors/`
   - provider-specific parsers (OpenAI, OpenRouter, Gemini, etc.)
2. `pricing_catalog/`
   - local pricing loader + versioned entries
3. `cost_calculator.py`
4. `llm_call_logger.py`
5. `decorators.py` / middleware hooks
6. `schemas.py`
7. `exporters/`
   - DB writer
   - OpenTelemetry span attributes

This should be provider-agnostic and not tied to FatSecret.

# LLM Call Observability / Tracing Options (What to learn next)
You asked specifically about tools like Logfire / LangSmith. Good idea. The best choice depends on what you optimize for:

- fastest setup
- Python app observability
- LLM-native evals/prompt tooling
- self-hosting / data control
- cost predictability

## Recommended Evaluation Criteria (use this before choosing)
1. Python/FastAPI instrumentation quality
2. LLM-specific traces (prompts, tokens, outputs, retries)
3. Prompt versioning / experiments
4. Eval workflows (later)
5. Self-hosting availability
6. Cost and pricing transparency
7. OpenTelemetry compatibility
8. Data export/API access

## Practical Recommendation (phased, not dogmatic)
### Phase A (immediate, best ROI)
Implement your own local token/cost logging + trace IDs first.

Why:
- works today
- reusable across projects
- no vendor lock-in
- gives you cost visibility immediately

### Phase B (observability platform)
Add one external platform as a UI/trace explorer on top.

Recommended default candidate for your style:
- **Langfuse** if you want LLM-native observability + self-host option + broad portability

Recommended if you are heavily in LangChain/LangGraph ecosystem:
- **LangSmith**

Recommended if you want strong Python app observability first (not only LLM traces):
- **Pydantic Logfire**

## Why this recommendation (critical take)
- Your architecture is multi-service and will likely span more than just one agent framework.
- You explicitly care about cost, exportability, and reuse across projects.
- That usually favors:
  - local canonical logging schema (yours)
  - plus OTel-compatible observability backend/tool
rather than a single vendor SDK owning all telemetry semantics.

# Tooling Snapshot (as of 2026-02-25, verify before purchase)
Prices/features change often; verify before committing.

## Pydantic Logfire (official pricing pages)
- Free personal tier with 10M records (logs/spans/metrics) listed on pricing page
- Team/Growth tiers with usage pricing (records-based)
- Strong fit for Python instrumentation and general app observability

## LangSmith (official pricing page)
- Pricing combines seats + trace usage
- Strong LLM tracing/evals/prompt tooling, especially in LangChain ecosystem
- Now supports OpenTelemetry ingestion/integration paths (LangChain blog/docs)

## Langfuse (official docs/GitHub + verify pricing)
- Strong LLM observability/evals/prompt management focus
- Self-hosting and cloud options
- Open-source orientation; verify current cloud pricing and hosted limits directly before deciding

## Important purchasing rule
Do a 1-2 week instrumented pilot with real traffic before choosing a paid plan.
Decision should be based on:
- trace volume
- retained data needs
- team workflows
- alerting/debugging usefulness

# Implementation Plan for This Reliability + Telemetry Layer
## Phase 1: Local reliability controls (no vendor)
1. Add MCP health checks (`discovery`, `get_saved_meals`, `get_user_food_entries`, `search_foods` sanity)
2. Add runtime states (`synced`, `pending_sync`, `pending_review`, `failed_not_captured`)
3. Add local pending store schema
4. Add degraded-mode responses

## Phase 2: Token/cost logging foundation
1. Create `shared_llm_telemetry` module (or project-local equivalent first)
2. Add provider usage extractors
3. Add pricing table + versioning
4. Log per-call usage and estimated cost
5. Add daily rollup report endpoint or CLI

## Phase 3: Tracing platform integration pilot
1. Instrument FastAPI with trace IDs / OpenTelemetry (or platform SDK)
2. Correlate LLM calls + resolver + MCP executor in one trace
3. Run a small pilot with real nutrition parsing requests
4. Compare UX/cost between chosen tools

## Phase 4: Retry/reconciliation workflows
1. Background job to retry `pending_fatsecret_sync`
2. Admin/user endpoint to inspect pending items
3. Manual resolve tools for ambiguous items

# Test Plan (Reliability + Telemetry)
## Reliability tests
1. Simulate `search_foods` unhealthy -> expect `captured_pending_review` or alternate path
2. Simulate `add_food_entry` write failure -> expect `captured_pending_sync`
3. Resolver ambiguity -> expect no write, explicit blocking issue
4. UTF-8 accented names under Windows path -> expect correct persisted names

## Telemetry tests
1. LLM call logs include tokens and cost estimate
2. Missing usage fields produce partial estimate (no crash)
3. Pricing version rollover chooses correct row by date
4. Correlation IDs link API request -> parser -> resolver -> executor

# Deliverables (Next Iteration)
1. `pending_nutrition_events` DB schema + state model
2. MCP health-check module + endpoint
3. `shared_llm_telemetry` base module (project-local version acceptable first)
4. `llm_model_pricing` + `llm_call_log` schema
5. cost calculator + daily summary report
6. observability tool pilot decision memo (after 1-2 week data)

# Direct Answer to the Concern ("If a big model already fails, deterministic will be hard")
Correct concern, but the answer is not "use a bigger model".

The answer is:
- deterministic runtime + health checks + degraded modes + observability

Large models help with interpretation, but they do not solve:
- broken tool behavior
- transport/runtime bugs
- encoding issues
- missing telemetry

Those require engineering controls, which this document specifies.

# Sources to Verify Tooling/Pricing Before Adoption
Use primary sources before spending money:
- Pydantic Logfire pricing: https://pydantic.dev/pricing
- Logfire pricing change note (recent): https://pydantic.dev/articles/logfire-pricing-change
- LangSmith pricing: https://www.langchain.com/pricing
- LangSmith OTel blog post: https://blog.langchain.com/end-to-end-opentelemetry-langsmith
- Langfuse docs / repo (self-host + features): https://langfuse.com/docs and https://github.com/langfuse/langfuse

Note: pricing/features are time-sensitive; re-check during the implementation session.
