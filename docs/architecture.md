# Architecture and operation flow

The installed FatSecret MCP server uses Python 3.11 or later, MCP SDK 2.x, and
the `fatsecret` Python package. Network and browser latency dominate request
time, so a direct in-process Python adapter is faster and simpler than a
cross-language bridge.

## System boundaries

The server keeps four contracts separate:

1. The generated official OAS describes supported FatSecret Platform methods.
2. The manual member-web OAS describes unsupported HTML and WebForms
   automation.
3. The Python package implements authentication, requests, retries, parsing,
   write verification, and durable copy operations.
4. The MCP catalog controls model-visible names, profiles, annotations, and
   exposure policy.

Adding an OAS endpoint does not expose it automatically. A version-controlled
allowlist is the exposure source of truth. Runtime reflection supplies the
signature only after a resource and operation family has been reviewed; the
inventory then selects the highest numeric version in that family.

## Startup flow

The installed process starts as follows:

1. Once releases exist, `uvx fatsecret-mcp@latest` refreshes the latest package before
   launch. A persistent installation instead uses `uv tool upgrade
   fatsecret-mcp`.
2. `Settings.from_env()` loads the transport, profile, state directory, and
   credentials.
3. The server creates the official, member, authentication, telemetry, and
   durable-operation adapters.
4. The inventory scans explicitly approved public resource classes and keeps
   the highest `_vN` method for each endpoint family.
5. The catalog selects the baseline tools for the configured profile.
6. `MCPServer` registers only those typed handlers and returns them from
   `tools/list`.
7. The local event store records the profile and advertised tool names without
   recording arguments or results.

## Request flow

A normal tool request follows these steps:

1. MCP validates the generated input schema before dispatch.
2. The runtime starts a local trace event with the session, profile, tool, and
   capability identifiers.
3. AnyIO runs the synchronous Python backend outside the MCP event loop.
4. The backend applies authentication, authoritative `Retry-After` handling,
   parsing, mutation serialization, and read-after-write verification.
5. The adapter converts Pydantic models, dates, and decimals to structured JSON
   output.
6. The runtime records duration and a success or error class. It sanitizes
   exceptions before returning protocol error content.

The server never records credentials, cookies, headers, raw arguments, raw
responses, recipe text, food names, or upstream HTML.

## Capability reach flow

If the active profile does not advertise a needed operation, call
`resolve_fatsecret_capability` with a concise description of the operation.

The resolver performs these steps:

1. Search the 28-tool reviewed catalog and the latest-version backend
   inventory.
2. Rank candidates by stable names, operation families, resource terms, and
   documented descriptions.
3. Reject bootstrap tools and every dynamic mutation that lacks a curated
   idempotency and reconciliation wrapper.
4. For an installed `stdio` process, register only the selected wrapper and
   publish a tool-list-changed event.
5. Return selected, activated, and blocked tools with reason codes.
6. Record candidates, selections, activations, and eventual invocations for
   profile analysis.

Activation is monotonic and limited to eight additions per process. A reached
tool remains active until the installed server process exits. Streamable HTTP
returns `restart_required` because its process-global registry cannot safely
hold per-client overlays.

## Profile observability

The SQLite event store supports these analyses:

- Advertised-versus-invoked frequency by profile.
- Reached, selected, activated, and invoked conversion rates.
- Tool co-occurrence and sequence analysis.
- Latency and error-class heat maps.
- Profile misses and frequently requested backend operations.
- Dynamic schema additions and their context cost.

Profile assignments remain version-controlled decisions. Telemetry can suggest
promotion or demotion, but it cannot change profiles or authorization policy.
Rare destructive tools are not demoted based only on frequency.

## Mutation behavior

Recipe creation, ingredient addition, and recipe copy require caller-provided
idempotency keys. The server uses the backend SQLite stores to prevent duplicate
writes and to resume multi-request copies after rate limits or restarts.

Official food-diary creation also requires an idempotency key. Member mutations
are serialized across threads and installed server processes. Resumable copy
operations persist `Retry-After` deadlines instead of hiding them in a sleeping
HTTP client; direct member mutations wait for the authoritative delay.

Recipe replacement, ingredient replacement, deletion, and RDI changes use
desired-state semantics and read-after-write verification. Ambiguous writes
must be reconciled before retry.

The current backend implements ingredient replacement with an HTTP form
adapter. Live investigation found that FatSecret can require a browser-backed
submission for this operation. The MCP contract remains stable, but this path
is not considered production-complete until the backend provides and tests the
browser adapter.

## Release and update flow

Each MCP release pins one tested `fatsecret` backend release. The release
pipeline performs these steps:

1. Update the backend pin.
2. Rebuild and verify the latest-version inventory.
3. Validate official and member OAS mappings.
4. Run unit, protocol, restart, idempotency, and opt-in live tests.
5. Build and inspect the wheel and source distribution.
6. Publish the MCP package.

On the next client start, `uvx fatsecret-mcp@latest` refreshes the package and
launches the tested server-backend combination. A running process never
replaces its own code.
