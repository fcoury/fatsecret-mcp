console.log(JSON.stringify({
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "execute",
    "arguments": {
      "tool": "get_my_recipes",
      "arguments": {
        "maxResults": 50
      }
    }
  },
  "id": 1
}));
