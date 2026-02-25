# Objective
Design and implement a low-cost, deterministic nutrition microservice that replicates the successful GymTrack parsing pattern:

- Small LLM = syntactic parser (NL -> JSON)
- Deterministic backend = normalization + entity resolution + business rules
- FatSecret MCP = execution/persistence layer (stdio JSON-RPC via one-shot pipe)

The microservice will be validated standalone first, then integrated into GymTrack/FastAPI later.

# Why This Plan (Context)
This plan intentionally avoids runtime dependence on a large reasoning agent. The previous agent/skill work in this repo is now treated as:

- operational spec
- business rules source
- debugging harness
- acceptance test reference

The runtime system should be cheaper and more deterministic than an agentic flow.

# Environment & Test Credentials (Important for E2E)
The project root already contains a `.env` file with usable API keys for end-to-end validation during implementation:

- `OPENROUTER_API_KEY`
- `GOOGLE_API_KEY`

These can be used in the implementation session to run final E2E tests for:
- cheap parser model calls (e.g. via OpenRouter)
- multimodal/voice/image parsing experiments (e.g. via Google/Gemini), if enabled in the prototype scope

Important:
- Do not hardcode keys in source code or tests.
- Load from environment/config only.
- Mask secrets in logs/traces.

# Scope (V1)
## In Scope
- Text-first nutrition logging microservice (voice/photo parsers can plug in later)
- Intents:
  - `log_combo`
  - `log_combo_modified` (e.g. "sin mango")
  - `log_single_food_grams`
- Deterministic resolution of:
  - date refs (`today`, `tomorrow`)
  - meal hints (`breakfast/lunch/dinner/other`)
  - combo matching (Saved Meals)
  - ingredient removals by normalized name
  - gram serving rule (`measurement_description = g` => exact grams in `numberOfUnits`)
- FatSecret MCP execution through one-shot stdio pipe to `node dist/index.js`
- Tracing + confidence scoring + fallback policy

## Out of Scope (V1)
- Full photo-to-plate multimodal pipeline (vision model integration)
- Recipe creation/management
- Habit intelligence (`get_usual_foods`, `get_recent_foods`)
- Advanced unit conversion beyond safe grams path
- Full GymTrack integration (only design hooks and adapter contract)

# Target Architecture (Deterministic Parsing Model)
## Pipeline (4 phases)
1. `NutritionParseService` (LLM cheap parser)
2. `NutritionNormalizerService` (deterministic canonicalization)
3. `NutritionResolverService` (deterministic matching + rule engine + execution plan)
4. `FatSecretExecutorService` (MCP JSON-RPC transport + retries + result parsing)

## Key Principle
The LLM does not make business decisions or data lookups. It only emits a small JSON intent payload under strict schema.

# Proposed Folder / Module Structure (Microservice Prototype)
This can live in a new repo or a prototype folder. If prototyped here first, use:

- `prototypes/nutrition-microservice/`
- `prototypes/nutrition-microservice/app/main.py`
- `prototypes/nutrition-microservice/app/api/routes.py`
- `prototypes/nutrition-microservice/app/services/nutrition_parse_service.py`
- `prototypes/nutrition-microservice/app/services/nutrition_normalizer_service.py`
- `prototypes/nutrition-microservice/app/services/nutrition_resolver_service.py`
- `prototypes/nutrition-microservice/app/services/fatsecret_executor_service.py`
- `prototypes/nutrition-microservice/app/services/fatsecret_context_service.py`
- `prototypes/nutrition-microservice/app/models/schemas.py`
- `prototypes/nutrition-microservice/app/prompts/nutrition_parse.yaml`
- `prototypes/nutrition-microservice/tests/`

# Naming Convention (Mandatory, for readability)
The user requires Spanish, highly descriptive names so the code is self-explanatory at first glance.

## Mandatory rule
- Class names, function names, variable names, and modules should be in Spanish and descriptive whenever possible.

## Examples (preferred style)
- `ServicioParseoNutricion`
- `ServicioNormalizacionNutricion`
- `ServicioResolucionNutricion`
- `ServicioEjecucionFatSecret`
- `obtener_comidas_guardadas()`
- `resolver_combo_por_nombre()`
- `aplicar_regla_gramos()`
- `resultado_resolucion`
- `plan_ejecucion`
- `errores_bloqueantes`

