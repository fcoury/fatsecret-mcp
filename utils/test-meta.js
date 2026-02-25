/**
 * Test Meta-Tool Pattern for FatSecret MCP
 * Usage: node utils/test-meta.js | node dist/index.js
 */

// 1. Initialize
console.log(JSON.stringify({
  jsonrpc: "2.0",
  method: "initialize",
  params: { protocolVersion: "0.1.0", capabilities: {} },
  id: 1
}));

// 2. Discovery (List exposed tools: discovery and execute)
console.log(JSON.stringify({
  jsonrpc: "2.0",
  method: "tools/list",
  params: {},
  id: 2
}));

// 3. Call Discovery (List internal tool names)
console.log(JSON.stringify({
  jsonrpc: "2.0",
  method: "tools/call",
  params: {
    name: "discovery",
    arguments: {}
  },
  id: 3
}));

// 4. Call Execute (Search for "apple" using internal tool)
console.log(JSON.stringify({
  jsonrpc: "2.0",
  method: "tools/call",
  params: {
    name: "execute",
    arguments: {
      tool: "search_foods",
      arguments: {
        searchExpression: "apple",
        maxResults: 2
      }
    }
  },
  id: 4
}));
