console.log(JSON.stringify({
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "execute",
    "arguments": {
      "tool": "get_food",
      "arguments": { "foodId": "35755" }
    }
  },
  "id": 1
}));
