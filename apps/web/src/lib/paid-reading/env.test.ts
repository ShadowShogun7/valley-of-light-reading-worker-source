import assert from "node:assert/strict";
import test from "node:test";
import {
  getCommerceEnvironment,
  getLaunchEnvironment,
  parsePaidAccessEnvironment,
  resetPaidAccessEnvironmentForTests,
  ServerConfigurationError,
} from "@/lib/paid-reading/env";

const validEnvironment = {
  NODE_ENV: "test",
  VALLEY_ACCESS_SIGNING_SECRET: "test-only-access-signing-secret-with-32-bytes",
  VALLEY_CHECKOUT_TERMS_VERSION: "checkout-v1",
  VALLEY_GENERATION_CONSENT_VERSION: "consent-v1",
  VALLEY_SUPABASE_SERVICE_ROLE_KEY: "test-service-role-key-with-enough-length",
  VALLEY_SUPABASE_URL: "http://127.0.0.1:54321",
  VALEOFLIGHT_APP_BASE_URL: "http://127.0.0.1:3000",
};

test("server environment fails closed when a required secret is absent", () => {
  assert.throws(
    () =>
      parsePaidAccessEnvironment({
        ...validEnvironment,
        VALLEY_ACCESS_SIGNING_SECRET: undefined,
      }),
    (error: unknown) =>
      error instanceof ServerConfigurationError &&
      error.missingOrInvalidKeys.includes("VALLEY_ACCESS_SIGNING_SECRET")
  );
});

test("server environment accepts explicit local test configuration", () => {
  const parsed = parsePaidAccessEnvironment(validEnvironment);
  assert.deepEqual(parsed.VALLEY_ACCEPTED_CHECKOUT_TERMS_VERSIONS, [
    "checkout-v1",
  ]);
  assert.equal(parsed.VALLEY_ACCESS_GRANT_TTL_DAYS, 30);
  assert.equal(parsed.VALLEY_RUNTIME_ENV, "development");
  assert.equal(
    parsed.VALLEY_WOOCOMMERCE_RECONCILIATION_BATCH_SIZE,
    25
  );
  assert.equal(
    parsed.VALLEY_WOOCOMMERCE_RECONCILIATION_MAX_AGE_MINUTES,
    30
  );
  assert.equal(parsed.VALLEY_EMAIL_QUEUE_MAX_AGE_MINUTES, 15);
});

test("terms-version drain allowlist must contain the current version", () => {
  assert.throws(
    () =>
      parsePaidAccessEnvironment({
        ...validEnvironment,
        VALLEY_ACCEPTED_CHECKOUT_TERMS_VERSIONS: "checkout-old",
      }),
    (error: unknown) =>
      error instanceof ServerConfigurationError &&
      error.missingOrInvalidKeys.includes(
        "VALLEY_ACCEPTED_CHECKOUT_TERMS_VERSIONS"
      )
  );
  const parsed = parsePaidAccessEnvironment({
    ...validEnvironment,
    VALLEY_ACCEPTED_CHECKOUT_TERMS_VERSIONS:
      "checkout-v1,checkout-previous",
  });
  assert.deepEqual(parsed.VALLEY_ACCEPTED_CHECKOUT_TERMS_VERSIONS, [
    "checkout-v1",
    "checkout-previous",
  ]);
});

