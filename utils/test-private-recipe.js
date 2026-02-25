console.log(JSON.stringify({
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "execute",
    "arguments": {
      "tool": "get_recipe",
      "arguments": {
        "recipeId": "77729465"
      }
    }
  },
  "id": 1
}));