## Exceptions (acceptable)
- External API field names and wire contracts that must preserve canonical English names (e.g. MCP/FatSecret JSON keys such as `foodId`, `servingId`, `numberOfUnits`)
- Widely standard technical acronyms (`MCP`, `LLM`, `JSON`, `SQL`, `API`)

## Implementation note
You may keep external payload schemas in English for compatibility, but internal code identifiers should remain in Spanish.

If you prefer direct GymTrack integration instead of a prototype repo, mirror this structure inside GymTrack modules.

# Contracts (Decision-Complete)
## 1) Parser Input Contract (LLM stage)
Input to parser service:

- `user_text`: raw text or transcript
- `reference_date`: absolute date (`YYYY-MM-DD`)
- `available_combos`: list of combo names (exact names)
- `meal_aliases`: canonical meal aliases (`desayuno/comida/almuerzo/cena/...`)
- optional `recent_combo_aliases`: known user shortcuts (future)

## 2) Parser Output Contract (strict JSON, minimal)
Use a minimal schema. Do not ask the LLM for IDs, servings, or macros.

```json
{
  "intent": "log_combo_modified",
  "date_ref": "tomorrow",
  "meal_hint": "lunch",
  "combo_ref": "ensalada base",
  "operations": [
    { "op": "remove", "target": "mango" }
  ]
}
```

Allowed `intent` values (V1):
- `log_combo`
- `log_combo_modified`
- `log_single_food_grams`
- `unknown` (explicit fallback state)

Allowed `operations` (V1):
- `remove` (target text)

For `log_single_food_grams`:
```json
{
  "intent": "log_single_food_grams",
  "date_ref": "today",
  "meal_hint": "other",
  "food_ref": "yogur griego",
  "grams": 250
}
```

## 3) Normalized Intent Contract (deterministic)
The normalizer converts parser output to a backend-safe object:

```json
{
  "intent": "log_combo_modified",
  "date": "2026-02-26",
  "meal_type": "lunch",
  "combo_ref_raw": "ensalada base",
  "combo_ref_normalized": "ensalada base",
  "operations": [
    { "op": "remove", "target_raw": "mango", "target_normalized": "mango" }
  ],
  "parser_valid": true,
  "parse_issues": []
}
```

## 4) Resolver Output (Execution Plan)
Resolver must output an execution plan before making any write:

```json
{
  "plan_type": "fatsecret_write_batch",
  "date": "2026-02-26",
  "meal_type": "lunch",
  "combo_match": {
    "saved_meal_id": "47326383",
    "saved_meal_name": "Ensalada Base",
    "score": 0.98
  },
  "resolved_items": [
    {
      "food_id": "4881229",
      "food_entry_name": "Pollo a la plancha",
      "serving_id": "4751539",
      "number_of_units": 200,
      "rule_applied": "measurement_description=g => grams exact"
    }
  ],
  "excluded_items": ["Mango"],
  "confidence": {
    "overall": 0.95,
    "combo_match": 0.98,
    "unit_resolution": 1.0
  },
  "needs_confirmation": false,
  "blocking_issues": []
}
```

## 5) Executor Result Contract
```json
{
  "status": "ok",
  "date": "2026-02-26",
  "meal_type": "lunch",
  "executed_count": 7,
  "failed_count": 0,
  "entries": [
    {
      "food_entry_name": "Pollo a la plancha",
      "food_entry_id": "22670000000",
      "serving_id": "4751539",
      "number_of_units": "200.000"
    }
  ],
  "partial_failures": []
}
```

# Service Responsibilities (SRP)
## `NutritionParseService` (LLM cheap parser)
- Loads YAML prompt template
- Injects dynamic context (combo names, reference date, examples)
- Calls small LLM (`Qwen`, `gpt-4o-mini`, etc.)
- Validates raw JSON syntax/schema
- Returns parser output + parser metadata (latency, model, token use if available)

## `NutritionNormalizerService` (deterministic)
- Parses `date_ref` into absolute `YYYY-MM-DD`
- Maps meal aliases to enum (`breakfast/lunch/dinner/other`)
- Normalizes free text (`lowercase`, whitespace, optional accent-folding for matching)
- Validates allowed intents and operation shapes
- Emits normalized intent + issues

