# FatSecret MCP Server

A Model Context Protocol (MCP) server that provides access to the FatSecret nutrition database API with full 3-Legged OAuth authentication support.

## Features

- **Complete OAuth 1.0a Implementation**: Full 3-legged OAuth flow for user authentication
- **Food Database Access**: Search and retrieve detailed nutrition information
- **Recipe Database**: Search for recipes and get detailed cooking instructions
- **User Data Management**: Access user food diaries and add food entries
- **Secure Credential Storage**: Encrypted storage of API credentials and tokens

## Getting Started

### Prerequisites

- Node.js (v14 or higher)
- npm or yarn
- A FatSecret developer account

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/fatsecret-mcp.git
cd fatsecret-mcp

# Install dependencies
npm install

# Build the TypeScript
npm run build
```

## Setup

### 1. Get FatSecret API Credentials

1. Visit the [FatSecret Platform](https://platform.fatsecret.com/)
2. Create a developer account and register your application
3. Note down your **Client ID** and **Client Secret**

### 2. Configure the MCP Server

The server needs to be configured in your MCP client (like Claude Desktop). Add this to your MCP configuration:

```json
{
  "mcpServers": {
    "fatsecret": {
      "command": "node",
      "args": ["path/to/fatsecret-mcp-server/dist/index.js"]
    }
  }
}
```

### 3. Authentication Process

#### Option 1: Using the OAuth Console Utility (Recommended)

The easiest way to authenticate is using the included OAuth console utility:

```bash
# Make sure you've built the project first
npm run build

# Run the OAuth console utility
node dist/cli.js
```

This interactive utility will:
1. Ask for your Client ID and Client Secret
2. Save them securely in `~/.fatsecret-mcp-config.json`
3. Guide you through the OAuth flow:
   - Opens your browser to the FatSecret authorization page
   - Prompts you to paste the verifier code after authorization
   - Saves the access tokens for future use

#### Option 1a: Automated HTTP Session Login

For an account you control, the console can reproduce the OAuth1 PIN flow
without opening a browser. It requests an OAuth token, submits the FatSecret
`authorize.aspx` form in a cookie-preserving HTTP session, extracts the
verifier PIN, and exchanges it for permanent access tokens:

```bash
FATSECRET_CLIENT_ID=... \
FATSECRET_CLIENT_SECRET=... \
FATSECRET_USERNAME=... \
FATSECRET_PASSWORD=... \
node dist/cli.js --password-login
```

Only the client credentials and resulting OAuth access tokens are written to
`~/.fatsecret-mcp-config.json`. The username and password are not stored. The
config file is restricted to the current user (`0600`). FatSecret can
rate-limit repeated login attempts; reuse the saved token rather than logging
in on every server start.

#### Option 2: Manual Authentication via MCP Tools

If you prefer to authenticate through the MCP interface (e.g., in Claude):

1. **Set your API credentials:**
   ```
   Use tool: set_credentials
   Parameters:
   - clientId: "your_client_id_here"
   - clientSecret: "your_client_secret_here"
   ```

2. **Start the OAuth flow:**
   ```
   Use tool: start_oauth_flow
   Parameters:
   - callbackUrl: "oob" (for out-of-band authentication)
   ```

3. **Visit the authorization URL** provided in the response:
   - Log in to your FatSecret account (or create one)
   - Click "Allow" to authorize the application
   - Copy the verifier code shown on the page

4. **Complete the OAuth flow:**
   ```
   Use tool: complete_oauth_flow
   Parameters:
   - requestToken: [from step 2 response]
   - requestTokenSecret: [from step 2 response]
   - verifier: [the code you copied from the authorization page]
   ```

#### Option 3: Using Environment Variables

You can also provide credentials via environment variables:

```bash
# Create a .env file in the project root
CLIENT_ID=your_client_id_here
CLIENT_SECRET=your_client_secret_here

