const logFood = (name, foodId, servingId) => JSON.stringify({
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "execute",
    "arguments": {
      "tool": "add_food_entry",
      "arguments": { 
        "foodId": foodId, 
        "foodEntryName": name,
        "servingId": servingId, 
        "numberOfUnits": 1,
        "mealType": "other"
      }
    }
  },
  "id": Math.floor(Math.random() * 1000)
});

console.log(logFood("Manzana (Test Final)", "35718", "32915"));
console.log(logFood("Platano (Test Final)", "35755", "32978"));
