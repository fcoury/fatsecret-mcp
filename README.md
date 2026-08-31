# FatSecret MCP

Python MCP 2.x server for the official FatSecret Platform API and the
unofficial authenticated member website API provided by `fatsecret`.

## Run

After this package and its pinned `fatsecret==5.0.0` backend are published, run
the latest release and resolve it again on every process start:

```bash
uvx fatsecret-mcp@latest
```

For this checkout, `uv` uses the adjacent `../fatsecret` backend:

```bash
uv sync
uv run fatsecret-mcp --profile default
```

Example MCP client configuration:

```json
{
  "mcpServers": {
    "fatsecret": {
      "command": "uvx",
      "args": ["fatsecret-mcp@latest"]
    }
  }
}
```

`uvx ...@latest` updates on process start. A running process never replaces
its own code. A persistent installation uses `uv tool upgrade fatsecret-mcp`.

## Configure

Official Platform operations use `FATSECRET_CLIENT_ID`,
`FATSECRET_CLIENT_SECRET`, and optional delegated `FATSECRET_ACCESS_TOKEN` and
`FATSECRET_ACCESS_TOKEN_SECRET` values. Member website operations use
`FATSECRET_USERNAME` and `FATSECRET_PASSWORD`.

The bootstrap profile exposes OAuth setup tools. Persisted API secrets use the
operating-system keyring; member credentials remain environment-only.

## Profiles

Profiles keep unused schemas out of model context. The resolver is present in
every profile.

| Profile | Initial tool set |
| --- | --- |
| `default`, `member` | Member recipes, RDI, auth status, resolver |
| `discovery` | Public food and recipe discovery, auth status, resolver |
| `diary` | Profile, diary, weight, auth status, resolver |
| `bootstrap` | Credential and OAuth setup, resolver |
| `full` | All 28 curated tools |

The 13 compatibility tools are:

```text
set_credentials, start_oauth_flow, complete_oauth_flow,
authenticate_with_password, check_auth_status, search_foods, get_food,
search_recipes, get_recipe, get_user_profile, get_user_food_entries,
add_food_entry, get_weight_month
```

The 14 member tools are:

```text
get_member_rdi, set_member_rdi, list_member_recipes, get_member_recipe,
create_member_recipe, replace_member_recipe, delete_member_recipe,
list_member_food_portions, add_member_recipe_ingredient,
replace_member_recipe_ingredient, delete_member_recipe_ingredient,
copy_member_recipe, get_member_operation, resume_member_operation
```

`resolve_fatsecret_capability` searches those tools plus a version-controlled
allowlist of official backend operation families. It selects only the latest
installed `_vN` implementation for each family. On `stdio`, a selected wrapper
can be activated and a tool-list-change notification is published. Unreviewed
dynamic mutations are never activated. Streamable HTTP reports that a restart
and profile change are required because its high-level registry is process-wide.

Some official operations require Premier or a specific OAuth scope. Resolver
results expose known access requirements; FatSecret remains authoritative for
account entitlement.

## Observability

Local SQLite telemetry records tool names, capability decisions, rankings,
reason codes, latency, profile, and schema size. It does not record arguments,
results, credentials, recipe text, food names, headers, or cookies.

```bash
uv run fatsecret-mcp --observability-report
```

The report shows use frequency, transitions, reached-tool conversion, profile
misses, and coarse session-goal counts. Disable telemetry with
`FATSECRET_MCP_TELEMETRY=0`.

## Unsupported Interface Boundary

Member recipe and RDI tools automate `foods.fatsecret.com`; they are not part of
FatSecret's supported Platform API. Writes use exact IDs, serialized mutation,
idempotency where creation can duplicate data, and read-after-write checks.

Ingredient replacement currently uses the backend HTTP form adapter. Live
testing found accounts for which FatSecret requires browser-backed submission,
so this operation is experimental until the backend ships that adapter.

See [docs/architecture.md](docs/architecture.md) for the complete startup,
request, retry, capability reach, observability, and release flows.

## Verify

```bash
uv run ruff format --check src tests
uv run ruff check src tests
uv run basedpyright
uv run pytest -q
uv build --no-sources
```
