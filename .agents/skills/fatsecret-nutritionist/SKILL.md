---
name: fatsecret-nutritionist
description: Legacy compatibility skill for FatSecret MCP nutrition orchestration. Use fatsecret-orchestrator as the canonical pipe-first skill for natural diary/combo logging.
---

# FatSecret Nutritionist (Legacy Compatibility Shim)

This skill is kept for compatibility with older prompts. For natural language diary/combo logging, follow the canonical behavior from `fatsecret-orchestrator`.

## Critical Bootstrap (duplicated on purpose)

- Use direct one-shot JSON-RPC pipe to `node dist/index.js`.
- Do NOT create scripts to talk to the MCP.
- Do NOT use `npm start` / interactive mode for user logging requests.
- No `initialize` call is needed in one-shot pipe mode.
- Prefer `discovery` -> `execute` and read schemas from `references/capabilities.md`.

### PowerShell quick template
```powershell
'{"jsonrpc":"2.0","method":"tools/call","params":{"name":"execute","arguments":{"tool":"TOOL_NAME","arguments":{}}},"id":1}' | node dist/index.js
```

## Canonical path

- Primary skill: `.agents/skills/fatsecret-orchestrator/SKILL.md`
- This legacy skill should match the orchestrator defaults:
  - pipe-first execution
  - read-before-write for combos
  - direct write when no critical ambiguity
  - grams rule (`g` => `numberOfUnits = grams`)

## Minimal operational reminders

- Combo logging: `get_saved_meals` -> `get_meal_details` -> modify in memory -> `add_food_entry` x N
- Single food logging: `search_foods` -> `get_food` -> `add_food_entry`
- Ask only for critical ambiguity (non-unique combo, unsafe unit conversion, missing quantity)
