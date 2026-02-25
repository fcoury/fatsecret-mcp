# Natural Language Logging Rules (V1)

Scope: diary + saved meal combo logging only.

## 1. Intent Mapping

Map common user phrases to logging actions:

- "apunta", "anade", "registra" -> write to diary
- "mi comida de siempre", "mi ensalada de siempre", "mi desayuno habitual" -> saved meal combo lookup
- "para hoy" -> `date=today` (or omit date if tool defaults to today)
- "para manana" -> next calendar day in local time, output concrete `YYYY-MM-DD`
- "sin X" -> remove matching ingredient(s) from combo before logging

## 2. Combo Resolution

Preferred resolution order:
1. Exact normalized name match
2. Contains match
3. Single obvious habitual candidate (only if unique)

If multiple candidates remain, ask a clarification question with top candidates.

Normalization rules:
- lowercase
- trim spaces
- collapse repeated spaces
- optionally ignore accents for matching

## 3. Read-Before-Write (Mandatory)

Never log combo ingredients from memory or previous conversation state.

Required sequence:
1. `get_saved_meals`
2. `get_meal_details`
3. in-memory modifications
4. `add_food_entry` x N

## 4. Units Autonomy (V1)

### Deterministic grams rule
If the selected serving is grams (`g`) or `measurement_description` is `g`:
- `numberOfUnits = grams requested`

Examples:
- 150g -> `numberOfUnits: 150`
- 500g -> `numberOfUnits: 500`
- `Pollo 200g` with 1g serving -> `numberOfUnits: 200` (never `2`)

### Non-gram fallback
- If logging from combo and no quantity change was requested: reuse combo `servingId` + `numberOfUnits` exactly.
- If user requests gram change but item has no grams serving available: ask (do not guess).
- Do not create conversions for cups/servings unless explicitly provided by FatSecret serving data and unambiguous.

## 5. Meal Type Defaults

Priority:
1. Explicit user request ("en cena") -> use that
2. Unique combo metadata meal type (if known)
3. `other`

Allowed values for diary logging:
- `breakfast`
- `lunch`
- `dinner`
- `other`

## 6. Ambiguity Policy (Ask Only for Critical Data)

Ask only if:
- combo is not uniquely resolvable
- excluded ingredient does not exist in combo
- new ingredient is requested without enough quantity info
- unit conversion is unsafe

Otherwise write directly.

## 7. Final Response Format (Recommended)

Return a short summary:
- action completed
- concrete date used (`YYYY-MM-DD`)
- combo name resolved
- items logged count + names (or count + notable items)
- exclusions applied
- any partial failures (explicitly)

## 8. Naming Hygiene for Custom Names

- Prefer descriptive names without embedding quantity when quantity is already expressed by `numberOfUnits`.
  - Prefer: `Pollo a la plancha` or `Pollo`
  - Avoid: `Pollo 200g` (unless quantity in the name is intentionally needed for UX)
- Preserve accents in user-facing names (`Rúcula`, `Canónigos`).
- If using PowerShell to pipe JSON with accents, force UTF-8 before executing.
