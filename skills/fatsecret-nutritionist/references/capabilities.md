# FatSecret Nutritionist Capabilities

This document provides technical schemas and operational guidance for the FatSecret MCP tools. Access these via the `execute` proxy tool.

## 1. Authentication and Setup

### `set_credentials`
Configure API access.
- `clientId` (string, required)
- `clientSecret` (string, required)

### `start_oauth_flow`
Get Authorization URL for 3-legged OAuth.
- `callbackUrl` (string, optional, default: "oob")

### `complete_oauth_flow`
Finalize authentication.
- `requestToken` (string, required)
- `requestTokenSecret` (string, required)
- `verifier` (string, required)

---

## 2. Food Discovery

### `search_foods`
Search the global FatSecret database.
- `searchExpression` (string, required)
- `pageNumber` (number, default: 0)
- `maxResults` (number, default: 20)

### `get_food`
Get nutritional data and servings for a food item.
- `foodId` (string, required)
**Note:** Always call this before logging to get valid `servingId` values.

---

## 3. Diary Management

### `add_food_entry`
Log a food consumption.
- `foodId` (string, required)
- `foodEntryName` (string, required): Name to show in the diary.
- `servingId` (string, required)
- `numberOfUnits` (number, required)
- `mealType` (enum: [breakfast, lunch, dinner, other], required)
- `date` (string, optional): YYYY-MM-DD (defaults to today)

### `delete_food_entry`
Remove a log from the diary.
- `foodEntryId` (string, required)

### `get_user_food_entries`
List daily consumption.
- `date` (string, optional): YYYY-MM-DD

### `get_food_month_summary`
Monthly nutritional breakdown.
- `date` (string, optional): Any date in the target month.

---

## 4. Saved Meals (Combos) - RECOMMENDED FOR CUSTOM LOGS

### `get_saved_meals`
List all user combos.

### `get_meal_details`
List foods and quantities inside a specific Saved Meal.
- `mealId` (string, required)
**Reliability Rule:** Always call this before logging a combo to ensure you have the latest ingredient list.

### `create_saved_meal`
Create a new combo container.
- `name` (string, required)
- `description` (string, optional)
- `meals` (string, optional): Comma-separated (e.g., "Breakfast,Lunch") to show in web UI checks.

### `edit_saved_meal_name`
Update combo metadata.
- `mealId` (string, required)
- `name` (string, required)
- `description` (string, optional)
- `meals` (string, optional)

### `add_food_to_meal`
Add an ingredient to a combo.
- `mealId` (string, required)
- `foodId` (string, required)
- `mealItemName` (string, required)
- `servingId` (string, required)
- `numberOfUnits` (number, required)

### `edit_food_in_meal`
Update ingredient quantity/serving.
- `mealItemId` (string, required)
- `servingId` (string, required)
- `numberOfUnits` (number, required)

### `remove_food_from_meal`
Delete an ingredient from a combo.
- `mealItemId` (string, required)

---

## 5. Habits and Personal Profile

### `get_usual_foods`
Most eaten foods.
- `mealType` (string, optional): breakfast, lunch, dinner, other.

### `get_recent_foods`
Recently eaten foods.
- `mealType` (string, optional): breakfast, lunch, dinner, other.

### `get_member_foods`
Search user's private custom foods/recipes.
- `searchExpression` (string, optional)

### `get_weight_month`
Weight log history.
- `date` (string, optional)

---

## 6. Favorites

### `get_all_favorites`
List all favorited recipes.

### `manage_favorite_recipe`
Star/Unstar a recipe.
- `recipeId` (string, required)
- `action` (enum: [add, delete], required)

### `get_my_recipes`
List user cookbook (Note: pending items may be hidden; use get_member_foods).

### `search_my_recipes`
Search cookbook by name.

### `get_recipe`
Details/Ingredients of a specific recipe.
- `recipeId` (string, required)
