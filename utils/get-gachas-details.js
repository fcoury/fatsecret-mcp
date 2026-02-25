console.log(JSON.stringify({
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "execute",
    "arguments": {
      "tool": "get_meal_details",
      "arguments": { "mealId": "17297090" }
    }
  },
  "id": 1
}));
