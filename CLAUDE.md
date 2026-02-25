# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## FatSecret MCP Pipe-First Execution (Critical)

For user task execution in this repo (e.g. "apunta", "anade", "registra" foods/combos), use direct one-shot JSON-RPC piping to `node dist/index.js`.

- Do NOT use `npm start` / `npm run dev` / interactive sessions for these requests.
- Do NOT create helper scripts just to call the MCP.
- In one-shot pipe mode, call `tools/call` directly (no `initialize` needed).

PowerShell `discovery` example:
```powershell
'{"jsonrpc":"2.0","method":"tools/call","params":{"name":"discovery","arguments":{}},"id":1}' | node dist/index.js
```

PowerShell `execute` example:
```powershell
'{"jsonrpc":"2.0","method":"tools/call","params":{"name":"execute","arguments":{"tool":"TOOL_NAME","arguments":{}}},"id":1}' | node dist/index.js
```

Prefer the skill `.agents/skills/fatsecret-orchestrator/` for natural diary/combo logging behavior.

## Build and Development Commands

- **Build**: `npm run build` - Compiles TypeScript to JavaScript in the `dist/` directory
- **Start**: `npm start` - Runs the compiled server from `dist/index.js`
- **Development**: `npm run dev` - Builds and runs the server in one command
- **Clean**: `npm run clean` - Removes the `dist/` directory

## Project Architecture

This is a Model Context Protocol (MCP) server that provides access to the FatSecret nutrition database API through a 3-legged OAuth authentication system.

### Core Components

- **`src/index.ts`**: Main MCP server implementation with FatSecret API integration
  - Implements OAuth 1.0a flow for user authentication
  - Provides nutrition database search and user diary management tools
  - Handles secure credential storage in `~/.fatsecret-mcp-config.json`

- **`src/cli.ts`**: Standalone OAuth console utility for interactive authentication
  - Guides users through the complete OAuth flow
  - Opens browser for authorization and processes verifier codes
  - Alternative to MCP-based authentication

### Authentication Flow

The server supports multiple authentication methods:
1. **OAuth Console Utility**: Run `node dist/cli.js` for interactive setup
2. **MCP Tools**: Use `set_credentials`, `start_oauth_flow`, and `complete_oauth_flow` tools
3. **Environment Variables**: Set `CLIENT_ID` and `CLIENT_SECRET` in `.env`

### API Integration

- **Base URL**: `https://platform.fatsecret.com/rest/server.api`
- **OAuth URLs**: `https://authentication.fatsecret.com/oauth/*`
- **Date Format**: FatSecret API expects dates as "days since epoch" (automatically converted from YYYY-MM-DD)

### Available MCP Tools

**Authentication**:
- `set_credentials` - Set FatSecret API credentials
- `start_oauth_flow` - Begin OAuth authentication
- `complete_oauth_flow` - Complete OAuth with verifier code
- `check_auth_status` - Check current authentication status

**Food Database**:
- `search_foods` - Search nutrition database
- `get_food` - Get detailed food information

**Recipe Database**:
- `search_recipes` - Search recipe database
- `get_recipe` - Get detailed recipe information

**User Data** (requires authentication):
- `get_user_profile` - Get authenticated user profile
- `get_user_food_entries` - Get food diary entries
- `add_food_entry` - Add entries to user diary

### Testing Utilities

Located in `utils/` directory:
- **`test-interactive.js`**: Menu-driven interface for testing all MCP tools
- **`test-date-conversion.js`**: Validates date conversion logic
- **`test-mcp.js`**: Direct JSON-RPC testing via pipe

Run tests after building: `npm run build && node utils/test-interactive.js`

### Configuration Storage

- Configuration stored in `~/.fatsecret-mcp-config.json`
- Contains API credentials and OAuth tokens
- Automatically created during authentication flow

### Key Dependencies

- `@modelcontextprotocol/sdk`: MCP server framework
- `node-fetch`: HTTP requests to FatSecret API
- `dotenv`: Environment variable loading
- `crypto`: OAuth signature generation

## 📊 Plan Nutricional Personal - Carlos

### Perfil Usuario
- **Peso actual:** 77 kg
- **Altura:** 180 cm
- **Grasa corporal actual:** 16–17%
- **Objetivo:** Definición → 12–13% grasa corporal

### 🔥 Calorías y Déficit
- **TDEE estimado:** 2500–2600 kcal
- **Ingesta objetivo:** 2000–2100 kcal
- **Déficit:** 18–22% (~0,5–0,7 kg/semana)

### ⚖️ Macronutrientes diarios
- **Proteína:** 170 g (2,2 g/kg) → ~32%
- **Grasas:** 70 g (0,9 g/kg) → ~30%
- **Carbohidratos:** 170 g → ~38%

### 📅 Horarios de comida (ejemplo)
- **12:00 (rompe ayuno):** Huevos + aguacate + pan/verdura
- **15:00 (pre-entreno):** Whey + avena/plátano
- **16:30 (post-entreno):** Pollo/pavo + arroz + verduras + AOVE
- **20:30 (cena):** Carne magra (pollo, pavo, ternera 5–10% grasa) + patata/boniato + ensalada + frutos secos
- **23:00 (recena):** Yogur griego 0% + canela

### 💊 Suplementación clave
- **Proteína en polvo (whey/aislado)** → para cuadrar macros
- **Omega-3 (EPA/DHA 2–3 g/día)** → sustituto del pescado
- **Creatina 5 g/día** → fuerza y rendimiento

### 🎯 Objetivo 3 meses
- **Peso esperado:** 71–72 kg
- **Grasa corporal:** 12–13%
- **Pérdida de músculo:** 0–1 kg (mínima si cumples proteína y entreno)

### 🍽️ Comandos Claude Code para Plan Nutricional
- **`/plan`** - Mostrar resumen completo del plan nutricional
- **`/macros`** - Calcular estado actual de macros vs objetivos
- **`/deficit`** - Analizar déficit calórico del día actual
