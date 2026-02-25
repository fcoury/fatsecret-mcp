console.log(JSON.stringify({
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "execute",
    "arguments": {
      "tool": "create_saved_meal",
      "arguments": { "name": "MCP Test Combo", "description": "Prueba de CRUD desde terminal" }
    }
  },
  "id": 1
}));
