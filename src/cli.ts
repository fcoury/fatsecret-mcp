#!/usr/bin/env node

/**
 * Standalone FatSecret OAuth Console Utility
 *
 * This script can be run independently to complete the OAuth flow
 * and save credentials to the config file.
 */

import crypto from "crypto";
import fetch from "node-fetch";
import querystring from "querystring";
import fs from "fs/promises";
import path from "path";
import os from "os";
import readline from "readline";
import { exec } from "child_process";
import { promisify } from "util";
import * as dotenv from "dotenv";
import { FatSecretPasswordAuthenticator } from "./fatsecret-auth.js";

// Suppress dotenv console output by temporarily overriding console.log
const originalLog = console.log;
console.log = () => {};
dotenv.config();
console.log = originalLog;

const execAsync = promisify(exec);

interface FatSecretConfig {
  clientId: string;
  clientSecret: string;
  accessToken?: string;
  accessTokenSecret?: string;
  userId?: string;
}

class FatSecretOAuthConsole {
  private config: FatSecretConfig;
  private configPath: string;
  private readonly apiUrl = "https://platform.fatsecret.com/rest/server.api";
  private readonly requestTokenUrl = "https://authentication.fatsecret.com/oauth/request_token";
  private readonly authorizeUrl = "https://authentication.fatsecret.com/oauth/authorize";
  private readonly accessTokenUrl = "https://authentication.fatsecret.com/oauth/access_token";

  constructor() {
    this.configPath = path.join(os.homedir(), ".fatsecret-mcp-config.json");
    this.config = {
      clientId: process.env.FATSECRET_CLIENT_ID || process.env.CLIENT_ID || "",
      clientSecret:
        process.env.FATSECRET_CLIENT_SECRET || process.env.CLIENT_SECRET || "",
    };
  }

  private async loadConfig(): Promise<void> {
    try {
      const configData = await fs.readFile(this.configPath, "utf-8");
      this.config = { ...this.config, ...JSON.parse(configData) };
    } catch (error) {
      // Config file doesn't exist
    }
  }

  private async saveConfig(): Promise<void> {
    await fs.writeFile(this.configPath, JSON.stringify(this.config, null, 2), {
      mode: 0o600,
    });
    await fs.chmod(this.configPath, 0o600);
  }

  private createReadlineInterface(): readline.Interface {
    return readline.createInterface({
      input: process.stdin,
      output: process.stdout,
    });
  }

  private async promptUser(question: string): Promise<string> {
    const rl = this.createReadlineInterface();
    return new Promise((resolve) => {
      rl.question(question, (answer) => {
        rl.close();
        resolve(answer.trim());
      });
    });
  }

  private async openUrlInBrowser(url: string): Promise<boolean> {
    try {
      const platform = process.platform;
      let command: string;

      switch (platform) {
        case "darwin": // macOS
          command = `open "${url}"`;
          break;
        case "win32": // Windows
          command = `start "${url}"`;
          break;
        default: // Linux and others
          command = `xdg-open "${url}"`;
          break;
      }

      await execAsync(command);
      return true;
    } catch (error) {
      return false;
    }
  }

  private generateNonce(): string {
    return crypto.randomBytes(16).toString("hex");
  }

  private generateTimestamp(): string {
    return Math.floor(Date.now() / 1000).toString();
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

    console.log(`Making ${method} request to: ${requestUrl}`);

    const response = await fetch(requestUrl, options);
    const text = await response.text();

    console.log(`Response status: ${response.status}`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${text}`);
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

    // Add format=json for API requests
    params.format = "json";

    // Combine OAuth and regular parameters for signature
    const allParams = { ...params, ...oauthParams };

    // Generate signature with all parameters
    const signature = this.generateSignature(
      method,
      this.apiUrl,
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

    let requestUrl = this.apiUrl;
    if (method === "GET") {
      requestUrl += "?" + querystring.stringify(allParams);
    } else if (method === "POST") {
      options.headers["Content-Type"] = "application/x-www-form-urlencoded";
      options.body = querystring.stringify(allParams);
    }

    const response = await fetch(requestUrl, options);
    const text = await response.text();

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${text}`);
    }

