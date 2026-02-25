# FatSecret Agent Acceptance Suite (Anti-Panic, V1)

Purpose: verify that the instruction stack eliminates the initial panic phase and drives correct diary/combo execution behavior.

## Pass Criteria (all cases)

- First execution path uses one-shot pipe into `node dist/index.js`
- No helper script creation for MCP calls
- Uses `discovery` / `execute` correctly
- Follows read-before-write for combos
- Asks only for critical ambiguity
- Reports a concrete date (`YYYY-MM-DD`) in final summary

## Canonical Prompt Cases

### 1) Combo with exclusion (golden path)
Prompt:
`Apunta mi ensalada de siempre para manana pero sin mango`

Expected behavior:
- Resolve date to concrete tomorrow date
- Read combo (`get_saved_meals` + `get_meal_details`)
- Remove mango in memory
- Log remaining items with `add_food_entry`
- Summarize logged items and exclusion

### 2) Combo direct logging, date explicit
Prompt:
`Apunta mi desayuno de siempre para hoy`

Expected behavior:
- Combo flow, no unnecessary confirmation
- Direct write if combo match is unique

### 3) Single food in grams
Prompt:
`Anade 250g de yogur griego para hoy`

Expected behavior:
- `search_foods` -> `get_food` -> `add_food_entry`
- If serving in `g`, set `numberOfUnits=250`

### 4) Combo without date
Prompt:
`Apunta la ensalada de siempre`

Expected behavior:
- Default date = today
- Meal type inferred or `other`

### 5) Ambiguous exclusion
Prompt:
`Apunta mi ensalada de siempre sin algo`

Expected behavior:
- Ask clarification (critical ambiguity)
- No write before clarification

### 6) Explicit meal type override
Prompt:
`Registra mi combo ensalada base para manana en cena`

Expected behavior:
- Uses `mealType=dinner` for all diary entries

### 7) Gram request without grams serving (fallback)
Prompt:
`Anade 100g de [alimento con servings no-g]`

Expected behavior:
- Attempt to validate servings via `get_food`
- Ask instead of guessing conversion if no `g` serving

### 8) Missing combo
Prompt:
`Apunta mi combo ultra fit azul`

Expected behavior:
- No write
- Ask with top candidate names if any plausible matches

### 9) Tool drift recovery
Prompt:
`Apunta mi ensalada base`

Validation setup:
- Simulate or assume a `Tool not found` first attempt.

Expected behavior:
- Rerun `discovery`
- Retry with corrected tool name

### 10) Partial failure transparency
Prompt:
`Apunta mi ensalada de siempre para manana pero sin mango`

Validation setup:
- Simulate one `add_food_entry` failure in the batch.

Expected behavior:
- Report exactly which items succeeded/failed
- Do not claim full success

## Review Checklist (manual)

- Did the agent avoid programming a solution first?
- Did it avoid interactive process usage?
- Did it use read-before-write on combos?
- Did it apply grams rule correctly?
- Did it ask only when truly necessary?
- Did the final response match the executed actions?
