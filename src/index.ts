#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ErrorCode,
  ListToolsRequestSchema,
  McpError,
} from "@modelcontextprotocol/sdk/types.js";
import crypto from "crypto";
import fetch from "node-fetch";
import querystring from "querystring";
import fs from "fs/promises";
import path from "path";
import os from "os";
import * as dotenv from "dotenv";

// Suppress dotenv console output by temporarily overriding console.log
const originalLog = console.log;
console.log = () => {};
dotenv.config();
console.log = originalLog;

interface FatSecretConfig {
  clientId: string;
  clientSecret: string;
  accessToken?: string;
  accessTokenSecret?: string;
  userId?: string;
}

interface OAuthToken {
  oauth_token: string;
  oauth_token_secret: string;
  oauth_callback_confirmed?: string;
}

interface AccessToken {
  oauth_token: string;
  oauth_token_secret: string;
  user_id?: string;
}

class FatSecretMCPServer {
  private server: Server;
  private config: FatSecretConfig;
  private configPath: string;
  private readonly baseUrl = "https://platform.fatsecret.com/rest/server.api";
  private readonly requestTokenUrl = "https://authentication.fatsecret.com/oauth/request_token";
  private readonly authorizeUrl = "https://authentication.fatsecret.com/oauth/authorize";
  private readonly accessTokenUrl = "https://authentication.fatsecret.com/oauth/access_token";

  constructor() {
    this.server = new Server(
      {
        name: "fatsecret-mcp-server",
        version: "0.1.0",
      }
    );

    this.configPath = path.join(os.homedir(), ".fatsecret-mcp-config.json");
    this.config = {
      clientId: process.env.CLIENT_ID || "",
      clientSecret: process.env.CLIENT_SECRET || "",
    };

    this.setupToolHandlers();
  }

  private async loadConfig(): Promise<void> {
    try {
      const configData = await fs.readFile(this.configPath, "utf-8");
      this.config = { ...this.config, ...JSON.parse(configData) };
    } catch (error) {
      // Config file doesn't exist, will be created when credentials are set
    }
  }

  private async saveConfig(): Promise<void> {
    await fs.writeFile(this.configPath, JSON.stringify(this.config, null, 2));
  }

  private generateNonce(): string {
    return crypto.randomBytes(16).toString("hex");
  }

  private generateTimestamp(): string {
    return Math.floor(Date.now() / 1000).toString();
  }

  private dateToFatSecretFormat(dateString?: string): string {
    // Convert date to days since epoch (1970-01-01)
    // If no date provided, use today
    const date = dateString ? new Date(dateString) : new Date();
    const epochStart = new Date('1970-01-01');
    const daysSinceEpoch = Math.floor((date.getTime() - epochStart.getTime()) / (1000 * 60 * 60 * 24));
    return daysSinceEpoch.toString();
  }

