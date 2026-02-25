console.log(JSON.stringify({
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "execute",
    "arguments": {
      "tool": "add_food_to_meal",
      "arguments": { 
        "mealId": "47318666", 
        "foodId": "35718", 
        "mealItemName": "Manzana de Prueba",
        "servingId": "32915", 
        "numberOfUnits": 1 
      }
    }
  },
  "id": 1
}));
