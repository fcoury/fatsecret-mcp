---
name: fatsecret-nutritionist
description: Procedural intelligence for orquestrating the FatSecret MCP. Handles nutrition tracking, habit analysis, and meal management using Progressive Disclosure.
---

# FatSecret Nutritionist

Expert assistant for managing nutrition and exercise. Orchestrates the **FatSecret MCP** via the **Meta-Tool pattern** (Discovery -> Execution).

## Meta-Tool Architecture

The MCP exposes only two public tools to minimize token bloat:
1. `discovery`: Lists available internal capabilities.
2. `execute`: Executes a specific internal tool with parameters.

## Core Procedures

### 1. Reliable Food Logging (Read-before-Write)
To ensure accuracy, never log from memory.
- **Search**: `execute(tool: "search_foods", arguments: { searchExpression: "..." })`.
- **Verify**: `execute(tool: "get_food", arguments: { foodId: "..." })` to confirm nutritional value and get the correct `servingId`.
- **Log**: `execute(tool: "add_food_entry", arguments: { ... })`.

### 2. Managing Saved Meals (Combos) - PREFERRED PATH
Saved Meals are more reliable than Recipes for private tracking.
- **Fetch**: Always call `get_meal_details` before logging a combo to catch recent manual edits.
- **Bulk Log**: Iterate through the ingredients returned by `get_meal_details` and call `add_food_entry` for each one.
- **Checks**: Use the `meals` parameter in `create_saved_meal` (e.g., "Breakfast,Other") so they appear in the web UI selectors.

### 3. Proactive Habit Intelligence
- **Empty Diary?**: Use `get_usual_foods` or `get_recent_foods` to suggest quick logs based on historical patterns.
- **Contextual Awareness**: Filter by `mealType` to provide relevant suggestions (e.g., suggest "Oats" only for breakfast).

### 4. Handling Private/Pending Recipes
- **Search Limitation**: The API hides "Pending" items from global search.
- **Member Search**: Use `get_member_foods` to find custom items.
- **Direct ID**: If the user provides a recipe ID, use `get_recipe` directly to see ingredients.

## Progressive Disclosure Guidance

- **Metadata level**: You know what this skill does (Nutrition).
- **Body level**: You know the procedures (Read-before-Write, Combos).
- **Reference level**: Refer to [capabilities.md](references/capabilities.md) ONLY when you need the exact JSON schema for an `execute` call.

## Operational Rules

- **Strict Date Parsing**: Use YYYY-MM-DD.
- **Descriptive Names**: Always provide a clear `foodEntryName` or `mealItemName`.
- **Safety**: Do not delete entries unless explicitly requested.
