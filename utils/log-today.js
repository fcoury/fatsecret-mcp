console.log(JSON.stringify({
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "execute",
    "arguments": {
      "tool": "add_food_entry",
      "arguments": { 
        "foodId": "35718", 
        "foodEntryName": "Manzana (desde Combo Terminal)",
        "servingId": "32915", 
        "numberOfUnits": 1,
        "mealType": "other"
      }
    }
  },
  "id": 1
}));