# The server will automatically load these on startup
```

Note: You'll still need to complete the OAuth flow for user-specific operations.

## Usage

### 1. Set API Credentials

First, set your FatSecret API credentials:

```
Use the set_credentials tool with your Client ID and Client Secret
```

### 2. Authenticate a User (3-Legged OAuth)

For user-specific operations, you need to complete the OAuth flow:

```
1. Use start_oauth_flow tool (with callback URL or "oob" for out-of-band)
2. Visit the provided authorization URL
3. Authorize the application and get the verifier code
4. Use complete_oauth_flow tool with the request token, secret, and verifier
```

### 3. Use the API

Once authenticated, you can use all available tools:

#### Food Search and Information

- `search_foods`: Search for foods in the database
- `get_food`: Get detailed nutrition information for a specific food

#### Recipe Search and Information

- `search_recipes`: Search for recipes
- `get_recipe`: Get detailed recipe information including ingredients and instructions

#### User Data (Requires Authentication)

- `get_user_profile`: Get the authenticated user's profile
- `get_user_food_entries`: Get food diary entries for a specific date
- `add_food_entry`: Add a food entry to the user's diary

#### Utility

- `check_auth_status`: Check current authentication status

## Available Tools

### Authentication Tools

#### `set_credentials`

Set your FatSecret API credentials.

**Parameters:**

- `clientId` (string, required): Your FatSecret Client ID
- `clientSecret` (string, required): Your FatSecret Client Secret

#### `start_oauth_flow`

Start the 3-legged OAuth flow.

**Parameters:**

- `callbackUrl` (string, optional): OAuth callback URL (default: "oob")

#### `complete_oauth_flow`

Complete the OAuth flow with authorization.

**Parameters:**

- `requestToken` (string, required): Request token from start_oauth_flow
- `requestTokenSecret` (string, required): Request token secret from start_oauth_flow
- `verifier` (string, required): OAuth verifier from authorization

#### `authenticate_with_password`

Run the automated HTTP-session OAuth1 PIN flow. `username` and `password` are
optional tool arguments; when omitted, the server reads `FATSECRET_USERNAME`
and `FATSECRET_PASSWORD`. The password is never saved. Prefer the console
command above for initial setup so passwords do not pass through an MCP client.

#### `check_auth_status`

Check current authentication status.

### Food Database Tools

#### `search_foods`

Search for foods in the FatSecret database.

**Parameters:**

- `searchExpression` (string, required): Search term
- `pageNumber` (number, optional): Page number (default: 0)
- `maxResults` (number, optional): Max results per page (default: 20)

#### `get_food`

Get detailed information about a specific food.

**Parameters:**

- `foodId` (string, required): FatSecret food ID

### Recipe Database Tools

#### `search_recipes`

Search for recipes in the FatSecret database.

**Parameters:**

- `searchExpression` (string, required): Search term
- `pageNumber` (number, optional): Page number (default: 0)
- `maxResults` (number, optional): Max results per page (default: 20)

#### `get_recipe`

Get detailed information about a specific recipe.

**Parameters:**

- `recipeId` (string, required): FatSecret recipe ID

### User Data Tools (Requires Authentication)

#### `get_user_profile`

Get the authenticated user's profile information.

#### `get_user_food_entries`

Get user's food diary entries for a specific date.

**Parameters:**

- `date` (string, optional): Date in YYYY-MM-DD format (default: today)

#### `add_food_entry`

Add a food entry to the user's diary.

**Parameters:**

- `foodId` (string, required): FatSecret food ID
- `servingId` (string, required): Serving ID for the food
- `quantity` (number, required): Quantity of the serving
- `mealType` (string, required): Meal type (breakfast, lunch, dinner, snack)
- `date` (string, optional): Date in YYYY-MM-DD format (default: today)

## Example Workflow

1. **Setup Credentials:**

   ```
   Tool: set_credentials
   - clientId: "your_client_id"
   - clientSecret: "your_client_secret"
   ```

2. **Search for Foods:**

   ```
   Tool: search_foods
   - searchExpression: "chicken breast"
   ```

3. **Get Food Details:**

   ```
   Tool: get_food
   - foodId: "12345"
   ```

4. **Authenticate User (if needed):**

   ```
   Tool: start_oauth_flow
   - callbackUrl: "oob"

   # Follow the authorization URL, then:

   Tool: complete_oauth_flow
   - requestToken: "from_start_oauth_flow"
   - requestTokenSecret: "from_start_oauth_flow"
   - verifier: "from_authorization_page"
   ```

5. **Add Food to Diary:**
   ```
   Tool: add_food_entry
   - foodId: "12345"
   - servingId: "67890"
   - quantity: 1
   - mealType: "lunch"
   ```

## Configuration Storage

The server stores configuration (credentials and tokens) in `~/.fatsecret-mcp-config.json`. This file contains:

- API credentials (Client ID and Secret)
- OAuth access tokens (when authenticated)
- User ID (when authenticated)

## Security Notes

- Credentials are stored locally in your home directory
- OAuth tokens are securely managed using proper HMAC-SHA1 signing
- All API communications use HTTPS
- The server implements proper OAuth 1.0a security measures

## API Reference

This server implements the FatSecret Platform API. For detailed API documentation, visit:

- [FatSecret Platform API Documentation](https://platform.fatsecret.com/docs/guides)
- [OAuth 1.0a Specification](https://tools.ietf.org/html/rfc5849)

## Error Handling

The server provides detailed error messages for common issues:

- Missing or invalid credentials
- OAuth flow errors
- API rate limiting
- Network connectivity issues
- Invalid parameters

## Testing

### Testing from the Command Line

The project includes several test utilities:

#### 1. Interactive Test Tool

```bash
# Run the interactive test menu
node test-interactive.js
```

This provides a menu-driven interface to test all MCP tools.

#### 2. Date Conversion Test

```bash
# Test the date conversion logic
node test-date-conversion.js
```

Verifies that dates are correctly converted to FatSecret's "days since epoch" format.

#### 3. Direct JSON-RPC Testing

```bash
# Send test messages via pipe
node test-mcp.js | node dist/index.js
```

### Testing in Claude Desktop

1. Restart Claude Desktop after configuring the MCP server
2. Look for "fatsecret" in the available tools
3. Start by using `check_auth_status` to verify the connection

## Troubleshooting

### Common Issues

#### "Invalid integer value: date"
- The FatSecret API expects dates as days since epoch (1970-01-01)
- The server automatically converts YYYY-MM-DD format dates
- If you get this error, ensure you're using the latest version

#### OAuth Authentication Fails
- Verify your Client ID and Client Secret are correct
- Ensure you're using the correct URLs (authentication.fatsecret.com for OAuth)
- Check that you're copying the entire verifier code from the authorization page

#### Server Not Found in Claude
- Ensure the path in your MCP configuration is absolute, not relative
- Verify the server was built successfully (`npm run build`)
- Check Claude's logs for any error messages

#### "User authentication required"
- Complete the OAuth flow using either the CLI utility or MCP tools
- Check authentication status with `check_auth_status` tool
- Tokens are saved in `~/.fatsecret-mcp-config.json`

## Development

To modify or extend the server:

```bash
# Install dependencies
npm install

# Build and run
npm run build
npm start

# Development mode with auto-rebuild
npm run dev
```

### Project Structure

```
fatsecret-mcp/
├── src/
│   ├── index.ts        # Main MCP server implementation
│   └── cli.ts          # OAuth console utility
├── dist/               # Compiled JavaScript files
├── test-*.js           # Test utilities
├── package.json
├── tsconfig.json
└── README.md
```

## License

MIT License - see LICENSE file for details.