## `NutritionResolverService` (deterministic, core logic)
- Combo resolution:
  - `get_saved_meals`
  - tolerant matching (exact normalized > contains > single candidate)
- Read-before-write:
  - `get_meal_details`
- Operation application:
  - remove ingredient by normalized name match
- Gram rule enforcement:
  - for gram modifications or gram-derived naming patterns, call `get_food`
  - if selected serving has `measurement_description = g`, set `numberOfUnits = exact grams`
- Naming hygiene:
  - prefer descriptive names (e.g. `Pollo a la plancha`) over quantity-encoded names
- Confidence scoring:
  - combo match confidence
  - ingredient match confidence
  - unit resolution confidence
- Produce execution plan or blocking issues

## `FatSecretExecutorService` (deterministic MCP adapter)
- One-shot JSON-RPC transport over stdio:
  - `node dist/index.js`
- Public meta-tool usage:
  - `discovery` (on drift only / bootstrap optional cache)
  - `execute`
- Retry policy:
  - `tool not found` => rerun `discovery`
  - schema mismatch => internal developer error / reject
- UTF-8 safety:
  - if running under Windows PowerShell wrapper, force UTF-8 including `$OutputEncoding`
- Parse MCP responses into typed results

## `FatSecretContextService` (supporting service)
- Fetch and cache short-lived context for parser injection:
  - saved meal names
  - optional recent entries (future)
- Cache TTL proposal: 60-180 seconds for interactive sessions

# Prompting Strategy (Cheap Model Friendly)
## Prompt Template (`nutrition_parse.yaml`)
System prompt sections:
1. Role: parser only, no reasoning beyond extraction
2. Allowed intents and schemas (strict)
3. Exact combo list from context
4. Date reference rules (`today`, `tomorrow`)
5. Meal alias mapping hints
6. Output JSON only (no prose)
7. Examples (2-5)

## Dynamic Context Injection (V1)
Inject:
- `reference_date`
- `saved_meals_exact_list`
- `meal_aliases`

Do NOT inject:
- full FatSecret schema
- serving IDs
- nutrition values

## Model Selection Strategy
Default:
- small/cheap model (e.g. Qwen family or `gpt-4o-mini` equivalent)

Fallback (only by backend policy):
- larger model for parse retry when:
  - invalid JSON repeated
  - `intent = unknown` and user text is long/ambiguous
  - parser fails schema twice

# Deterministic Matching / Rules (Nutrition-specific)
## Combo Matching (Saved Meals)
Matching priority:
1. exact normalized match
2. exact accent-folded match
3. contains match
4. single high-scoring fuzzy match (threshold)
5. else block and ask confirmation

## Ingredient Removal (V1)
For `remove` ops:
1. normalize targets
2. exact normalized item match
3. contains match
4. if multiple matches => blocking ambiguity
5. if zero matches => blocking issue (no write)

## Gram Rule (Critical)
Mandatory rule derived from production bug:
- If `measurement_description == "g"`, `numberOfUnits = desired grams` exactly.
- Never compress `200g` into `2`.
- Never scale by hidden factors when serving is gram-based.

## Naming Hygiene Rules (V1)
- Prefer descriptive names without quantity in `foodEntryName` if quantity is already encoded in `numberOfUnits`.
- Preserve accents (`Rúcula`, `Canónigos`) in user-facing names.

# API Design (FastAPI Prototype)
## Endpoints (V1)
### `POST /v1/nutrition/parse`
Purpose: parse only (cheap LLM + normalization preview)

Request:
```json
{ "text": "Apunta mi ensalada de siempre para manana sin mango", "reference_date": "2026-02-25" }
```

Response:
- parser output
- normalized intent
- parse issues

### `POST /v1/nutrition/resolve`
Purpose: resolve normalized/parser payload into execution plan (no writes)

Request:
```json
{ "text": "...", "reference_date": "2026-02-25" }
```
or normalized payload variant

Response:
- execution plan
- confidence
- blocking issues

### `POST /v1/nutrition/execute`
Purpose: execute a previously approved execution plan

Request:
- execution plan JSON

Response:
- executor result

### `POST /v1/nutrition/parse-and-log`
Purpose: end-to-end one-shot (MVP convenience endpoint)

Behavior:
- parse -> normalize -> resolve -> execute if no blockers
- returns full trace summary

