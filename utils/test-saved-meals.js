console.log(JSON.stringify({
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "execute",
    "arguments": {
      "tool": "get_saved_meals",
      "arguments": {}
    }
  },
  "id": 1
}));
