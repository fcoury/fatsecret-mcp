console.log(JSON.stringify({
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "execute",
    "arguments": {
      "tool": "add_food_to_meal",
      "arguments": { 
        "mealId": "47318534", 
        "foodId": "35718", 
        "mealItemName": "Apple Test",
        "servingId": "32915", 
        "numberOfUnits": 2 
      }
    }
  },
  "id": 1
}));