test("commerce requires an exact amount but not legacy Resend credentials", () => {
  const overrides: Record<string, string | undefined> = {
    ...validEnvironment,
    RESEND_API_KEY: undefined,
    RESEND_WEBHOOK_SECRET: undefined,
    VALEOFLIGHT_EMAIL_FROM: undefined,
    VALEOFLIGHT_EMAIL_REPLY_TO: undefined,
    VALEOFLIGHT_SUPPORT_EMAIL: undefined,
    VALEOFLIGHT_WOOCOMMERCE_CONSUMER_KEY: "consumer-key",
    VALEOFLIGHT_WOOCOMMERCE_CONSUMER_SECRET: "consumer-secret",
    VALEOFLIGHT_WOOCOMMERCE_PRODUCT_ID: "13",
    VALEOFLIGHT_WOOCOMMERCE_REST_API_URL: "https://www.example.com/wp-json/wc/v3",
    VALEOFLIGHT_WOOCOMMERCE_WEBHOOK_SECRET: "webhook-secret-with-length",
    VALEOFLIGHT_WORDPRESS_EMAIL_API_URL:
      "https://www.example.com/wp-json/vale-of-light/v1/access-email",
    VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET:
      "test-wordpress-email-secret-with-32-bytes",
    VALEOFLIGHT_WOOCOMMERCE_EXPECTED_AMOUNT_MINOR: undefined,
  };
  const previous = Object.fromEntries(
    Object.keys(overrides).map((key) => [key, process.env[key]])
  );
  try {
    for (const [key, value] of Object.entries(overrides)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    resetPaidAccessEnvironmentForTests();
    assert.throws(
      () => getCommerceEnvironment(),
      (error: unknown) =>
        error instanceof ServerConfigurationError &&
        error.missingOrInvalidKeys.includes(
          "VALEOFLIGHT_WOOCOMMERCE_EXPECTED_AMOUNT_MINOR"
        )
    );
    process.env.VALEOFLIGHT_WOOCOMMERCE_EXPECTED_AMOUNT_MINOR = "1280";
    resetPaidAccessEnvironmentForTests();
    assert.equal(
      getCommerceEnvironment().VALEOFLIGHT_WOOCOMMERCE_PRODUCT_ID,
      13
    );
  } finally {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    resetPaidAccessEnvironmentForTests();
  }
});

test("production launch health requires an approved retention policy version", () => {
  const overrides: Record<string, string | undefined> = {
    ...validEnvironment,
    RESEND_API_KEY: "test-resend-key",
    RESEND_WEBHOOK_SECRET: "test-resend-webhook-secret",
    VALEOFLIGHT_EMAIL_FROM: "光之谷 <reading@example.com>",
    VALEOFLIGHT_EMAIL_REPLY_TO: "support@example.com",
    VALEOFLIGHT_SUPPORT_EMAIL: "support@example.com",
    VALEOFLIGHT_WOOCOMMERCE_CONSUMER_KEY: "consumer-key",
    VALEOFLIGHT_WOOCOMMERCE_CONSUMER_SECRET: "consumer-secret",
    VALEOFLIGHT_WOOCOMMERCE_PRODUCT_ID: "13",
    VALEOFLIGHT_WOOCOMMERCE_REST_API_URL:
      "https://www.example.com/wp-json/wc/v3",
    VALEOFLIGHT_WOOCOMMERCE_WEBHOOK_SECRET: "webhook-secret-with-length",
    VALEOFLIGHT_WORDPRESS_EMAIL_API_URL:
      "https://www.example.com/wp-json/vale-of-light/v1/access-email",
    VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET:
      "test-wordpress-email-secret-with-32-bytes",
    VALEOFLIGHT_WOOCOMMERCE_EXPECTED_AMOUNT_MINOR: "1280",
    VALLEY_RETENTION_POLICY_VERSION: undefined,
    CRON_SECRET: "test-only-cron-secret-with-at-least-32-bytes",
    VALLEY_WORKER_SIGNING_SECRET:
      "test-only-worker-signing-secret-with-32-bytes",
    VALLEY_WORKER_URL: "https://worker.example.com",
    VALLEY_AGPL_SOURCE_URL:
      "https://github.com/example/valley/releases/tag/v1",
    VALLEY_AGPL_SOURCE_SHA256: "a".repeat(64),
  };
  const previous = Object.fromEntries(
    Object.keys(overrides).map((key) => [key, process.env[key]])
  );
  try {
    for (const [key, value] of Object.entries(overrides)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    resetPaidAccessEnvironmentForTests();
    assert.throws(
      () => getLaunchEnvironment(),
      (error: unknown) =>
        error instanceof ServerConfigurationError &&
        error.missingOrInvalidKeys.includes("VALLEY_RETENTION_POLICY_VERSION")
    );
  } finally {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    resetPaidAccessEnvironmentForTests();
  }
});

test("production launch health requires the authenticated reconciliation schedule", () => {
  const overrides: Record<string, string | undefined> = {
    ...validEnvironment,
    CRON_SECRET: undefined,
    RESEND_API_KEY: "test-resend-key",
    RESEND_WEBHOOK_SECRET: "test-resend-webhook-secret",
    VALEOFLIGHT_EMAIL_FROM: "光之谷 <reading@example.com>",
    VALEOFLIGHT_EMAIL_REPLY_TO: "support@example.com",
    VALEOFLIGHT_SUPPORT_EMAIL: "support@example.com",
    VALEOFLIGHT_WOOCOMMERCE_CONSUMER_KEY: "consumer-key",
    VALEOFLIGHT_WOOCOMMERCE_CONSUMER_SECRET: "consumer-secret",
    VALEOFLIGHT_WOOCOMMERCE_PRODUCT_ID: "13",
    VALEOFLIGHT_WOOCOMMERCE_REST_API_URL:
      "https://www.example.com/wp-json/wc/v3",
    VALEOFLIGHT_WOOCOMMERCE_WEBHOOK_SECRET:
      "webhook-secret-with-length",
    VALEOFLIGHT_WOOCOMMERCE_EXPECTED_AMOUNT_MINOR: "1280",
    VALEOFLIGHT_WORDPRESS_EMAIL_API_URL:
      "https://www.example.com/wp-json/vale-of-light/v1/access-email",
    VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET:
      "test-wordpress-email-secret-with-32-bytes",
    VALLEY_RETENTION_POLICY_VERSION: "retention-v1",
    VALLEY_WORKER_SIGNING_SECRET:
      "test-only-worker-signing-secret-with-32-bytes",
    VALLEY_WORKER_URL: "https://worker.example.com",
    VALLEY_AGPL_SOURCE_URL:
      "https://github.com/example/valley/releases/tag/v1",
    VALLEY_AGPL_SOURCE_SHA256: "a".repeat(64),
  };
  const previous = Object.fromEntries(
    Object.keys(overrides).map((key) => [key, process.env[key]])
  );
  try {
    for (const [key, value] of Object.entries(overrides)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    resetPaidAccessEnvironmentForTests();
    assert.throws(
      () => getLaunchEnvironment(),
      (error: unknown) =>
        error instanceof ServerConfigurationError &&
        error.missingOrInvalidKeys.includes("CRON_SECRET")
    );
  } finally {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
    resetPaidAccessEnvironmentForTests();
  }
});

test("access grants must outlive the database recovery safety margin", () => {
  assert.throws(
    () =>
      parsePaidAccessEnvironment({
        ...validEnvironment,
        VALLEY_ACCESS_GRANT_TTL_DAYS: "1",
      }),
    (error: unknown) =>
      error instanceof ServerConfigurationError &&
      error.missingOrInvalidKeys.includes("VALLEY_ACCESS_GRANT_TTL_DAYS")
  );
});

test("worker integration requires a matching public AGPL source release", () => {
  assert.throws(
    () =>
      parsePaidAccessEnvironment({
        ...validEnvironment,
        VALLEY_WORKER_SIGNING_SECRET:
          "test-only-worker-signing-secret-with-32-bytes",
        VALLEY_WORKER_URL: "https://worker.example.com",
      }),
    (error: unknown) =>
      error instanceof ServerConfigurationError &&
      error.missingOrInvalidKeys.includes("VALLEY_AGPL_SOURCE_URL")
  );

  const parsed = parsePaidAccessEnvironment({
    ...validEnvironment,
    VALLEY_AGPL_SOURCE_SHA256: "b".repeat(64),
    VALLEY_AGPL_SOURCE_URL:
      "https://github.com/example/valley/releases/tag/v1",
    VALLEY_WORKER_SIGNING_SECRET:
      "test-only-worker-signing-secret-with-32-bytes",
    VALLEY_WORKER_URL: "https://worker.example.com",
  });
  assert.equal(parsed.VALLEY_AGPL_SOURCE_SHA256, "b".repeat(64));
});

test("WordPress email callback must use a fixed endpoint and a separate secret", () => {
  assert.throws(
    () =>
      parsePaidAccessEnvironment({
        ...validEnvironment,
        VALEOFLIGHT_WORDPRESS_EMAIL_API_URL:
          "https://www.example.com/wp-json/wp/v2/users",
        VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET:
          "test-wordpress-email-secret-with-32-bytes",
      }),
    (error: unknown) =>
      error instanceof ServerConfigurationError &&
      error.missingOrInvalidKeys.includes(
        "VALEOFLIGHT_WORDPRESS_EMAIL_API_URL"
      )
  );
  assert.throws(
    () =>
      parsePaidAccessEnvironment({
        ...validEnvironment,
        VALEOFLIGHT_WORDPRESS_EMAIL_API_URL:
          "https://www.example.com/wp-json/vale-of-light/v1/access-email",
        VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET:
          validEnvironment.VALLEY_ACCESS_SIGNING_SECRET,
      }),
    (error: unknown) =>
      error instanceof ServerConfigurationError &&
      error.missingOrInvalidKeys.includes(
        "VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET"
      )
  );
});
