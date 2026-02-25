# Objective
Fix the "Unknown method" errors for `autocomplete_foods` and `search_by_barcode` in the FatSecret MCP.

# Analysis
The `foods.autocomplete.v2` and `food.find_id_for_barcode.v2` methods are listed as **Premier Exclusive** in the FatSecret documentation. Standard API keys do not have access to these endpoints, which results in the `Unknown method` (Error 10) response from the API.

# Implementation Steps
1. **Remove Unsupported Endpoints from MCP:**
   - Remove the `autocomplete_foods` and `search_by_barcode` tools from the `toolRegistry` in `src/index.ts`.
2. **Update the Nutritionist Skill:**
   - Remove references to `autocomplete_foods` and `search_by_barcode` from `skills/fatsecret-nutritionist/references/capabilities.md`.
   - Remove the "Barcode Identification" workflow from `skills/fatsecret-nutritionist/SKILL.md`.
3. **Build and Test:**
   - Run `npm run build`.
   - Test the MCP with `node utils/test-meta.js` to ensure `discovery` no longer lists the removed tools and that other tools still function correctly.
4. **Document the Changes:**
   - Run the `crear-historial-docs` skill to record this fix, noting that Premier Exclusive features were pruned for standard API key compatibility.