  private percentEncode(str: string): string {
    return encodeURIComponent(str)
      .replace(
        /[!'()*]/g,
        (c) => "%" + c.charCodeAt(0).toString(16).toUpperCase(),
      );
  }

  private createSignatureBaseString(
    method: string,
    url: string,
    parameters: Record<string, string>,
  ): string {
    const sortedParams = Object.keys(parameters)
      .sort()
      .map((key) =>
        `${this.percentEncode(key)}=${this.percentEncode(parameters[key])}`
      )
      .join("&");

    return [
      method.toUpperCase(),
      this.percentEncode(url),
      this.percentEncode(sortedParams),
    ].join("&");
  }

  private createSigningKey(
    clientSecret: string,
    tokenSecret: string = "",
  ): string {
    return `${this.percentEncode(clientSecret)}&${
      this.percentEncode(tokenSecret)
    }`;
  }

  private generateSignature(
    method: string,
    url: string,
    parameters: Record<string, string>,
    clientSecret: string,
    tokenSecret: string = "",
  ): string {
    const baseString = this.createSignatureBaseString(method, url, parameters);
    const signingKey = this.createSigningKey(clientSecret, tokenSecret);

    return crypto
      .createHmac("sha1", signingKey)
      .update(baseString)
      .digest("base64");
  }

  private createOAuthHeader(
    method: string,
    url: string,
    additionalParams: Record<string, string> = {},
    token?: string,
    tokenSecret?: string,
    regularParams: Record<string, string> = {},
  ): string {
    const timestamp = this.generateTimestamp();
    const nonce = this.generateNonce();

    const oauthParams: Record<string, string> = {
      oauth_consumer_key: this.config.clientId,
      oauth_nonce: nonce,
      oauth_signature_method: "HMAC-SHA1",
      oauth_timestamp: timestamp,
      oauth_version: "1.0",
      ...additionalParams,
    };

    if (token) {
      oauthParams.oauth_token = token;
    }

    // For signature calculation, we need ALL parameters (OAuth + regular)
    const allParams = { ...oauthParams, ...regularParams };

    const signature = this.generateSignature(
      method,
      url,
      allParams,
      this.config.clientSecret,
      tokenSecret,
    );

    oauthParams.oauth_signature = signature;

    const headerParts = Object.keys(oauthParams)
      .sort()
      .map((key) =>
        `${this.percentEncode(key)}="${this.percentEncode(oauthParams[key])}"`
      )
      .join(", ");

    return `OAuth ${headerParts}`;
  }

  private async makeOAuthRequest(
    method: string,
    url: string,
    params: Record<string, string> = {},
    token?: string,
    tokenSecret?: string,
  ): Promise<any> {
    const timestamp = this.generateTimestamp();
    const nonce = this.generateNonce();

    // Build OAuth parameters
    const oauthParams: Record<string, string> = {
      oauth_consumer_key: this.config.clientId,
      oauth_nonce: nonce,
      oauth_signature_method: "HMAC-SHA1",
      oauth_timestamp: timestamp,
      oauth_version: "1.0",
    };

    if (token) {
      oauthParams.oauth_token = token;
    }

    // Combine OAuth and regular parameters for signature
    const allParams = { ...params, ...oauthParams };

    // Generate signature with all parameters
    const signature = this.generateSignature(
      method,
      url,
      allParams,
      this.config.clientSecret,
      tokenSecret,
    );

    // Add signature to the parameters
    allParams.oauth_signature = signature;

    const options: any = {
      method,
      headers: {},
    };

    let requestUrl = url;
    if (method === "GET") {
      requestUrl += "?" + querystring.stringify(allParams);
    } else if (method === "POST") {
      options.headers["Content-Type"] = "application/x-www-form-urlencoded";
      options.body = querystring.stringify(allParams);
    }

    const response = await fetch(requestUrl, options);
    const text = await response.text();

    if (!response.ok) {
      throw new Error(`OAuth error: ${response.status} - ${text}`);
    }

    // Try to parse as JSON, fallback to query string
    try {
      return JSON.parse(text);
    } catch {
      return querystring.parse(text);
    }
  }

  private async makeApiRequest(
    method: string,
    url: string,
    params: Record<string, string> = {},
    useAccessToken: boolean = true,
  ): Promise<any> {
    const timestamp = this.generateTimestamp();
    const nonce = this.generateNonce();

    // Build OAuth parameters
    const oauthParams: Record<string, string> = {
      oauth_consumer_key: this.config.clientId,
      oauth_nonce: nonce,
      oauth_signature_method: "HMAC-SHA1",
      oauth_timestamp: timestamp,
      oauth_version: "1.0",
    };

    if (useAccessToken && this.config.accessToken && this.config.accessTokenSecret) {
      oauthParams.oauth_token = this.config.accessToken;
    }

    // Add format=json for API requests
    params.format = "json";

    // Combine OAuth and regular parameters for signature
    const allParams = { ...params, ...oauthParams };

    // Generate signature with all parameters
    const tokenSecret = useAccessToken ? this.config.accessTokenSecret : undefined;
    const signature = this.generateSignature(
      method,
      url,
      allParams,
      this.config.clientSecret,
      tokenSecret,
    );

    // Add signature to the parameters
    allParams.oauth_signature = signature;

    const options: any = {
      method,
      headers: {},
    };

    let requestUrl = url;
    if (method === "GET") {
      requestUrl += "?" + querystring.stringify(allParams);
    } else if (method === "POST") {
      options.headers["Content-Type"] = "application/x-www-form-urlencoded";
      options.body = querystring.stringify(allParams);
    }

    const response = await fetch(requestUrl, options);
    const text = await response.text();

    if (!response.ok) {
      throw new Error(`FatSecret API error: ${response.status} - ${text}`);
    }

    // Try to parse as JSON, fallback to query string
    try {
      return JSON.parse(text);
    } catch {
      return querystring.parse(text);
    }
  }

  private setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "set_credentials",
            description:
              "Set FatSecret API credentials (Client ID and Client Secret)",
            inputSchema: {
              type: "object",
              properties: {
                clientId: {
                  type: "string",
                  description: "Your FatSecret Client ID",
                },
                clientSecret: {
                  type: "string",
                  description: "Your FatSecret Client Secret",
                },
              },
              required: ["clientId", "clientSecret"],
            },
          },
          {
            name: "start_oauth_flow",
            description:
              "Start the 3-legged OAuth flow to get user authorization",
            inputSchema: {
              type: "object",
              properties: {
                callbackUrl: {
                  type: "string",
                  description: 'OAuth callback URL (use "oob" for out-of-band)',
                  default: "oob",
                },
              },
            },
          },
          {
            name: "complete_oauth_flow",
            description:
              "Complete the OAuth flow with the authorization code/verifier",
            inputSchema: {
              type: "object",
              properties: {
                requestToken: {
                  type: "string",
                  description: "The request token from start_oauth_flow",
                },
                requestTokenSecret: {
                  type: "string",
                  description: "The request token secret from start_oauth_flow",
                },
                verifier: {
                  type: "string",
                  description:
                    "The OAuth verifier from the callback or authorization page",
                },
              },
              required: ["requestToken", "requestTokenSecret", "verifier"],
            },
          },
          {
            name: "search_foods",
            description: "Search for foods in the FatSecret database",
            inputSchema: {
              type: "object",
              properties: {
                searchExpression: {
                  type: "string",
                  description:
                    'Search term for foods (e.g., "chicken breast", "apple")',
                },
                pageNumber: {
                  type: "number",
                  description: "Page number for results (default: 0)",
                  default: 0,
                },
                maxResults: {
                  type: "number",
                  description: "Maximum results per page (default: 20)",
                  default: 20,
                },
              },
              required: ["searchExpression"],
            },
          },
          {
            name: "get_food",
            description: "Get detailed information about a specific food item",
            inputSchema: {
              type: "object",
              properties: {
                foodId: {
                  type: "string",
                  description: "The FatSecret food ID",
                },
              },
              required: ["foodId"],
            },
          },
          {
            name: "search_recipes",
            description: "Search for recipes in the FatSecret database",
            inputSchema: {
              type: "object",
              properties: {
                searchExpression: {
                  type: "string",
                  description: "Search term for recipes",
                },
                pageNumber: {
                  type: "number",
                  description: "Page number for results (default: 0)",
                  default: 0,
                },
                maxResults: {
                  type: "number",
                  description: "Maximum results per page (default: 20)",
                  default: 20,
                },
              },
              required: ["searchExpression"],
            },
          },
          {
            name: "get_recipe",
            description: "Get detailed information about a specific recipe",
            inputSchema: {
              type: "object",
              properties: {
                recipeId: {
                  type: "string",
                  description: "The FatSecret recipe ID",
                },
              },
              required: ["recipeId"],
            },
          },
          {
            name: "get_user_profile",
            description: "Get the authenticated user's profile information",
            inputSchema: {
              type: "object",
              properties: {},
            },
          },
          {
            name: "get_user_food_entries",
            description: "Get user's food diary entries for a specific date",
            inputSchema: {
              type: "object",
              properties: {
                date: {
                  type: "string",
                  description: "Date in YYYY-MM-DD format (default: today)",
                },
              },
            },
          },
          {
            name: "add_food_entry",
            description: "Add a food entry to the user's diary",
            inputSchema: {
              type: "object",
              properties: {
                foodId: {
                  type: "string",
                  description: "The FatSecret food ID",
                },
                servingId: {
                  type: "string",
                  description: "The serving ID for the food",
                },
                quantity: {
                  type: "number",
                  description: "Quantity of the serving",
                },
                mealType: {
                  type: "string",
                  description: "Meal type (breakfast, lunch, dinner, snack)",
                  enum: ["breakfast", "lunch", "dinner", "snack"],
                },
                foodEntryName: {
                  type: "string",
                  description: "Name/description of the food entry (e.g., 'Chicken Breast')",
                },
                date: {
                  type: "string",
                  description: "Date in YYYY-MM-DD format (default: today)",
                },
              },
              required: ["foodId", "servingId", "quantity", "mealType", "foodEntryName"],
            },
          },
          {
            name: "edit_food_entry",
            description: "Edit a food entry in the user's diary (can change meal type, quantity, etc.)",
            inputSchema: {
              type: "object",
              properties: {
                foodEntryId: {
                  type: "string",
                  description: "The food entry ID to edit",
                },
                foodEntryName: {
                  type: "string",
                  description: "New name/description of the food entry (optional)",
                },
                servingId: {
                  type: "string",
                  description: "New serving ID (optional)",
                },
                quantity: {
                  type: "number",
                  description: "New quantity (optional)",
                },
                mealType: {
                  type: "string",
                  description: "New meal type: breakfast, lunch, dinner, or other (optional)",
                  enum: ["breakfast", "lunch", "dinner", "other"],
                },
              },
              required: ["foodEntryId"],
            },
          },
          {
            name: "delete_food_entry",
            description: "Delete a food entry from the user's diary",
            inputSchema: {
              type: "object",
              properties: {
                foodEntryId: {
                  type: "string",
                  description: "The food entry ID to delete",
                },
              },
              required: ["foodEntryId"],
            },
          },
          {
            name: "check_auth_status",
            description: "Check if the user is authenticated with FatSecret",
            inputSchema: {
              type: "object",
              properties: {},
            },
          },
          {
            name: "get_weight_month",
            description: "Get user's weight entries for a specific month",
            inputSchema: {
              type: "object",
              properties: {
                date: {
                  type: "string",
                  description: "Date in YYYY-MM-DD format to specify the month (default: current month)",
                },
              },
            },
          },
        ],
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      await this.loadConfig();

      switch (request.params.name) {
        case "set_credentials":
          return await this.handleSetCredentials(request.params.arguments);
        case "start_oauth_flow":
          return await this.handleStartOAuthFlow(request.params.arguments);
        case "complete_oauth_flow":
          return await this.handleCompleteOAuthFlow(request.params.arguments);
        case "search_foods":
          return await this.handleSearchFoods(request.params.arguments);
        case "get_food":
          return await this.handleGetFood(request.params.arguments);
        case "search_recipes":
          return await this.handleSearchRecipes(request.params.arguments);
        case "get_recipe":
          return await this.handleGetRecipe(request.params.arguments);
        case "get_user_profile":
          return await this.handleGetUserProfile(request.params.arguments);
        case "get_user_food_entries":
          return await this.handleGetUserFoodEntries(request.params.arguments);
        case "add_food_entry":
          return await this.handleAddFoodEntry(request.params.arguments);
        case "edit_food_entry":
          return await this.handleEditFoodEntry(request.params.arguments);
        case "delete_food_entry":
          return await this.handleDeleteFoodEntry(request.params.arguments);
        case "check_auth_status":
          return await this.handleCheckAuthStatus(request.params.arguments);
        case "get_weight_month":
          return await this.handleGetWeightMonth(request.params.arguments);
        default:
          throw new McpError(
            ErrorCode.MethodNotFound,
            `Unknown tool: ${request.params.name}`,
          );
      }
    });
  }

  private async handleSetCredentials(args: any) {
    this.config.clientId = args.clientId;
    this.config.clientSecret = args.clientSecret;
    await this.saveConfig();

    return {
      content: [
        {
          type: "text",
          text:
            "FatSecret API credentials have been set successfully. You can now start the OAuth flow to authenticate users.",
        },
      ],
    };
  }

  private async handleStartOAuthFlow(args: any) {
    if (!this.config.clientId || !this.config.clientSecret) {
      throw new McpError(
        ErrorCode.InvalidRequest,
        "Please set your FatSecret API credentials first using set_credentials",
      );
    }

    const callbackUrl = args.callbackUrl || "oob";

    try {
      const response = await this.makeOAuthRequest(
        "POST",
        this.requestTokenUrl,
        { oauth_callback: callbackUrl },
      );

      const token = response.oauth_token as string;
      const tokenSecret = response.oauth_token_secret as string;
      const authUrl = `${this.authorizeUrl}?oauth_token=${token}`;

      return {
        content: [
          {
            type: "text",
            text:
              `OAuth flow started successfully!\n\nRequest Token: ${token}\nRequest Token Secret: ${tokenSecret}\n\nPlease visit this URL to authorize the application:\n${authUrl}\n\nAfter authorization, you'll receive a verifier code. Use the complete_oauth_flow tool with the request token, request token secret, and verifier to complete the authentication.`,
          },
        ],
      };
    } catch (error) {
      throw new McpError(
        ErrorCode.InternalError,
        `Failed to start OAuth flow: ${
          error instanceof Error ? error.message : "Unknown error"
        }`,
      );
    }
  }

  private async handleCompleteOAuthFlow(args: any) {
    if (!this.config.clientId || !this.config.clientSecret) {
      throw new McpError(
        ErrorCode.InvalidRequest,
        "Please set your FatSecret API credentials first",
      );
    }

    try {
      const response = await this.makeOAuthRequest(
        "GET",
        this.accessTokenUrl,
        { oauth_verifier: args.verifier },
        args.requestToken,
        args.requestTokenSecret,
      );

      const tokenData = response as any;

      this.config.accessToken = tokenData.oauth_token;
      this.config.accessTokenSecret = tokenData.oauth_token_secret;
      this.config.userId = tokenData.user_id;

      await this.saveConfig();

      return {
        content: [
          {
            type: "text",
            text:
              `OAuth flow completed successfully! You are now authenticated with FatSecret.\n\nUser ID: ${this.config.userId}\n\nYou can now use user-specific tools like get_user_profile, get_user_food_entries, and add_food_entry.`,
          },
        ],
      };
    } catch (error) {
      throw new McpError(
        ErrorCode.InternalError,
        `Failed to complete OAuth flow: ${
          error instanceof Error ? error.message : "Unknown error"
        }`,
      );
    }
  }

  private async handleSearchFoods(args: any) {
    if (!this.config.clientId || !this.config.clientSecret) {
      throw new McpError(
        ErrorCode.InvalidRequest,
        "Please set your FatSecret API credentials first",
      );
    }

    try {
      const params = {
        method: "foods.search",
        search_expression: args.searchExpression,
        page_number: args.pageNumber?.toString() || "0",
        max_results: args.maxResults?.toString() || "20",
        format: "json",
      };

      const response = await this.makeApiRequest(
        "GET",
        this.baseUrl,
        params,
        false,
      );

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(response, null, 2),
          },
        ],
      };
    } catch (error) {
      throw new McpError(
        ErrorCode.InternalError,
        `Failed to search foods: ${
          error instanceof Error ? error.message : "Unknown error"
        }`,
      );
    }
  }

  private async handleGetFood(args: any) {
    if (!this.config.clientId || !this.config.clientSecret) {
      throw new McpError(
        ErrorCode.InvalidRequest,
        "Please set your FatSecret API credentials first",
      );
    }

    try {
      const params = {
        method: "food.get",
        food_id: args.foodId,
        format: "json",
      };

      const response = await this.makeApiRequest(
        "GET",
        this.baseUrl,
        params,
        false,
      );

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(response, null, 2),
          },
        ],
      };
    } catch (error) {
      throw new McpError(
        ErrorCode.InternalError,
        `Failed to get food: ${
          error instanceof Error ? error.message : "Unknown error"
        }`,
      );
    }
  }

  private async handleSearchRecipes(args: any) {
    if (!this.config.clientId || !this.config.clientSecret) {
      throw new McpError(
        ErrorCode.InvalidRequest,
        "Please set your FatSecret API credentials first",
      );
    }

    try {
      const params = {
        method: "recipes.search",
        search_expression: args.searchExpression,
        page_number: args.pageNumber?.toString() || "0",
        max_results: args.maxResults?.toString() || "20",
        format: "json",
      };

      const response = await this.makeApiRequest(
        "GET",
        this.baseUrl,
        params,
        false,
      );

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(response, null, 2),
          },
        ],
      };
    } catch (error) {
      throw new McpError(
        ErrorCode.InternalError,
        `Failed to search recipes: ${
          error instanceof Error ? error.message : "Unknown error"
        }`,
      );
    }
  }

  private async handleGetRecipe(args: any) {
    if (!this.config.clientId || !this.config.clientSecret) {
      throw new McpError(
        ErrorCode.InvalidRequest,
        "Please set your FatSecret API credentials first",
      );
    }

    try {
      const params = {
        method: "recipe.get",
        recipe_id: args.recipeId,
        format: "json",
      };

      const response = await this.makeApiRequest(
        "GET",
        this.baseUrl,
        params,
        false,
      );

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(response, null, 2),
          },
        ],
      };
    } catch (error) {
      throw new McpError(
        ErrorCode.InternalError,
        `Failed to get recipe: ${
          error instanceof Error ? error.message : "Unknown error"
        }`,
      );
    }
  }

  private async handleGetUserProfile(args: any) {
    if (!this.config.accessToken || !this.config.accessTokenSecret) {
      throw new McpError(
        ErrorCode.InvalidRequest,
        "User authentication required. Please complete the OAuth flow first.",
      );
    }

    try {
      const params = {
        method: "profile.get",
        format: "json",
      };

      const response = await this.makeApiRequest(
        "GET",
        this.baseUrl,
        params,
        true,
      );

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(response, null, 2),
          },
        ],
      };
    } catch (error) {
      throw new McpError(
        ErrorCode.InternalError,
        `Failed to get user profile: ${
          error instanceof Error ? error.message : "Unknown error"
        }`,
      );
    }
  }

  private async handleGetUserFoodEntries(args: any) {
    if (!this.config.accessToken || !this.config.accessTokenSecret) {
      throw new McpError(
        ErrorCode.InvalidRequest,
        "User authentication required. Please complete the OAuth flow first.",
      );
    }

    try {
      const date = this.dateToFatSecretFormat(args.date);
      const params = {
        method: "food_entries.get",
        date: date,
        format: "json",
      };

      const response = await this.makeApiRequest(
        "GET",
        this.baseUrl,
        params,
        true,
      );

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(response, null, 2),
          },
        ],
      };
    } catch (error) {
      throw new McpError(
        ErrorCode.InternalError,
        `Failed to get food entries: ${
          error instanceof Error ? error.message : "Unknown error"
        }`,
      );
    }
  }

  private async handleAddFoodEntry(args: any) {
    if (!this.config.accessToken || !this.config.accessTokenSecret) {
      throw new McpError(
        ErrorCode.InvalidRequest,
        "User authentication required. Please complete the OAuth flow first.",
      );
    }

    try {
      const date = this.dateToFatSecretFormat(args.date);
      const params = {
        method: "food_entry.create",
        food_id: args.foodId,
        food_entry_name: args.foodEntryName,
        serving_id: args.servingId,
        number_of_units: args.quantity.toString(),
        meal: args.mealType,
        date: date,
        format: "json",
      };

      const response = await this.makeApiRequest(
        "POST",
        this.baseUrl,
        params,
        true,
      );

      return {
        content: [
          {
            type: "text",
            text: `Food entry added successfully!\n\n${
              JSON.stringify(response, null, 2)
            }`,
          },
        ],
      };
    } catch (error) {
      throw new McpError(
        ErrorCode.InternalError,
        `Failed to add food entry: ${
          error instanceof Error ? error.message : "Unknown error"
        }`,
      );
    }
  }

  private async handleEditFoodEntry(args: any) {
    if (!this.config.accessToken || !this.config.accessTokenSecret) {
      throw new McpError(
        ErrorCode.InvalidRequest,
        "User authentication required. Please complete the OAuth flow first.",
      );
    }

    try {
      const params: Record<string, string> = {
        method: "food_entry.edit",
        food_entry_id: args.foodEntryId,
        format: "json",
      };

      // Add optional parameters if provided
      if (args.foodEntryName) {
        params.food_entry_name = args.foodEntryName;
      }
      if (args.servingId) {
        params.serving_id = args.servingId;
      }
      if (args.quantity !== undefined) {
        params.number_of_units = args.quantity.toString();
      }
      if (args.mealType) {
        params.meal = args.mealType;
      }

      const response = await this.makeApiRequest(
        "POST",
        this.baseUrl,
        params,
        true,
      );

      return {
        content: [
          {
            type: "text",
            text: `Food entry edited successfully!\n\n${
              JSON.stringify(response, null, 2)
            }`,
          },
        ],
      };
    } catch (error) {
      throw new McpError(
        ErrorCode.InternalError,
        `Failed to edit food entry: ${
          error instanceof Error ? error.message : "Unknown error"
        }`,
      );
    }
  }

  private async handleDeleteFoodEntry(args: any) {
    if (!this.config.accessToken || !this.config.accessTokenSecret) {
      throw new McpError(
        ErrorCode.InvalidRequest,
        "User authentication required. Please complete the OAuth flow first.",
      );
    }

    try {
      const params = {
        method: "food_entry.delete",
        food_entry_id: args.foodEntryId,
        format: "json",
      };

      const response = await this.makeApiRequest(
        "POST",
        this.baseUrl,
        params,
        true,
      );

      return {
        content: [
          {
            type: "text",
            text: `Food entry deleted successfully!\n\n${
              JSON.stringify(response, null, 2)
            }`,
          },
        ],
      };
    } catch (error) {
      throw new McpError(
        ErrorCode.InternalError,
        `Failed to delete food entry: ${
          error instanceof Error ? error.message : "Unknown error"
        }`,
      );
    }
  }

  private async handleCheckAuthStatus(args: any) {
    const hasCredentials = !!(this.config.clientId && this.config.clientSecret);
    const hasAccessToken =
      !!(this.config.accessToken && this.config.accessTokenSecret);

    let status = "Not configured";
    if (hasCredentials && hasAccessToken) {
      status = "Fully authenticated";
    } else if (hasCredentials) {
      status = "Credentials set, authentication needed";
    }

    return {
      content: [
        {
          type: "text",
          text:
            `Authentication Status: ${status}\n\nCredentials configured: ${hasCredentials}\nUser authenticated: ${hasAccessToken}\nUser ID: ${
              this.config.userId || "N/A"
            }`,
        },
      ],
    };
  }

  private async handleGetWeightMonth(args: any) {
    if (!this.config.accessToken || !this.config.accessTokenSecret) {
      throw new McpError(
        ErrorCode.InvalidRequest,
        "User authentication required. Please complete the OAuth flow first.",
      );
    }

    try {
      const date = this.dateToFatSecretFormat(args.date);
      const params = {
        method: "weights.get_month",
        date: date,
        format: "json",
      };

      const response = await this.makeApiRequest(
        "GET",
        this.baseUrl,
        params,
        true,
      );

      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(response, null, 2),
          },
        ],
      };
    } catch (error) {
      throw new McpError(
        ErrorCode.InternalError,
        `Failed to get weight entries for month: ${
          error instanceof Error ? error.message : "Unknown error"
        }`,
      );
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("FatSecret MCP server running on stdio");
  }
}

const server = new FatSecretMCPServer();
server.run().catch(console.error);
