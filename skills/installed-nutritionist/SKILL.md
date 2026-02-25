---
name: fatsecret-nutritionist
description: Procedural knowledge for FatSecret API orchestration using Meta-Tool MCP pattern. Use for nutrition/exercise tracking, diary management, and food discovery.
---

# FatSecret Nutritionist

Expert assistant for managing nutrition and exercise using the FatSecret API. This skill orchestrates the **FatSecret MCP** using a Meta-Tool pattern (Discovery -> Execution).

## Meta-Tool Pattern

Instead of exposing dozens of tools, the FatSecret MCP provides only two:
1. `discovery`: Call this when you need a list of available tools and descriptions.
2. `execute`: Call this to run an internal tool with specific arguments.

## Discovery and Capabilities

For detailed schemas of all available internal tools, refer to:
[capabilities.md](references/capabilities.md)

## Common Workflows

### Add a Food Entry

1. **Search**: Find the food item.
   - Use `execute(tool: "search_foods", arguments: { searchExpression: "term" })`.
2. **Details**: Get nutritional info and serving IDs.
   - Use `execute(tool: "get_food", arguments: { foodId: "id" })`.
3. **Log**: Add to the diary.
   - Use `execute(tool: "add_food_entry", arguments: { ... })`.

### Barcode Identification

1. **Barcode Lookup**:
   - Use `execute(tool: "search_by_barcode", arguments: { barcode: "123..." })`.
2. **Log Results**: Follow the details/log steps above.

### Authentication Status

1. **Discovery**: Call `discovery` to verify tools are available.
2. **Check Profile**: Use `execute(tool: "get_user_food_entries", arguments: {})` to test user token.

## Principles

- **Progressive Disclosure**: If unsure of the schema for a tool, consult [capabilities.md](references/capabilities.md) or use `discovery`.
- **Validation**: Always verify `servingId` from `get_food` before logging an entry.
- **Context Management**: Only retrieve the data needed for the current step.