## Response Envelope (recommended)
Use consistent envelope:
```json
{
  "ok": true,
  "phase": "resolve",
  "data": {...},
  "warnings": [],
  "errors": []
}
```

# Error Taxonomy (Decision-Complete)
## Parser Errors
- `PARSER_INVALID_JSON`
- `PARSER_SCHEMA_MISMATCH`
- `PARSER_UNKNOWN_INTENT`

## Normalizer Errors
- `NORMALIZER_INVALID_DATE_REF`
- `NORMALIZER_INVALID_MEAL_HINT`

## Resolver Blocking Errors
- `RESOLVER_COMBO_NOT_FOUND`
- `RESOLVER_COMBO_AMBIGUOUS`
- `RESOLVER_INGREDIENT_NOT_FOUND_IN_COMBO`
- `RESOLVER_INGREDIENT_AMBIGUOUS`
- `RESOLVER_UNSAFE_UNIT_CONVERSION`

## Executor Errors
- `MCP_TRANSPORT_ERROR`
- `MCP_TOOL_NOT_FOUND`
- `MCP_SCHEMA_ERROR`
- `MCP_PARTIAL_WRITE_FAILURE`

# Observability / Tracing (Important for Cost + Debugging)
Persist or log per request:
- raw input text
- parser prompt version + model
- parser raw output
- normalized intent
- resolution plan
- MCP payloads sent (sanitized if needed)
- MCP results
- latency per phase
- fallback used (boolean + reason)

This is essential to compare cheap parser performance vs fallback.

# Testing Plan (Standalone, Mostly Automatable)
## A. Unit Tests (No MCP)
1. `NutritionNormalizerService`
   - date refs (`today`, `tomorrow`)
   - meal aliases (`comida` => `lunch`)
   - schema validation
2. Match normalization
   - accent folding (`Rúcula` / `Canónigos`)
3. Gram rule helper
   - `measurement_description = g` => exact grams

## B. Resolver Tests (Mocked Executor/MCP)
1. Combo exact match
2. Combo fuzzy match
3. Remove ingredient success
4. Remove ingredient ambiguous
5. Remove ingredient missing
6. Gram-serving unit resolution

## C. Integration Tests (Real MCP via pipe)
Use existing local FatSecret MCP and one-shot pipe.

Golden scenarios:
1. `Apunta mi ensalada de siempre para manana sin mango`
2. `Anade 250g de yogur griego para hoy`
3. `Registra mi ensalada base para manana en cena`
4. accented names persistence (`Rúcula`, `Canónigos`) under Windows PowerShell UTF-8 setup

## D. Acceptance Tests (Reuse Existing Repo Assets)
Leverage the acceptance suite already created:
- `docs/guides/fatsecret-agent-acceptance-suite.md`

Adapt its cases to microservice endpoint tests (`/parse`, `/resolve`, `/parse-and-log`).

# Existing Skills / Assets We Already Have (Leverage in Next Session)
This section is included explicitly so the next session can move fast.

## Session-available Skills (from AGENTS instructions)
1. `crear-historial-docs`
   - Use after implementation/testing to document the session and create a focused commit for the session log.
2. `fatsecret-nutritionist`
   - Legacy compatibility skill; still useful as procedural reference and fallback operational guidance.
3. `skill-creator`
   - Use if we decide to package the new microservice workflow as a dedicated skill (e.g. `nutrition-microservice-dev`).
4. `skill-installer`
   - Use only if importing an external skill or standardizing local skill deployment workflow.

## Repo Skills / Instruction Assets (already built and highly relevant)
1. `.agents/skills/fatsecret-orchestrator/SKILL.md`
   - Canonical anti-panic, pipe-first operating rules
   - grams rule and UTF-8 PowerShell guidance
2. `.agents/skills/fatsecret-orchestrator/references/pipe-protocol.md`
   - one-shot JSON-RPC patterns and error recovery
3. `.agents/skills/fatsecret-orchestrator/references/nl-logging-rules.md`
   - natural language operation rules and naming hygiene
4. `.agents/skills/fatsecret-orchestrator/references/capabilities.md`
   - exact MCP tool schemas
5. `docs/guides/fatsecret-agent-master-context.md`
   - portable ES/EN system prompt for manual/agentic validation
6. `docs/guides/fatsecret-agent-acceptance-suite.md`
   - ready-made test scenarios to convert into endpoint/integration tests
