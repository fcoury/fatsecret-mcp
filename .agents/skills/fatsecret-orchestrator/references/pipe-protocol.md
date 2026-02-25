# FatSecret MCP Pipe Protocol (One-Shot)

This project's MCP server is most reliable from CLI when called as a one-shot stdio process:

- Send one JSON-RPC request through stdin
- Receive one JSON response on stdout
- Process exits

## Rule 1: No Interactive Session for User Tasks

For user requests like "apunta..." / "registra...", do not start long-running or interactive sessions.

- Avoid: `npm start`, `npm run dev`, custom interactive harnesses
- Use: direct pipe to `node dist/index.js`

## Rule 2: No Initialize Needed in One-Shot Mode

When using direct pipe, call `tools/call` directly. Do not send MCP `initialize`.

## JSON-RPC Envelope

### Discovery
```json
{"jsonrpc":"2.0","method":"tools/call","params":{"name":"discovery","arguments":{}},"id":1}
```

### Execute
```json
{"jsonrpc":"2.0","method":"tools/call","params":{"name":"execute","arguments":{"tool":"TOOL_NAME","arguments":{}}},"id":1}
```

## Shell Snippets

### PowerShell
```powershell
'{"jsonrpc":"2.0","method":"tools/call","params":{"name":"discovery","arguments":{}},"id":1}' | node dist/index.js
```

### PowerShell + UTF-8 (required if JSON contains accents)
```powershell
$utf8 = [System.Text.UTF8Encoding]::new($false)
[Console]::InputEncoding = $utf8
[Console]::OutputEncoding = $utf8
$OutputEncoding = $utf8
'{"jsonrpc":"2.0","method":"tools/call","params":{"name":"execute","arguments":{"tool":"TOOL_NAME","arguments":{"foodEntryName":"Canónigos"}}},"id":1}' | node dist/index.js
```

### Bash
```bash
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"discovery","arguments":{}},"id":1}' | node dist/index.js
```

## Error Recovery

### Tool not found
1. Run `discovery` again (tool catalog drift).
2. Retry using the exact internal tool name returned by discovery.

### Invalid args / schema mismatch
1. Open `references/capabilities.md`.
2. Rebuild the `execute.arguments` payload with exact field names.
3. Retry once.

### Quoting issues (shell)
- Prefer single-quoted JSON strings in PowerShell and Bash examples.
- Keep the JSON in one line.
- Do not mix shell variables until the base command works.
- In Windows PowerShell, set `[Console]::InputEncoding`, `[Console]::OutputEncoding`, and `$OutputEncoding` to UTF-8 before piping when JSON values contain non-ASCII characters (`Rúcula`, `Canónigos`, etc.).

## Logging Reliability Rule

Before any write (`add_food_entry`) from a combo:
- Read combo state with `get_meal_details`
- Modify in memory
- Execute writes item-by-item

This prevents stale combo ingredients from being logged.
