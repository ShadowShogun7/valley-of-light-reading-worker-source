import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import test from "node:test";
import {
  buildAccessToken,
  signWordPressEmailBody,
  signWorkerBody,
  verifyAccessToken,
  verifyWooCommerceSignature,
  verifyWorkerSignature,
} from "@/lib/paid-reading/crypto";
import { toWholeSecondIso } from "@/lib/paid-reading/time";

const signingSecret = "test-only-access-signing-secret-with-32-bytes";
const grantId = "82f8cc20-48be-4a31-96a9-16f0d9cff117";
const now = new Date("2026-07-26T08:00:00.000Z");
const expiry = new Date("2026-08-25T08:00:00.000Z");

test("access token is deterministic, verifiable, and contains no stored raw secret", () => {
  const first = buildAccessToken({ expiresAt: expiry, grantId, signingSecret });
  const second = buildAccessToken({ expiresAt: expiry, grantId, signingSecret });
  assert.equal(first, second);
  const verified = verifyAccessToken(first, signingSecret, now);
  assert.equal(verified?.grantId, grantId);
  assert.equal(verified?.expiresAt, expiry.toISOString());
  assert.match(verified?.tokenHash ?? "", /^[0-9a-f]{64}$/);
});

test("access token rejects tampering and expiry", () => {
  const token = buildAccessToken({ expiresAt: expiry, grantId, signingSecret });
  assert.equal(
    verifyAccessToken(`${token.slice(0, -1)}A`, signingSecret, now),
    null
  );
  assert.equal(
    verifyAccessToken(token, signingSecret, new Date("2026-08-25T08:00:01.000Z")),
    null
  );
});

test("database expiry is normalized to the token's whole-second precision", () => {
  const expiryWithMilliseconds = new Date("2026-08-25T08:00:00.217Z");
  const normalizedExpiry = toWholeSecondIso(expiryWithMilliseconds);
  const token = buildAccessToken({
    expiresAt: normalizedExpiry,
    grantId,
    signingSecret,
  });
  assert.equal(
    verifyAccessToken(token, signingSecret, now)?.expiresAt,
    normalizedExpiry
  );
  assert.equal(normalizedExpiry, "2026-08-25T08:00:00.000Z");
});

test("WooCommerce webhook signature uses base64 HMAC over the raw bytes", () => {
  const body = new TextEncoder().encode('{"id":123}');
  const secret = "woocommerce-webhook-secret";
  const signature = createHmac("sha256", secret).update(body).digest("base64");
  assert.equal(verifyWooCommerceSignature(body, signature, secret), true);
  assert.equal(verifyWooCommerceSignature(body, `${signature}x`, secret), false);
});

test("worker signature checks timestamp freshness and raw body", () => {
  const body = new TextEncoder().encode('{"readingId":"x"}');
  const timestamp = String(Math.floor(now.getTime() / 1000));
  const signature = signWorkerBody(body, timestamp, signingSecret);
  assert.equal(
    verifyWorkerSignature({
      now,
      rawBody: body,
      signingSecret,
      suppliedSignature: signature,
      timestamp,
    }),
    true
  );
  assert.equal(
    verifyWorkerSignature({
      now: new Date(now.getTime() + 301_000),
      rawBody: body,
      signingSecret,
      suppliedSignature: signature,
      timestamp,
    }),
    false
  );
});

test("WordPress email callback signature matches the PHP bridge contract", () => {
  const body = '{"version":"woo-access-email-v1"}';
  const timestamp = "1787745600";
  const secret = "notification-secret-abcdefghijklmnopqrstuvwxyz";
  assert.equal(
    signWordPressEmailBody(body, timestamp, secret),
    "1ZaCdOfdkrkap6vKn2KoR7u6six2_eS1odKpmh-iTZU"
  );
});
