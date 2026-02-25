console.log(JSON.stringify({
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "execute",
    "arguments": {
      "tool": "edit_saved_meal_name",
      "arguments": { 
        "mealId": "47318666", 
        "name": "Combo Test Terminal", 
        "description": "Ahora con checks marcados",
        "meals": "Breakfast,Other" 
      }
    }
  },
  "id": 1
}));
