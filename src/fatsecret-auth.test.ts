import assert from "node:assert/strict";
import test from "node:test";
import { Response } from "node-fetch";
import {
  extractInputValue,
  extractVerifierPin,
  FatSecretPasswordAuthenticator,
} from "./fatsecret-auth.js";

test("extracts ASP.NET fields regardless of attribute order", () => {
  const html = `
    <input value="vs&amp;token" type="hidden" name="__VIEWSTATE">
    <input name='__VIEWSTATEGENERATOR' value='vsg-token'>
  `;
  assert.equal(extractInputValue(html, "__VIEWSTATE"), "vs&token");
  assert.equal(
    extractInputValue(html, "__VIEWSTATEGENERATOR"),
    "vsg-token",
  );
});

test("extracts the verifier PIN", () => {
  assert.equal(
    extractVerifierPin("<html><body><b> 1234567 </b></body></html>"),
    "1234567",
  );
});

test("completes request-token, session login, and token exchange", async () => {
  const calls: Array<{ url: string; method: string; body?: string }> = [];
  const responses = [
    new Response(
      "oauth_token=request-token&oauth_token_secret=request-secret&oauth_callback_confirmed=true",
    ),
    new Response(
      '<input name="__VIEWSTATE" value="vs"><input name="__VIEWSTATEGENERATOR" value="vsg">',
      { headers: { "set-cookie": "sid=abc; Path=/; HttpOnly" } },
    ),
    new Response("<html><b>7654321</b></html>"),
    new Response(
      "oauth_token=access-token&oauth_token_secret=access-secret&user_id=user-1",
    ),
  ];
  const fakeFetch = async (url: string, init: any = {}) => {
    calls.push({
      url,
      method: init.method ?? "GET",
      body: typeof init.body === "string" ? init.body : undefined,
    });
    const response = responses.shift();
    assert.ok(response, "unexpected fetch call");
    return response;
  };

  const authenticator = new FatSecretPasswordAuthenticator(
    "client-id",
    "client-secret",
    fakeFetch,
  );
  const token = await authenticator.authenticate("user", "password");

  assert.deepEqual(token, {
    oauth_token: "access-token",
    oauth_token_secret: "access-secret",
    user_id: "user-1",
  });
  assert.equal(calls.length, 4);
  assert.match(calls[1].url, /authorize\.aspx\?oauth_token=request-token$/);
  assert.match(calls[2].body ?? "", /Name=user/);
  assert.match(calls[2].body ?? "", /Password=password/);
  assert.match(calls[3].url, /oauth_verifier=7654321/);
});

test("reports rate limiting distinctly", async () => {
  const responses = [
    new Response("oauth_token=rt&oauth_token_secret=rs"),
    new Response(
      '<input name="__VIEWSTATE" value="vs"><input name="__VIEWSTATEGENERATOR" value="vsg">',
    ),
    new Response("", { status: 429 }),
  ];
  const authenticator = new FatSecretPasswordAuthenticator(
    "client-id",
    "client-secret",
    async () => responses.shift()!,
  );

  await assert.rejects(
    authenticator.authenticate("user", "password"),
    /rate-limited.*HTTP 429/i,
  );
});
