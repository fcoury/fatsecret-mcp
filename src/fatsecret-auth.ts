import crypto from "crypto";
import fetch, {
  Headers,
  type RequestInit,
  type Response,
} from "node-fetch";
import querystring from "querystring";

export interface FatSecretAccessToken {
  oauth_token: string;
  oauth_token_secret: string;
  user_id?: string;
}

type FetchLike = (url: string, init?: RequestInit) => Promise<Response>;

const REQUEST_TOKEN_URL =
  "https://authentication.fatsecret.com/oauth/request_token";
const AUTHORIZE_URL =
  "https://authentication.fatsecret.com/oauth/authorize.aspx";
const ACCESS_TOKEN_URL =
  "https://authentication.fatsecret.com/oauth/access_token";

function percentEncode(value: string): string {
  return encodeURIComponent(value).replace(
    /[!'()*]/g,
    (character) =>
      `%${character.charCodeAt(0).toString(16).toUpperCase()}`,
  );
}

function decodeHtml(value: string): string {
  return value
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&amp;/gi, "&")
    .replace(/&#(\d+);/g, (_, code: string) =>
      String.fromCodePoint(Number.parseInt(code, 10)))
    .replace(/&#x([\da-f]+);/gi, (_, code: string) =>
      String.fromCodePoint(Number.parseInt(code, 16)));
}

function readAttribute(tag: string, name: string): string | undefined {
  const escapedName = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = tag.match(
    new RegExp(
      `(?:^|\\s)${escapedName}\\s*=\\s*(?:"([^"]*)"|'([^']*)'|([^\\s>]+))`,
      "i",
    ),
  );
  const value = match?.[1] ?? match?.[2] ?? match?.[3];
  return value === undefined ? undefined : decodeHtml(value);
}

export function extractInputValue(
  html: string,
  inputName: string,
): string | undefined {
  for (const match of html.matchAll(/<input\b[^>]*>/gi)) {
    if (readAttribute(match[0], "name") === inputName) {
      return readAttribute(match[0], "value") ?? "";
    }
  }
  return undefined;
}

export function extractVerifierPin(html: string): string | undefined {
  const match = html.match(/<b\b[^>]*>([\s\S]*?)<\/b>/i);
  if (!match) {
    return undefined;
  }
  return decodeHtml(match[1].replace(/<[^>]*>/g, "")).trim() || undefined;
}

function rejectionHint(html: string): string | undefined {
  const normalized = html.toLowerCase();
  return [
    "captcha",
    "rate",
    "too many",
    "blocked",
    "incorrect",
    "invalid",
    "denied",
    "verify",
  ].find((candidate) => normalized.includes(candidate));
}

export class FatSecretPasswordAuthenticator {
  private readonly cookies = new Map<string, string>();

  constructor(
    private readonly clientId: string,
    private readonly clientSecret: string,
    private readonly fetchImpl: FetchLike = fetch,
  ) {}

  private createSignature(
    method: string,
    url: string,
    parameters: Record<string, string>,
    tokenSecret = "",
  ): string {
    const normalizedParameters = Object.keys(parameters)
      .sort()
      .map((key) =>
        `${percentEncode(key)}=${percentEncode(parameters[key])}`)
      .join("&");
    const baseString = [
      method.toUpperCase(),
      percentEncode(url),
      percentEncode(normalizedParameters),
    ].join("&");
    const signingKey =
      `${percentEncode(this.clientSecret)}&${percentEncode(tokenSecret)}`;
    return crypto.createHmac("sha1", signingKey).update(baseString).digest(
      "base64",
    );
  }

  private async oauthRequest(
    method: "GET" | "POST",
    url: string,
    params: Record<string, string> = {},
    token?: string,
    tokenSecret?: string,
  ): Promise<Record<string, string>> {
    const oauthParams: Record<string, string> = {
      oauth_consumer_key: this.clientId,
      oauth_nonce: crypto.randomBytes(16).toString("hex"),
      oauth_signature_method: "HMAC-SHA1",
      oauth_timestamp: Math.floor(Date.now() / 1000).toString(),
      oauth_version: "1.0",
    };
    if (token) {
      oauthParams.oauth_token = token;
    }

    const allParams = { ...params, ...oauthParams };
    allParams.oauth_signature = this.createSignature(
      method,
      url,
      allParams,
      tokenSecret,
    );

    const encoded = querystring.stringify(allParams);
    const response = await this.fetchImpl(
      method === "GET" ? `${url}?${encoded}` : url,
      method === "GET"
        ? { method }
        : {
          method,
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: encoded,
        },
    );
    const body = await response.text();
    if (!response.ok) {
      throw new Error(`FatSecret OAuth endpoint returned HTTP ${response.status}`);
    }

    return Object.fromEntries(
      Object.entries(querystring.parse(body)).map(([key, value]) => [
        key,
        Array.isArray(value) ? value[0] ?? "" : value ?? "",
      ]),
    );
  }

