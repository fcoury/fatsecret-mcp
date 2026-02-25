---
name: fatsecret-orchestrator
description: Strict pipe-first orchestration for FatSecret MCP natural logging (diary + saved meals combos). Use when user asks to log/add/register foods or habitual combos in natural language (e.g. "apunta", "anade", "registra", "mi comida de siempre", "para manana", "sin X").
---

# FatSecret Orchestrator (Pipe-First, Anti-Panic)

Codex-first skill for reliable FatSecret MCP execution from natural language. The agent acts as a blind orchestrator: read current state, transform in memory, execute exact MCP calls.

## Bootstrap (MUST / MUST NOT)

### MUST
- Use direct one-shot JSON-RPC pipe to `node dist/index.js` for every MCP call.
- Treat the MCP as stdio + non-interactive for user tasks.
- Use `discovery` if the internal tool is unknown or a tool error suggests drift.
- Read `references/capabilities.md` before `execute` when schema/args are uncertain.
- Follow read-before-write for diary logging and combo-based actions.
- Apply V1 units rule: if the serving/unit is grams (`g`), `numberOfUnits = grams`.
- If `measurement_description` is `g`, `numberOfUnits` MUST exactly equal the desired grams (example: "Pollo 200g" => `200`, never `2`).
- Write directly (no confirmation) when intent is clear and all critical data is present.
- Ask only for critical ambiguity (non-unique combo, unresolved units, missing quantity/date when needed).
- Return a short execution summary with concrete date and logged/excluded items.

### MUST NOT
- Do NOT create scripts (`.js`, `.ts`, `.py`, etc.) to talk to the MCP.
- Do NOT use `npm start`, `npm run dev`, or interactive sessions to fulfill a user logging request.
- Do NOT invent `foodId`, `servingId`, or conversions.
- Do NOT skip `get_meal_details` before logging a Saved Meal combo.
- Do NOT compress gram quantities when `measurement_description == "g"` (example: `200g` must send `numberOfUnits = 200`, never `2`).

## Default Pipe Protocol (PowerShell + Bash)

Use one process per call. No `initialize` step is required in one-shot pipe mode.

### PowerShell: `discovery`
```powershell
'{"jsonrpc":"2.0","method":"tools/call","params":{"name":"discovery","arguments":{}},"id":1}' | node dist/index.js
```

### PowerShell: `execute`
```powershell
'{"jsonrpc":"2.0","method":"tools/call","params":{"name":"execute","arguments":{"tool":"TOOL_NAME","arguments":{}}},"id":1}' | node dist/index.js
```

### PowerShell with accents in JSON values (UTF-8)
```powershell
$utf8 = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
'{"jsonrpc":"2.0","method":"tools/call","params":{"name":"execute","arguments":{"tool":"TOOL_NAME","arguments":{"foodEntryName":"Rúcula"}}},"id":1}' | node dist/index.js
```

### Bash: `discovery`
```bash
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"discovery","arguments":{}},"id":1}' | node dist/index.js
```

### Bash: `execute`
```bash
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"execute","arguments":{"tool":"TOOL_NAME","arguments":{}}},"id":1}' | node dist/index.js
```

## V1 Decision Tree (Diary + Combos)

### A. Natural combo logging (preferred path)
Trigger examples: "mi ensalada de siempre", "apunta mi desayuno habitual", "para manana", "sin mango".

1. Resolve date (`today` if omitted; "manana" = next day).
2. Resolve combo from `get_saved_meals`.
3. Read latest ingredients with `get_meal_details`.
4. Apply user modifications in memory (V1: exclusions and simple quantity changes when safe).
5. Log each remaining item with `add_food_entry`.
6. Summarize exact date + items logged + exclusions.

### B. Single food logging
1. `search_foods`
2. `get_food` (to validate servings and IDs)
3. `add_food_entry`

## Natural-Language Modification Rules (V1)

- `sin X`: remove ingredients matching `X` by normalized name match.
- `con X`: if adding a new ingredient requires search and quantity is missing, ask.
- Quantity change in grams:
  - If target ingredient has a grams serving, use it and set `numberOfUnits` to grams.
  - If not, ask instead of guessing.
  - When `measurement_description == "g"`, never scale by 100 or any heuristic factor.

See `references/nl-logging-rules.md` for full matching and fallback behavior.

## Ambiguity Policy (Direct Write by Default)

Ask only when one of these happens:
- Multiple plausible combos and no clear winner.
- Excluded ingredient does not match any combo item.
- Unit conflict cannot be resolved safely.
- User intent is missing a critical quantity for a new item.

Otherwise execute immediately.

## Progressive Disclosure

- Core behavior is in this file (strict bootstrap + V1 flows).
- Read `references/pipe-protocol.md` for exact transport/recovery rules.
- Read `references/nl-logging-rules.md` for deterministic parsing defaults.
- Read `references/capabilities.md` only for exact tool schemas / argument names.
