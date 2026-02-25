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

// Suppress dotenv console output
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

class FatSecretMCPServer {
  private server: Server;
  private config: FatSecretConfig;
  private configPath: string;
  private readonly baseUrl = "https://platform.fatsecret.com/rest/server.api";
  private readonly requestTokenUrl = "https://authentication.fatsecret.com/oauth/request_token";
  private readonly authorizeUrl = "https://authentication.fatsecret.com/oauth/authorize";
  private readonly accessTokenUrl = "https://authentication.fatsecret.com/oauth/access_token";

  // Meta-Tool Registry
  private toolRegistry: Record<string, {
    description: string;
    inputSchema: any;
    handler: (args: any) => Promise<any>;
  }> = {};

  constructor() {
    this.server = new Server(
      {
        name: "fatsecret-mcp-server",
        version: "0.2.0",
      }
    );

    this.configPath = path.join(os.homedir(), ".fatsecret-mcp-config.json");
    this.config = {
      clientId: process.env.CLIENT_ID || "",
      clientSecret: process.env.CLIENT_SECRET || "",
    };

    this.initializeToolRegistry();
    this.setupMetaToolHandlers();
  }

  private initializeToolRegistry() {
    this.toolRegistry = {
      "set_credentials": {
        description: "Configure the API with your FatSecret Client ID and Client Secret. Necessary for any API interaction.",
        inputSchema: {
          type: "object",
          properties: {
            clientId: { type: "string" },
            clientSecret: { type: "string" },
          },
          required: ["clientId", "clientSecret"],
        },
        handler: async (args) => {
          this.config.clientId = args.clientId;
          this.config.clientSecret = args.clientSecret;
          await this.saveConfig();
          return { content: [{ type: "text", text: "Credentials set successfully." }] };
        }
      },
      "start_oauth_flow": {
        description: "Initiate the 3-legged OAuth flow to access user-specific data (diaries, weight, saved meals). Returns the Authorization URL.",
        inputSchema: {
          type: "object",
          properties: {
            callbackUrl: { type: "string", default: "oob" },
          },
        },
        handler: async (args) => this.handleStartOAuthFlow(args)
      },
      "complete_oauth_flow": {
        description: "Finalize the OAuth flow by exchanging the verifier code for a permanent access token.",
        inputSchema: {
          type: "object",
          properties: {
            requestToken: { type: "string" },
            requestTokenSecret: { type: "string" },
            verifier: { type: "string" },
          },
          required: ["requestToken", "requestTokenSecret", "verifier"],
        },
        handler: async (args) => this.handleCompleteOAuthFlow(args)
      },
      "search_foods": {
        description: "Search for food items in the global FatSecret database. Use this to find generic or brand-name foods.",
        inputSchema: {
          type: "object",
          properties: {
            searchExpression: { type: "string" },
            pageNumber: { type: "number", default: 0 },
            maxResults: { type: "number", default: 20 },
          },
          required: ["searchExpression"],
        },
        handler: async (args) => {
          const params = {
            method: "foods.search",
            search_expression: args.searchExpression,
            page_number: args.pageNumber?.toString() || "0",
            max_results: args.maxResults?.toString() || "20",
          };
          const response = await this.makeApiRequest("GET", this.baseUrl, params, false);
          return { content: [{ type: "text", text: JSON.stringify(response, null, 2) }] };
        }
      },
      "get_food": {
        description: "Retrieve detailed nutritional information and available serving portions for a specific food ID.",
        inputSchema: {
          type: "object",
          properties: { foodId: { type: "string" } },
          required: ["foodId"],
        },
        handler: async (args) => {
          const params = { method: "food.get.v4", food_id: args.foodId };
          const response = await this.makeApiRequest("GET", this.baseUrl, params, false);
          return { content: [{ type: "text", text: JSON.stringify(response, null, 2) }] };
        }
      },
      "add_food_entry": {
        description: "Log a food consumption entry into the user's daily diary. Requires foodId, servingId, and meal type.",
        inputSchema: {
          type: "object",
          properties: {
            foodId: { type: "string" },
            foodEntryName: { type: "string", description: "Descriptive name for the diary entry" },
            servingId: { type: "string" },
            numberOfUnits: { type: "number", description: "Quantity of the chosen serving" },
            mealType: {
              type: "string",
              enum: ["breakfast", "lunch", "dinner", "other"],
            },
            date: { type: "string", description: "Target date in YYYY-MM-DD format (default: today)" },
          },
          required: ["foodId", "foodEntryName", "servingId", "numberOfUnits", "mealType"],
        },
        handler: async (args) => {
          const date = this.dateToFatSecretFormat(args.date);
          const params = {
            method: "food_entry.create",
            food_id: args.foodId,
            food_entry_name: args.foodEntryName,
            serving_id: args.servingId,
            number_of_units: args.numberOfUnits.toString(),
            meal: args.mealType,
            date: date,
          };
          const response = await this.makeApiRequest("POST", this.baseUrl, params, true);
          const foodEntryId =
            typeof response?.food_entry_id === "object" && response?.food_entry_id?.value
              ? response.food_entry_id.value
              : response?.food_entry_id ?? null;
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(
                  {
                    status: "ok",
                    action: "add_food_entry",
                    food_entry_id: foodEntryId,
                    api_response: response,
                  },
                  null,
                  2
                ),
              },
            ],
          };
        }
      },
      "delete_food_entry": {
        description: "Remove a specific food log from the user's diary using its entry ID.",
        inputSchema: {
          type: "object",
          properties: {
            foodEntryId: { type: "string", description: "The unique ID of the food entry to delete" }
          },
          required: ["foodEntryId"]
        },
        handler: async (args) => {
          const params = {
            method: "food_entry.delete",
            food_entry_id: args.foodEntryId
          };
          const response = await this.makeApiRequest("POST", this.baseUrl, params, true);
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(
                  {
                    status: "ok",
                    action: "delete_food_entry",
                    food_entry_id: args.foodEntryId,
                    api_response: response,
                  },
                  null,
                  2
                ),
              },
            ],
          };
        }
      },
      "get_user_food_entries": {
        description: "List all food items logged by the user for a specific date.",
        inputSchema: {
          type: "object",
          properties: { date: { type: "string", description: "YYYY-MM-DD" } },
        },
        handler: async (args) => {
          const date = this.dateToFatSecretFormat(args.date);
          const params = { method: "food_entries.get.v2", date };
          const response = await this.makeApiRequest("GET", this.baseUrl, params, true);
          return { content: [{ type: "text", text: JSON.stringify(response, null, 2) }] };
        }
      },
      "get_food_month_summary": {
        description: "Retrieve a daily nutritional summary (calories, macros) for an entire month.",
        inputSchema: {
          type: "object",
          properties: {
            date: { type: "string", description: "Any date within the target month (YYYY-MM-DD)" },
          },
        },
        handler: async (args) => {
          const dateVal = this.dateToFatSecretFormat(args.date);
          const params = { method: "food_entries.get_month.v2", date: dateVal };
          const response = await this.makeApiRequest("GET", this.baseUrl, params, true);
          return { content: [{ type: "text", text: JSON.stringify(response, null, 2) }] };
        }
      },
      "get_weight_month": {
        description: "Get the user's weight log history for a specific month.",
        inputSchema: {
          type: "object",
          properties: { date: { type: "string", description: "YYYY-MM-DD" } },
        },
        handler: async (args) => {
          const dateVal = this.dateToFatSecretFormat(args.date);
          const params = { method: "weights.get_month", date: dateVal };
          const response = await this.makeApiRequest("GET", this.baseUrl, params, true);
          return { content: [{ type: "text", text: JSON.stringify(response, null, 2) }] };
        }
      },
      "get_favorite_foods": {
        description: "List all individual food items marked as favorites by the user.",
        inputSchema: {
          type: "object",
          properties: {},
        },
        handler: async (args) => {
          const params = { method: "foods.get_favorites" };
          const response = await this.makeApiRequest("GET", this.baseUrl, params, true);
          return { content: [{ type: "text", text: JSON.stringify(response, null, 2) }] };
        }
      },
      "get_my_recipes": {
        description: "List recipes created by the user (Cookbook). Note: pending recipes may be hidden here; use get_member_foods instead if missing.",
        inputSchema: {
          type: "object",
          properties: {
            pageNumber: { type: "number", default: 0 },
            maxResults: { type: "number", default: 20 },
          },
        },
        handler: async (args) => {
          const params = {
            method: "recipes.search",
            recipe_types: "Member",
            page_number: args.pageNumber?.toString() || "0",
            max_results: args.maxResults?.toString() || "20",
          };
          const response = await this.makeApiRequest("GET", this.baseUrl, params, true);
          return { content: [{ type: "text", text: JSON.stringify(response, null, 2) }] };
        }
      },
      "search_my_recipes": {
        description: "Directly search for a user-created recipe by name. Bypasses some API listing restrictions.",
        inputSchema: {
          type: "object",
          properties: {
            searchExpression: { type: "string", description: "Recipe name" },
            pageNumber: { type: "number", default: 0 },
            maxResults: { type: "number", default: 20 },
          },
          required: ["searchExpression"]
        },
        handler: async (args) => {
          const params = {
            method: "recipes.search",
            search_expression: args.searchExpression,
            page_number: args.pageNumber?.toString() || "0",
            max_results: args.maxResults?.toString() || "20",
          };
          // 3-legged request
          const response = await this.makeApiRequest("GET", this.baseUrl, params, true);
          return { content: [{ type: "text", text: JSON.stringify(response, null, 2) }] };
        }
      },
      "get_recipe": {
        description: "Get the full manifest of a recipe: ingredients, preparation steps, and detailed nutritional breakdown.",
        inputSchema: {
          type: "object",
          properties: {
            recipeId: { type: "string", description: "The recipe's unique ID" }
          },
          required: ["recipeId"]
        },
        handler: async (args) => {
          const params = {
            method: "recipe.get.v2", 
            recipe_id: args.recipeId,
          };
          const response = await this.makeApiRequest("GET", this.baseUrl, params, true);
          return { content: [{ type: "text", text: JSON.stringify(response, null, 2) }] };
        }
      },
      "get_saved_meals": {
        description: "List all 'Saved Meals' (Combos). These are preferred for custom combinations as they are always visible and editable.",
        inputSchema: {
          type: "object",
          properties: {},
        },
        handler: async (args) => {
          const params = {
            method: "saved_meals.get",
          };
          const response = await this.makeApiRequest("GET", this.baseUrl, params, true);
          return { content: [{ type: "text", text: JSON.stringify(response, null, 2) }] };
        }
      },
      "create_saved_meal": {
        description: "Create a new Saved Meal container. Specify which meal times (Breakfast, etc.) it is suitable for.",
        inputSchema: {
          type: "object",
          properties: {
            name: { type: "string", description: "Name of the combo" },
            description: { type: "string" },
            meals: { type: "string", description: "Comma-separated: Breakfast,Lunch,Dinner,Other" }
          },
          required: ["name"]
        },
        handler: async (args) => {
          const params: Record<string, string> = {
            method: "saved_meal.create",
            saved_meal_name: args.name
          };
          if (args.description) params.saved_meal_description = args.description;
          if (args.meals) params.meals = args.meals;
          const response = await this.makeApiRequest("POST", this.baseUrl, params, true);
          return { content: [{ type: "text", text: `Saved meal created!\n\n${JSON.stringify(response, null, 2)}` }] };
        }
      },
      "edit_saved_meal_name": {
        description: "Update the metadata (name, description, suitability) of an existing Saved Meal.",
        inputSchema: {
          type: "object",
          properties: {
            mealId: { type: "string" },
            name: { type: "string" },
            description: { type: "string" },
            meals: { type: "string", description: "Comma-separated: Breakfast,Lunch,Dinner,Other" }
          },
          required: ["mealId", "name"]
        },
        handler: async (args) => {
          const params: Record<string, string> = {
            method: "saved_meal.edit",
            saved_meal_id: args.mealId,
            saved_meal_name: args.name
          };
          if (args.description) params.saved_meal_description = args.description;
          if (args.meals) params.meals = args.meals;
          const response = await this.makeApiRequest("POST", this.baseUrl, params, true);
          return { content: [{ type: "text", text: `Saved meal edited!\n\n${JSON.stringify(response, null, 2)}` }] };
        }
      },
      "delete_saved_meal": {
        description: "Permanently delete a Saved Meal combo.",
        inputSchema: {
          type: "object",
          properties: {
            mealId: { type: "string" }
          },
          required: ["mealId"]
        },
        handler: async (args) => {
          const params = {
            method: "saved_meal.delete",
            saved_meal_id: args.mealId
          };
          const response = await this.makeApiRequest("POST", this.baseUrl, params, true);
          return { content: [{ type: "text", text: `Saved meal deleted!\n\n${JSON.stringify(response, null, 2)}` }] };
        }
      },
      "add_food_to_meal": {
        description: "Add a food item as a component of a Saved Meal. Requires a descriptive item name.",
        inputSchema: {
          type: "object",
          properties: {
            mealId: { type: "string" },
            foodId: { type: "string" },
            mealItemName: { type: "string", description: "Name for this component within the meal" },
            servingId: { type: "string" },
            numberOfUnits: { type: "number" }
          },
          required: ["mealId", "foodId", "mealItemName", "servingId", "numberOfUnits"]
        },
        handler: async (args) => {
          const params = {
            method: "saved_meal_item.add",
            saved_meal_id: args.mealId,
            food_id: args.foodId,
            saved_meal_item_name: args.mealItemName,
            serving_id: args.servingId,
            number_of_units: args.numberOfUnits.toString()
          };
          const response = await this.makeApiRequest("POST", this.baseUrl, params, true);
          return { content: [{ type: "text", text: `Food added to meal!\n\n${JSON.stringify(response, null, 2)}` }] };
        }
      },
      "edit_food_in_meal": {
        description: "Adjust the portion or serving type of a specific component within a Saved Meal.",
        inputSchema: {
          type: "object",
          properties: {
            mealItemId: { type: "string" },
            servingId: { type: "string" },
            numberOfUnits: { type: "number" }
          },
          required: ["mealItemId", "servingId", "numberOfUnits"]
        },
        handler: async (args) => {
          const params = {
            method: "saved_meal_item.edit",
            saved_meal_item_id: args.mealItemId,
            serving_id: args.servingId,
            number_of_units: args.numberOfUnits.toString()
          };
          const response = await this.makeApiRequest("POST", this.baseUrl, params, true);
          return { content: [{ type: "text", text: `Food in meal edited!\n\n${JSON.stringify(response, null, 2)}` }] };
        }
      },
      "remove_food_from_meal": {
        description: "Remove an individual ingredient from a Saved Meal.",
        inputSchema: {
          type: "object",
          properties: {
            mealItemId: { type: "string" }
          },
          required: ["mealItemId"]
        },
        handler: async (args) => {
          const params = {
            method: "saved_meal_item.delete",
            saved_meal_item_id: args.mealItemId
          };
          const response = await this.makeApiRequest("POST", this.baseUrl, params, true);
          return { content: [{ type: "text", text: `Food removed from meal!\n\n${JSON.stringify(response, null, 2)}` }] };
        }
      },
      "get_meal_details": {
        description: "List all foods and their exact quantities contained within a specific Saved Meal.",
        inputSchema: {
          type: "object",
          properties: {
            mealId: { type: "string" }
          },
          required: ["mealId"]
        },
        handler: async (args) => {
          const params = {
            method: "saved_meal_items.get",
            saved_meal_id: args.mealId
          };
          const response = await this.makeApiRequest("GET", this.baseUrl, params, true);
          return { content: [{ type: "text", text: JSON.stringify(response, null, 2) }] };
        }
      },
      "get_usual_foods": {
        description: "Analyze the user's history to find the most frequently consumed foods.",
        inputSchema: {
          type: "object",
          properties: {
            mealType: { type: "string", description: "Optional filter: breakfast, lunch, dinner, other" }
          },
        },
        handler: async (args) => {
          const params: Record<string, string> = { method: "foods.get_most_eaten" };
          if (args.mealType) params.meal = args.mealType;
          const response = await this.makeApiRequest("GET", this.baseUrl, params, true);
          return { content: [{ type: "text", text: JSON.stringify(response, null, 2) }] };
        }
      },
      "get_recent_foods": {
        description: "Retrieve items the user has logged in the last few days for quick re-logging.",
        inputSchema: {
          type: "object",
          properties: {
            mealType: { type: "string", description: "Optional filter: breakfast, lunch, dinner, other" }
          },
        },
        handler: async (args) => {
          const params: Record<string, string> = { method: "foods.get_recently_eaten" };
          if (args.mealType) params.meal = args.mealType;
          const response = await this.makeApiRequest("GET", this.baseUrl, params, true);
          return { content: [{ type: "text", text: JSON.stringify(response, null, 2) }] };
        }
      },
      "get_member_foods": {
        description: "Search the user's private collection of custom foods and recipes. Essential for finding 'Pending' items.",
        inputSchema: {
          type: "object",
          properties: {
            searchExpression: { type: "string" },
            pageNumber: { type: "number", default: 0 },
            maxResults: { type: "number", default: 20 },
          },
        },
        handler: async (args) => {
          const params: Record<string, string> = {
            method: "foods.search",
            food_type: "Member",
            page_number: args.pageNumber?.toString() || "0",
            max_results: args.maxResults?.toString() || "20",
          };
          if (args.searchExpression) params.search_expression = args.searchExpression;
          const response = await this.makeApiRequest("GET", this.baseUrl, params, true);
          return { content: [{ type: "text", text: JSON.stringify(response, null, 2) }] };
        }
      },
      "get_all_favorites": {
        description: "List all recipes the user has favorited across the platform.",
        inputSchema: {
          type: "object",
          properties: {
            pageNumber: { type: "number", default: 0 },
            maxResults: { type: "number", default: 20 },
          },
        },
        handler: async (args) => {
          const params = {
            method: "recipes.get_favorites.v2",
            page_number: args.pageNumber?.toString() || "0",
            max_results: args.maxResults?.toString() || "20",
          };
          const response = await this.makeApiRequest("GET", this.baseUrl, params, true);
          return { content: [{ type: "text", text: JSON.stringify(response, null, 2) }] };
        }
      },
      "manage_favorite_recipe": {
        description: "Mark a recipe as favorite (star) or remove it from favorites.",
        inputSchema: {
          type: "object",
          properties: {
            recipeId: { type: "string" },
            action: { type: "string", enum: ["add", "delete"] }
          },
          required: ["recipeId", "action"]
        },
        handler: async (args) => {
          const method = args.action === "add" ? "recipe.add_favorite" : "recipe.delete_favorite";
          const params = { method, recipe_id: args.recipeId };
          const response = await this.makeApiRequest("POST", this.baseUrl, params, true);
          return { content: [{ type: "text", text: `Recipe ${args.action}ed successfully!\n\n${JSON.stringify(response, null, 2)}` }] };
        }
      }
    };
  }

  private setupMetaToolHandlers() {
    // ListTools - Only Discovery and Execute
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "discovery",
            description: "Lists all available FatSecret capabilities and their tool names. Use this when you need to know what you can do.",
            inputSchema: { type: "object", properties: {} },
          },
          {
            name: "execute",
            description: "Executes a specific FatSecret tool. Requires the tool name from discovery and the corresponding arguments.",
            inputSchema: {
              type: "object",
              properties: {
                tool: { type: "string", description: "The name of the tool to execute" },
                arguments: { type: "object", description: "Arguments for the tool" },
              },
              required: ["tool", "arguments"],
            },
          },
        ],
      };
    });

    // CallTool - Handles Discovery and Execute
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      await this.loadConfig();

      const { name, arguments: args } = request.params;

      if (name === "discovery") {
        const toolList = Object.entries(this.toolRegistry).map(([id, info]) => ({
          name: id,
          description: info.description,
        }));
        return {
          content: [{ type: "text", text: "Available FatSecret tools:\n" + JSON.stringify(toolList, null, 2) }],
        };
      }

      if (name === "execute") {
        const { tool, arguments: toolArgs } = args as { tool: string; arguments: any };
        const toolInfo = this.toolRegistry[tool];
        if (!toolInfo) {
          throw new McpError(ErrorCode.InvalidParams, `Tool '${tool}' not found in registry.`);
        }
        try {
          return await toolInfo.handler(toolArgs);
        } catch (error) {
          throw new McpError(ErrorCode.InternalError, error instanceof Error ? error.message : "Execution failed");
        }
      }

      throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${name}`);
    });
  }

  // --- Helper Methods (OAuth & API) ---

  private percentEncode(str: string): string {
    return encodeURIComponent(str)
      .replace(/[!'()*]/g, (c) => `%${c.charCodeAt(0).toString(16).toUpperCase()}`);
  }

  private stringifyParams(params: Record<string, string>): string {
    return Object.keys(params)
      .sort()
      .map((key) => `${this.percentEncode(key)}=${this.percentEncode(params[key])}`)
      .join("&");
  }

  private async loadConfig(): Promise<void> {
    try {
      const configData = await fs.readFile(this.configPath, "utf-8");
      this.config = { ...this.config, ...JSON.parse(configData) };
    } catch (error) {}
  }

  private async saveConfig(): Promise<void> {
    await fs.writeFile(this.configPath, JSON.stringify(this.config, null, 2));
  }

  private generateNonce = () => crypto.randomBytes(16).toString("hex");
  private generateTimestamp = () => Math.floor(Date.now() / 1000).toString();

  private dateToFatSecretFormat(dateString?: string): string {
    const date = dateString ? new Date(dateString) : new Date();
    const epochStart = new Date('1970-01-01');
    return Math.floor((date.getTime() - epochStart.getTime()) / (1000 * 60 * 60 * 24)).toString();
  }

  private generateSignature(method: string, url: string, parameters: Record<string, string>, clientSecret: string, tokenSecret: string = ""): string {
    const sortedParamsString = this.stringifyParams(parameters);
    const baseString = [method.toUpperCase(), this.percentEncode(url), this.percentEncode(sortedParamsString)].join("&");
    const signingKey = `${this.percentEncode(clientSecret)}&${this.percentEncode(tokenSecret)}`;
    return crypto.createHmac("sha1", signingKey).update(baseString).digest("base64");
  }

  private async makeApiRequest(method: string, url: string, params: Record<string, string> = {}, useAccessToken: boolean = true): Promise<any> {
    const allParams: Record<string, string> = {
      ...params,
      oauth_consumer_key: this.config.clientId,
      oauth_nonce: this.generateNonce(),
      oauth_signature_method: "HMAC-SHA1",
      oauth_timestamp: this.generateTimestamp(),
      oauth_version: "1.0",
      format: "json",
    };

    if (useAccessToken && this.config.accessToken) {
      allParams.oauth_token = this.config.accessToken;
    }

    const tokenSecret = useAccessToken ? this.config.accessTokenSecret : "";
    allParams.oauth_signature = this.generateSignature(method, url, allParams, this.config.clientSecret, tokenSecret);

    const options: any = { method, headers: {} };
    let requestUrl = url;
    const queryString = this.stringifyParams(allParams);

    if (method === "GET") {
      requestUrl += "?" + queryString;
    } else {
      // Preserve UTF-8 in custom names (e.g. "Rúcula", "Canónigos") when posting form data.
      options.headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8";
      options.headers["Accept-Charset"] = "UTF-8";
      options.body = Buffer.from(queryString, "utf8");
    }

    const response = await fetch(requestUrl, options);
    const text = await response.text();
    if (!response.ok) throw new Error(`FatSecret API error: ${response.status} - ${text}`);
    try { return JSON.parse(text); } catch { return querystring.parse(text); }
  }

  private async handleStartOAuthFlow(args: any) {
    const response = await this.makeApiRequest("POST", this.requestTokenUrl, { oauth_callback: args.callbackUrl || "oob" }, false);
    const token = response.oauth_token as string;
    const secret = response.oauth_token_secret as string;
    return {
      content: [{ type: "text", text: `Auth URL: ${this.authorizeUrl}?oauth_token=${token}\nToken: ${token}\nSecret: ${secret}` }]
    };
  }

  private async handleCompleteOAuthFlow(args: any) {
    const response = await this.makeApiRequest("GET", this.accessTokenUrl, { oauth_verifier: args.verifier }, true); // Uses req token as auth token
    this.config.accessToken = response.oauth_token;
    this.config.accessTokenSecret = response.oauth_token_secret;
    this.config.userId = response.user_id;
    await this.saveConfig();
    return { content: [{ type: "text", text: "OAuth completed successfully!" }] };
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("FatSecret MCP server (Meta-Tool v0.2.0) running on stdio");
  }
}

const server = new FatSecretMCPServer();
server.run().catch(console.error);
