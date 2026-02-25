# FatSecret Nutritionist Capabilities

This document details the internal tools available through the FatSecret MCP via the `execute` tool.

## Search and Discovery

### `search_foods`
Search for foods in the database.
- `searchExpression` (string, required): Term to search for.
- `pageNumber` (number, default: 0)
- `maxResults` (number, default: 20)

### `autocomplete_foods`
Get suggestions as you type.
- `expression` (string, required): Partial food name.
- `maxResults` (number, default: 10)

### `get_food`
Get detailed nutritional data and serving IDs.
- `foodId` (string, required)

### `search_by_barcode`
Find food by GTIN-13 barcode.
- `barcode` (string, required)

## Diary Management

### `add_food_entry`
Add a food item to the user's diary.
- `foodId` (string, required)
- `foodEntryName` (string, required): Display name in diary.
- `servingId` (string, required)
- `numberOfUnits` (number, required)
- `mealType` (enum: [breakfast, lunch, dinner, other], required)
- `date` (string, optional): YYYY-MM-DD (defaults to today)

### `get_user_food_entries`
List diary entries for a date.
- `date` (string, optional): YYYY-MM-DD

### `get_food_month_summary`
Monthly nutritional totals.
- `date` (string, optional): Any date in the target month.

## User Profile

### `get_weight_month`
Weight history for a month.
- `date` (string, optional)

## Configuration

### `set_credentials`
Set API Client ID and Secret.

### `start_oauth_flow` / `complete_oauth_flow`
Manage 3-legged authentication.