  private rememberCookies(response: Response): void {
    const setCookies = response.headers.raw()["set-cookie"] ?? [];
    for (const setCookie of setCookies) {
      const pair = setCookie.split(";", 1)[0];
      const separator = pair.indexOf("=");
      if (separator > 0) {
        this.cookies.set(pair.slice(0, separator), pair.slice(separator + 1));
      }
    }
  }

  private cookieHeader(): string {
    return [...this.cookies.entries()]
      .map(([name, value]) => `${name}=${value}`)
      .join("; ");
  }

  private async sessionRequest(
    initialUrl: string,
    initialOptions: RequestInit = {},
  ): Promise<Response> {
    let url = initialUrl;
    let method = initialOptions.method ?? "GET";
    let body = initialOptions.body;
    const headers = new Headers(initialOptions.headers);

    for (let redirectCount = 0; redirectCount <= 10; redirectCount += 1) {
      const cookies = this.cookieHeader();
      if (cookies) {
        headers.set("Cookie", cookies);
      }

      const response = await this.fetchImpl(url, {
        ...initialOptions,
        method,
        body,
        headers,
        redirect: "manual",
      });
      this.rememberCookies(response);

      const location = response.headers.get("location");
      if (![301, 302, 303, 307, 308].includes(response.status) || !location) {
        return response;
      }
      if (redirectCount === 10) {
        throw new Error("FatSecret login exceeded the redirect limit");
      }

      url = new URL(location, url).toString();
      if ([301, 302, 303].includes(response.status) && method !== "GET") {
        method = "GET";
        body = undefined;
        headers.delete("Content-Type");
      }
    }

    throw new Error("FatSecret login exceeded the redirect limit");
  }

  async authenticate(
    username: string,
    password: string,
  ): Promise<FatSecretAccessToken> {
    if (!this.clientId || !this.clientSecret) {
      throw new Error("FatSecret client credentials are required");
    }
    if (!username || !password) {
      throw new Error("FatSecret username and password are required");
    }

    const requestToken = await this.oauthRequest(
      "POST",
      REQUEST_TOKEN_URL,
      { oauth_callback: "oob" },
    );
    if (!requestToken.oauth_token || !requestToken.oauth_token_secret) {
      throw new Error("FatSecret request-token response was incomplete");
    }

    const authorizeUrl =
      `${AUTHORIZE_URL}?oauth_token=${encodeURIComponent(requestToken.oauth_token)}`;
    const loginResponse = await this.sessionRequest(authorizeUrl);
    const loginHtml = await loginResponse.text();
    if (!loginResponse.ok) {
      throw new Error(
        `FatSecret login page returned HTTP ${loginResponse.status}`,
      );
    }

    const viewState = extractInputValue(loginHtml, "__VIEWSTATE");
    const viewStateGenerator = extractInputValue(
      loginHtml,
      "__VIEWSTATEGENERATOR",
    );
    if (viewState === undefined || viewStateGenerator === undefined) {
      throw new Error(
        "FatSecret login page is missing ASP.NET state fields; the page may be rate-limited or showing a CAPTCHA",
      );
    }

    const form = new URLSearchParams({
      __VIEWSTATE: viewState,
      __VIEWSTATEGENERATOR: viewStateGenerator,
      Name: username,
      Password: password,
      "Login.x": "0",
      "Login.y": "0",
    });
    const pinResponse = await this.sessionRequest(authorizeUrl, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form.toString(),
    });
    const pinHtml = await pinResponse.text();
    if (pinResponse.status === 429) {
      throw new Error(
        "FatSecret rate-limited the login request (HTTP 429); wait several minutes before retrying",
      );
    }
    if (pinResponse.status >= 500) {
      throw new Error(
        `FatSecret login is unavailable (HTTP ${pinResponse.status})`,
      );
    }
    if (!pinResponse.ok) {
      throw new Error(`FatSecret login returned HTTP ${pinResponse.status}`);
    }

    const verifier = extractVerifierPin(pinHtml);
    if (!verifier) {
      const hint = rejectionHint(pinHtml);
      throw new Error(
        `FatSecret login was rejected or did not return a verifier PIN${
          hint ? ` (response indicated ${hint})` : ""
        }`,
      );
    }

    const accessToken = await this.oauthRequest(
      "GET",
      ACCESS_TOKEN_URL,
      { oauth_verifier: verifier },
      requestToken.oauth_token,
      requestToken.oauth_token_secret,
    );
    if (!accessToken.oauth_token || !accessToken.oauth_token_secret) {
      throw new Error("FatSecret access-token response was incomplete");
    }

    return accessToken as unknown as FatSecretAccessToken;
  }
}