    // Try to parse as JSON, fallback to query string
    try {
      return JSON.parse(text);
    } catch {
      return querystring.parse(text);
    }
  }

  async setupCredentials(): Promise<void> {
    console.log("=== FatSecret API Credentials Setup ===\n");

    if (this.config.clientId && this.config.clientSecret) {
      console.log("Existing credentials found:");
      console.log(`Client ID: ${this.config.clientId}`);
      console.log(
        `Client Secret: ${this.config.clientSecret.substring(0, 8)}...`,
      );

      const useExisting = await this.promptUser(
        "\nUse existing credentials? (y/n): ",
      );
      if (
        useExisting.toLowerCase() === "y" || useExisting.toLowerCase() === "yes"
      ) {
        return;
      }
    }

    console.log("Please enter your FatSecret API credentials.");
    console.log("You can get these from: https://platform.fatsecret.com/\n");

    this.config.clientId = await this.promptUser("Client ID: ");
    this.config.clientSecret = await this.promptUser("Client Secret: ");

    if (!this.config.clientId || !this.config.clientSecret) {
      throw new Error("Client ID and Client Secret are required");
    }

    await this.saveConfig();
    console.log("✓ Credentials saved successfully\n");
  }

  async runOAuthFlow(): Promise<void> {
    console.log("=== Starting OAuth Flow ===\n");

    // Step 1: Get request token
    console.log("Step 1: Getting request token...");

    let requestToken: string;
    let requestTokenSecret: string;

    try {
      const response = await this.makeOAuthRequest(
        "POST",
        this.requestTokenUrl,
        {
          oauth_callback: "oob",
        }, // Regular parameters
        undefined, // No token
        undefined, // No token secret
      );

      console.log("Response from request token endpoint:", response);

      requestToken = response.oauth_token;
      requestTokenSecret = response.oauth_token_secret;

      if (!requestToken || !requestTokenSecret) {
        throw new Error("Invalid response: missing token or token secret");
      }

      console.log("✓ Request token obtained\n");
    } catch (error) {
      console.error("Failed to get request token:", error);
      throw error;
    }

    // Step 2: User authorization
    console.log("Step 2: User authorization");
    const authUrl = `${this.authorizeUrl}?oauth_token=${requestToken}`;

    console.log("Opening authorization URL in your browser...");
    console.log(`URL: ${authUrl}\n`);

    const browserOpened = await this.openUrlInBrowser(authUrl);
    if (!browserOpened) {
      console.log(
        "Could not open browser automatically. Please visit the URL above manually.\n",
      );
    }

    console.log("Instructions:");
    console.log("1. Log in to your FatSecret account (or create one)");
    console.log('2. Click "Allow" to authorize this application');
    console.log("3. Copy the verifier code from the page");
    console.log("4. Paste it below\n");

    const verifier = await this.promptUser("Enter the verifier code: ");

    if (!verifier) {
      throw new Error("Verifier code is required");
    }

    // Step 3: Get access token
    console.log("\nStep 3: Getting access token...");

    try {
      const accessResponse = await this.makeOAuthRequest(
        "GET",
        this.accessTokenUrl,
        {
          oauth_verifier: verifier,
        }, // Regular parameters
        requestToken,
        requestTokenSecret,
      );

      if (!accessResponse.oauth_token || !accessResponse.oauth_token_secret) {
        throw new Error(
          "Invalid response from access token endpoint. Please try again.",
        );
      }

      this.config.accessToken = accessResponse.oauth_token;
      this.config.accessTokenSecret = accessResponse.oauth_token_secret;
      this.config.userId = accessResponse.user_id;

      await this.saveConfig();

      console.log("✓ Access token obtained");
      console.log("✓ OAuth flow completed successfully!\n");
      console.log(`User ID: ${this.config.userId}`);
      console.log("Authentication details saved to:", this.configPath);
    } catch (error) {
      console.error("Failed to get access token:", error);
      throw error;
    }
  }

  async checkStatus(): Promise<void> {
    console.log("=== Authentication Status ===\n");

    const hasCredentials = !!(this.config.clientId && this.config.clientSecret);
    const hasAccessToken =
      !!(this.config.accessToken && this.config.accessTokenSecret);

    console.log(`Credentials configured: ${hasCredentials ? "✓" : "✗"}`);
    console.log(`User authenticated: ${hasAccessToken ? "✓" : "✗"}`);

    if (hasCredentials) {
      console.log(`Client ID: ${this.config.clientId}`);
    }

    if (hasAccessToken) {
      console.log(`User ID: ${this.config.userId || "N/A"}`);
    }

    console.log(`Config file: ${this.configPath}`);
  }

  async run(): Promise<void> {
    try {
      await this.loadConfig();

      if (process.argv.includes("--password-login")) {
        await this.runPasswordLogin();
        return;
      }

      console.log("FatSecret OAuth Console Utility\n");
      console.log(
        "This utility will help you authenticate with the FatSecret API.\n",
      );

      // Setup credentials
      await this.setupCredentials();

      // Run OAuth flow
      const runOAuth = await this.promptUser(
        "Do you want to authenticate a user now? (y/n): ",
      );
      if (runOAuth.toLowerCase() === "y" || runOAuth.toLowerCase() === "yes") {
        await this.runOAuthFlow();
      }

      // Show final status
      console.log();
      await this.checkStatus();

      console.log(
        "\nSetup complete! You can now use the FatSecret MCP server.",
      );
    } catch (error) {
      console.error(
        "Error:",
        error instanceof Error ? error.message : "Unknown error",
      );
      process.exit(1);
    }
  }

  private async runPasswordLogin(): Promise<void> {
    const username = process.env.FATSECRET_USERNAME || "";
    const password = process.env.FATSECRET_PASSWORD || "";
    if (!this.config.clientId || !this.config.clientSecret) {
      throw new Error(
        "Set FATSECRET_CLIENT_ID and FATSECRET_CLIENT_SECRET (or CLIENT_ID and CLIENT_SECRET)",
      );
    }
    if (!username || !password) {
      throw new Error("Set FATSECRET_USERNAME and FATSECRET_PASSWORD");
    }

    console.log("Authenticating with FatSecret using the HTTP session flow...");
    const authenticator = new FatSecretPasswordAuthenticator(
      this.config.clientId,
      this.config.clientSecret,
    );
    const tokenData = await authenticator.authenticate(username, password);
    this.config.accessToken = tokenData.oauth_token;
    this.config.accessTokenSecret = tokenData.oauth_token_secret;
    this.config.userId = tokenData.user_id;
    await this.saveConfig();

    console.log("✓ FatSecret authentication completed");
    console.log(`User ID: ${this.config.userId || "N/A"}`);
    console.log(`Tokens saved to: ${this.configPath}`);
    console.log("The username and password were not stored.");
  }
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  const oauth = new FatSecretOAuthConsole();
  oauth.run();
}

export default FatSecretOAuthConsole;
