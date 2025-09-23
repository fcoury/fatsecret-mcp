# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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