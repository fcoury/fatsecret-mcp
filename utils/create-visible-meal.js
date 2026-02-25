console.log(JSON.stringify({
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "execute",
    "arguments": {
      "tool": "create_saved_meal",
      "arguments": { 
        "name": "Combo Test Terminal", 
        "description": "Creado desde Gemini CLI para verificar en la web" 
      }
    }
  },
  "id": 1
}));
