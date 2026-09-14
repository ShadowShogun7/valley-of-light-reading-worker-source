import assert from "node:assert/strict";
import test, { afterEach, beforeEach } from "node:test";
import { NextRequest } from "next/server";
import { POST } from "@/app/api/reading-access/recover/route";
import { resetPaidAccessEnvironmentForTests } from "@/lib/paid-reading/env";
import { resetPaidReadingDatabaseForTests } from "@/lib/paid-reading/supabase";
import { sha256Hex } from "@/lib/paid-reading/crypto";

const appOrigin = "https://reading.example.com";
const testEnvironment = {
  NODE_ENV: "test",
  VALLEY_RUNTIME_ENV: "development",
  VALLEY_ACCESS_SIGNING_SECRET: "test-only-access-signing-secret-with-32-bytes",
  VALLEY_ACCESS_GRANT_TTL_DAYS: "30",
  VALLEY_CHECKOUT_TERMS_VERSION: "checkout-v1",
  VALLEY_DATA_CONFIRMATION_VERSION: "data-confirmation-v1",
  VALLEY_GENERATION_CONSENT_VERSION: "consent-v1",
  VALLEY_SUPABASE_SERVICE_ROLE_KEY: "test-service-role-key-with-enough-length",
  VALLEY_SUPABASE_URL: "https://database.example.com",
  VALEOFLIGHT_APP_BASE_URL: appOrigin,
};
const readingId = "123e4567-e89b-42d3-a456-426614174000";
type RpcCall = { name: string; body: Record<string, unknown> };
let calls: RpcCall[];
let eligible: boolean;
let rateLimited: boolean;
let databaseUnavailable: boolean;
let previousEnvironment: NodeJS.ProcessEnv;
const originalFetch = globalThis.fetch;

beforeEach(() => {
  previousEnvironment = { ...process.env };
  // No real credentials or remote writes are permitted in these route tests.
  for (const key of Object.keys(process.env)) {
    if (/^(VALLEY_|VALEOFLIGHT_|RESEND_|CRON_SECRET$)/.test(key)) {
      delete process.env[key];
    }
  }
  Object.assign(process.env, testEnvironment);
  resetPaidAccessEnvironmentForTests();
  resetPaidReadingDatabaseForTests();
  calls = [];
  eligible = true;
  rateLimited = false;
  databaseUnavailable = false;
  globalThis.fetch = async (input, init) => {
    const url = new URL(input instanceof Request ? input.url : String(input));
    assert.equal(url.origin, testEnvironment.VALLEY_SUPABASE_URL);
    const name = url.pathname.split("/").at(-1)!;
    const body = JSON.parse(String(init?.body)) as Record<string, unknown>;
    calls.push({ name, body });
    if (name === "valley_take_rate_limit") {
      return Response.json(!rateLimited);
    }
    assert.equal(name, "valley_recover_paid_reading");
    if (databaseUnavailable) {
      return Response.json({ message: "DATABASE_UNAVAILABLE" }, { status: 503 });
    }
    // Mirror the SQL precondition, not the application constant under test.
    if (body.p_recovery_template_version !==
      `paid-access-recovery-v1:${body.p_candidate_grant_id}`) {
      return Response.json({
        code: "22023", message: "INVALID_READING_RECOVERY_REQUEST",
      }, { status: 400 });
    }
    return Response.json(eligible ? {
      eligible: true,
      billing_email: body.p_billing_email,
      grant_expires_at: body.p_candidate_grant_expires_at,
      grant_id: body.p_candidate_grant_id,
      order_number: body.p_order_number,
      provider_order_id: "123",
      reading_id: readingId,
      reading_status: "ready",
    } : { eligible: false });
  };
});

afterEach(() => {
  globalThis.fetch = originalFetch;
  for (const key of Object.keys(process.env)) {
    if (!(key in previousEnvironment)) delete process.env[key];
  }
  Object.assign(process.env, previousEnvironment);
  resetPaidAccessEnvironmentForTests();
  resetPaidReadingDatabaseForTests();
});

function request(body: unknown, origin = appOrigin) {
  return new NextRequest(`${appOrigin}/api/reading-access/recover`, {
    body: JSON.stringify(body),
    headers: { "content-type": "application/json", origin },
    method: "POST",
  });
}

const validBody = { billingEmail: "Buyer@example.com", orderNumber: "123" };

test("valid recovery queues the exact database template and returns a private generic response", async () => {
  const response = await POST(request({
    billingEmail: " Buyer@Example.com ", orderNumber: " 123 ",
  }));
  assert.equal(response.status, 202);
  assert.match(response.headers.get("cache-control") ?? "", /private, no-store/);
  assert.deepEqual(calls.map(({ name }) => name), [
    "valley_take_rate_limit", "valley_take_rate_limit", "valley_recover_paid_reading",
  ]);
  const body = calls[2].body;
  assert.equal(body.p_billing_email, "buyer@example.com");
  assert.equal(body.p_order_number, "123");
  assert.equal(body.p_recipient_hash, sha256Hex("buyer@example.com"));
  assert.match(String(body.p_candidate_grant_id), /^[0-9a-f-]{36}$/);
  const expiry = new Date(String(body.p_candidate_grant_expires_at));
  assert.equal(expiry.getUTCMilliseconds(), 0);
  assert.ok(expiry.getTime() > Date.now() + 29 * 86_400_000);
  const text = await response.text();
  assert.equal(JSON.parse(text).accepted, true);
  assert.doesNotMatch(text, /buyer@|123e4567|grant|reading_id|\/r#|eligible/);
});

test("unknown, refunded or suppressed orders are indistinguishable from eligible recovery", async () => {
  const accepted = await POST(request(validBody));
  eligible = false;
  const unavailable = await POST(request(validBody));
  assert.equal(accepted.status, 202);
  assert.equal(unavailable.status, accepted.status);
  assert.equal(await unavailable.text(), await accepted.text());
});

test("invalid form input does not reach recovery or disclose eligibility", async () => {
  for (const body of [
    { ...validBody, billingEmail: "not-an-email" },
    { ...validBody, orderNumber: " " },
    { ...validBody, newBillingEmail: "other@example.com" },
  ]) {
    calls = [];
    const response = await POST(request(body));
    assert.equal(response.status, 202);
    assert.deepEqual(calls.map(({ name }) => name), ["valley_take_rate_limit"]);
  }
});

test("untrusted origin cannot queue recovery", async () => {
  const response = await POST(request(validBody, "https://untrusted.example.com"));
  assert.equal(response.status, 403);
  assert.equal(calls.length, 0);
});

test("rate-limited recovery does not queue an email", async () => {
  rateLimited = true;
  const response = await POST(request(validBody));
  assert.equal(response.status, 429);
  assert.equal(calls.length, 1);
});

test("database failure remains an error, not a false successful resend", async (context) => {
  databaseUnavailable = true;
  const errorLog = context.mock.method(console, "error", () => undefined);
  const response = await POST(request(validBody));
  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), { error: "RECOVERY_TEMPORARILY_UNAVAILABLE" });
  assert.deepEqual(errorLog.mock.calls[0].arguments, [
    "Reading access recovery failed", "DATABASE_OPERATION_FAILED",
  ]);
});
