console.log(JSON.stringify({
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "execute",
    "arguments": {
      "tool": "search_foods",
      "arguments": { "searchExpression": "Apple", "maxResults": 1 }
    }
  },
  "id": 1
}));
