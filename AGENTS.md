# AGENTS.md

## FatSecret MCP Local Execution Rules (Pipe-First)

These rules are repository-specific guardrails for any coding agent working on user nutrition tasks in this repo.

### Default operating mode for user requests ("apunta", "anade", "registra")

- Use direct one-shot JSON-RPC piping into `node dist/index.js`.
- Treat the MCP as non-interactive stdio for task execution.
- Use `discovery` if the internal tool name is unknown.
- Use `execute` with exact argument schemas from the skill references.

### Hard prohibitions for task execution

- Do not create helper scripts just to call the MCP.
- Do not use `npm start` / `npm run dev` / interactive runners to fulfill a user logging request.
- Do not invent `foodId`, `servingId`, `numberOfUnits`, or conversions.
- If `measurement_description = g`, send exact grams in `numberOfUnits` (never compress `200g` into `2`).
- In Windows PowerShell, force UTF-8 before piping JSON with accented names (`Rúcula`, `Canónigos`) and set `$OutputEncoding`.

### Reliability rules

- Combo logging MUST be read-before-write:
  1. `get_saved_meals`
  2. `get_meal_details`
  3. apply modifications in memory
  4. `add_food_entry` per item
- V1 unit autonomy:
  - If serving unit is `g`, then `numberOfUnits = grams`.
  - Otherwise reuse known combo units or ask if conversion is required.

### Skills

- Prefer `.agents/skills/fatsecret-orchestrator/` for natural diary/combo logging.
- `.agents/skills/fatsecret-nutritionist/` is legacy compatibility and should defer to the orchestrator behavior.
