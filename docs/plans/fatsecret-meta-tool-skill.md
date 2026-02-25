# Objective
Implement a Meta-Tool Pattern for the FatSecret MCP and create a "FatSecret Nutritionist" Skill that orchestrates it using Progressive Disclosure.

# Key Files & Context
- `src/index.ts`: The MCP server code. We will refactor it to expose only two tools: `discovery` and `execute`.
- `skills/fatsecret-nutritionist/SKILL.md`: The Skill instructions for the agent.
- `skills/fatsecret-nutritionist/references/capabilities.md`: Detailed documentation for all internal tools.

# Implementation Steps

## 1. Refactor MCP to Meta-Tool Pattern
1.  **Add New API Capabilities**: 
    - `food.find_id_for_barcode.v2` (Barcode Search)
    - `foods.autocomplete.v2` (Autocomplete)
    - `exercise_entries.get.v2` (Get Exercises)
    - `exercise_entry.edit.v1` (Add/Edit Exercise)
2.  **Internalize Tool Registry**: Define a map of all tools (including new ones) with their schemas and handlers within the `FatSecretMCPServer` class.
3.  **Expose Meta-Tools**:
    - `discovery`: Returns a list of available tool names and descriptions.
    - `execute`: Takes `tool` (string) and `arguments` (object) and invokes the internal handler.
4.  **Fix Bugs in `add_food_entry`**:
    - Rename `quantity` to `number_of_units`.
    - Ensure `food_entry_name` is provided.
    - Map `meal` types correctly (breakfast, lunch, dinner, other).

## 2. Create the Nutritionist Skill
1.  **SKILL.md**: Instructions for using the MCP's `discovery` and `execute` tools.
    - Guide the agent to first use `discovery` if it doesn't know which tool to use.
    - Provide high-level workflows (e.g., "Add a meal" = `search_foods` -> `get_food` -> `add_food_entry`).
2.  **capabilities.md**: Detailed schemas for each internal tool for the agent to reference via Progressive Disclosure.

## 3. Verification
1.  **Build**: Run `npm run build`.
2.  **Test**: Run the MCP with `node dist/index.js` and use standard MCP inspection or `utils/test-mcp.js`.
3.  **Skill Installation**: Package and install the skill locally.
4.  **User Verification**: Demonstrate a complex workflow (barcode search -> add entry) through the skill.

# Verification & Testing
- Unit tests for date conversion and OAuth signing.
- Integration test for the `execute` tool with multiple internal tools.
- Validation of the Skill using `package_skill.cjs`.

## V2 UPGRADE PLAN
- Add get_meal_details, get_usual_foods, get_recent_foods, get_all_favorites, manage_favorite_recipe.
