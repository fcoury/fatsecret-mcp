# Decision Memo: Nutrition Deterministic Microservice (V1)

## Purpose
Lock the default technical decisions for the next implementation session so we can build quickly, validate, and only revisit decisions if real evidence requires it.

This memo complements:
- `implementation-plan.md` (full build plan)
- `reliability-fallback-token-observability-plan.md` (runtime resilience + telemetry)

## Executive Decision (Default Path)
We will build a **deterministic nutrition microservice prototype** with:

1. **Small/cheap LLM parser by default** (JSON extraction only)
2. **Deterministic normalizer + resolver** (business logic in code)
3. **FatSecret MCP executor via one-shot stdio JSON-RPC**
4. **Degraded mode support** (capture locally if FatSecret sync fails)
5. **Local token/cost tracking from day 1**
6. **Observability platform decision deferred until pilot data**

## Why This Is the Right Default
- Minimizes runtime cost
- Reuses proven GymTrack pattern
- Avoids agentic runtime unpredictability
- Keeps FatSecret MCP as a deterministic persistence adapter
- Gives us debuggable traces phase-by-phase

## Runtime Architecture Decision (Locked for V1)
### Use 4-phase pipeline (not 3)
We explicitly choose:

- `ServicioParseoNutricion`
- `ServicioNormalizacionNutricion`
- `ServicioResolucionNutricion`
- `ServicioEjecucionFatSecret`

Reason:
- Better separation of concerns
- Easier testing
- Simpler prompt schemas
- Less resolver complexity leakage

## LLM Strategy Decision (Locked for V1)
### Default parser model
- Use a **cheap/small model** (OpenRouter-backed by default if available)
- The parser only returns strict JSON, no reasoning, no IDs, no servings

### Fallback model
- Optional and backend-controlled only
- Triggered by parse failures or invalid JSON after retry
- Not required for happy path delivery

### API keys / E2E readiness
Use existing root `.env` keys for final E2E validation:
- `OPENROUTER_API_KEY`
- `GOOGLE_API_KEY`

Rules:
- load from environment only
- never hardcode
- never print raw keys in logs

## Domain Logic Decision (Locked for V1)
### Resolver owns all business decisions
The resolver (code) decides:
- combo matching
- ingredient matching
- date normalization
- meal type normalization
- unit resolution
- blocking ambiguities
- confidence score
- execution plan generation

The parser (LLM) does **not** decide:
- `foodId`
- `servingId`
- `numberOfUnits`
- macro values
- final write behavior

## Critical Nutrition Rules (Locked for V1)
### 1. Read-before-write for combos (mandatory)
- `get_saved_meals` -> `get_meal_details` -> apply ops in memory -> `add_food_entry` x N

### 2. Gram rule (mandatory)
- If `measurement_description == "g"`, then `numberOfUnits = gramos exactos`
- Never compress `200g` into `2`

### 3. Naming hygiene (default)
- Prefer descriptive names without quantity in the custom name
- Example: `Pollo a la plancha` over `Pollo 200g`

### 4. UTF-8 hygiene (Windows PowerShell path)
- If piping JSON with non-ASCII text, set:
  - `[Console]::InputEncoding`
  - `[Console]::OutputEncoding`
  - `$OutputEncoding`
  to UTF-8

## Reliability / Fallback Decision (Locked for V1)
### We will support degraded capture
If FatSecret persistence fails:
- capture locally
- return explicit state
- do not lose user input

Allowed final states:
- `synced_to_fatsecret`
- `captured_pending_sync`
- `captured_pending_review`
- `failed_not_captured` (should be rare)

### We will not block on perfect search
If `search_foods` is unhealthy:
- combo flows may still work from Saved Meal IDs
- single-food flows can degrade to pending review/sync

## Observability / Token Cost Decision (Locked for V1)
### Build local token/cost ledger first (mandatory)
Before adopting a paid tool, implement:
- `llm_call_log`
- `llm_model_pricing`
- cost calculator
- per-call token usage logging

Reason:
- portable across projects
- immediate visibility
- avoids vendor lock-in

### External observability platform (deferred decision)
We will evaluate after a short pilot.

Initial recommendation to test first:
- **Langfuse** (good fit for LLM observability + portability/self-host options)

Alternatives to evaluate during pilot:
- **Logfire** (strong Python app observability)
- **LangSmith** (strong if adopting LangChain/LangGraph workflows)

## Naming Convention Decision (Locked for V1)
### Internal code identifiers must be in Spanish and descriptive
Mandatory for:
- clases
- funciones
- variables
- módulos (cuando sea viable)

Examples:
- `ServicioParseoNutricion`
- `obtener_comidas_guardadas()`
- `resolver_combo_por_nombre()`
- `aplicar_regla_gramos()`
- `plan_ejecucion`
- `errores_bloqueantes`

Exceptions:
- payload keys / external contracts (`foodId`, `servingId`, `numberOfUnits`)
- standard acronyms (`MCP`, `LLM`, `JSON`, `API`)

## Build Location Decision (Default)
### Default recommendation for next session
Prototype first in this repo:
- `prototypes/nutrition-microservice/`

Reason:
- direct access to working FatSecret MCP
- existing skills/docs/acceptance assets
- faster debugging and E2E validation

Later:
- port to GymTrack backend once validated

## What We Will Reuse Immediately (No Redesign)
- `.agents/skills/fatsecret-orchestrator/` (rules + protocol)
- `docs/guides/fatsecret-agent-acceptance-suite.md`
- `docs/guides/fatsecret-agent-master-context.md`
- `AGENTS.md` and `CLAUDE.md` guardrails
- real MCP behavior already validated in this repo

## What We Will Not Do in V1 (Anti-scope creep)
- No large-model-first runtime
- No recipe automation
- No full image pipeline productionization
- No over-engineered agent layer in runtime
- No dependency on paid observability platform before local telemetry exists

## Success Criteria for the Next Session
1. Prototype endpoints running (`/parse`, `/resolve`, `/execute`, `/parse-and-log`)
2. Cheap parser model integrated via env keys
3. Resolver applies combo + remove + grams rule correctly
4. MCP executor writes to FatSecret via one-shot pipe
5. Degraded mode returns `captured_pending_*` on failures
6. Token/cost logging recorded for parser calls
7. At least 3 E2E scenarios tested successfully

## Decision Review Trigger (When to revisit this memo)
Only revisit these defaults if we observe one of:
- cheap parser accuracy is insufficient after prompt/context tuning
- resolver complexity becomes unmanageable without expanding parser contract
- MCP runtime instability dominates and requires stronger local catalog strategy
- observability requirements exceed local telemetry + pilot tooling quickly

Otherwise, proceed with implementation using this memo as the default operating baseline.