7. `AGENTS.md` + `CLAUDE.md`
   - repo-wide guardrails and operational reminders
8. Root `.env` (already present)
   - Contains `OPENROUTER_API_KEY` and `GOOGLE_API_KEY` for final E2E tests during implementation
   - Use via environment loading only (never hardcode / never log raw secrets)

## Existing Test/Utility Scripts in Repo (useful for quick validation)
- `utils/test-meta.js`
- `utils/test-mcp.js`
- various `utils/*` scripts that demonstrate `execute` payload patterns

These are not the final runtime design, but they are useful for rapid verification in the implementation session.

# Implementation Phases (Next Session Execution Plan)
## Phase 0 - Confirm placement
Decision to make at start:
- prototype inside this repo (`prototypes/nutrition-microservice`)
- or implement directly in GymTrack

Default recommendation: prototype here first for 1 session, then port.

## Phase 1 - Skeleton + Schemas
- Create FastAPI app skeleton
- Add Pydantic models for parser/normalized/resolver/executor contracts
- Add endpoint stubs (`/parse`, `/resolve`, `/execute`, `/parse-and-log`)

## Phase 2 - MCP Executor Adapter (deterministic)
- Implement one-shot JSON-RPC stdio calls
- Implement response parser + error taxonomy mapping
- Add UTF-8 safe PowerShell invocation notes (if Windows execution wrapper is used)

## Phase 3 - Normalizer + Resolver Core
- Implement date/meal normalization
- Implement combo matching and `get_meal_details` read-before-write flow
- Implement `remove` operation
- Implement gram rule (`measurement_description = g`)

## Phase 4 - Parser Integration (cheap LLM)
- Add YAML prompt loader
- Add small-model client adapter interface
- Validate strict JSON parsing and schema conformance
- Add fallback policy hooks (no large model mandatory on day 1)

## Phase 5 - End-to-End Tests
- Run parse-only cases
- Run resolve-only cases
- Run real MCP integration cases (safe test dates)
- Verify accented names and grams correctness
- Run final E2E parser tests using `.env` keys available in project root (`OPENROUTER_API_KEY`, `GOOGLE_API_KEY`) with secret-safe logging

## Phase 6 - Hardening / Portability
- Trace logging
- timeout/retry tuning
- config/env cleanup
- documentation for GymTrack integration adapter

# Acceptance Criteria (Definition of Done for Prototype V1)
1. End-to-end endpoint `/v1/nutrition/parse-and-log` can process at least:
   - combo logging
   - combo logging with `remove`
   - single food in grams
2. Resolver enforces exact-grams rule for gram-based servings.
3. Read-before-write combo execution is mandatory in implementation.
4. Accented custom names are preserved in successful writes (`Rúcula`, `Canónigos`) when using documented UTF-8 path.
5. System runs with a small/cheap parser model by default.
6. Fallback hook exists but is not required for happy path.
7. Trace output is sufficient to debug parser/resolver/executor phases independently.

# Risks and Mitigations
## Risk: Parser over-extraction / schema drift
Mitigation:
- strict JSON schema validation
- minimal parser contract
- resolver rejects unknown fields/ops

## Risk: Combo ambiguity in real user language
Mitigation:
- confidence scoring + block when ambiguous
- optional preview mode in V2

## Risk: Cost creeps up due to larger prompts
Mitigation:
- inject only exact combo names and minimal aliases
- cache context
- avoid tool/schema blobs in parser prompt

## Risk: Windows encoding regressions
Mitigation:
- preserve UTF-8 notes in docs/skills
- include accented-name integration test in CI/manual smoke checklist

# Deliverables for the Next Session
At the end of the next implementation session, aim to have:
- runnable FastAPI prototype
- endpoint contracts implemented
- deterministic resolver with grams rule
- MCP executor adapter
- at least 3 passing integration scenarios
- short session log (`crear-historial-docs`)

# Notes for “One Sitting” Development
This functionality is feasible in one focused session because the hardest pieces already exist in this repo as reusable knowledge and validated behavior:

- MCP API + authentication + execution path already working
- anti-panic operational rules already documented
- acceptance scenarios already written
- real production bugs already discovered and codified (grams + UTF-8)

The next session should prioritize implementation speed by reusing these artifacts rather than redesigning the domain logic.
