import assert from "node:assert/strict";
import test from "node:test";
import {
  buildWooCommerceReconciliationEvent,
  verifyWooCommerceEvent,
  verifyWooCommerceOrder,
  verifyWooCommerceOrderForDelivery,
  WooCommerceVerificationError,
} from "@/lib/paid-reading/woocommerce";

const environment = {
  VALLEY_ACCEPTED_CHECKOUT_TERMS_VERSIONS: ["checkout-v1"],
  VALEOFLIGHT_WOOCOMMERCE_EXPECTED_AMOUNT_MINOR: 1280,
  VALEOFLIGHT_WOOCOMMERCE_EXPECTED_CURRENCY: "TWD",
  VALEOFLIGHT_WOOCOMMERCE_PRODUCT_ID: 789,
} as const;

const paidOrder = {
  billing: { email: "Buyer@Example.com" },
  currency: "TWD",
  date_paid_gmt: "2026-07-26T09:00:00",
  id: 123,
  line_items: [{ product_id: 789, quantity: 1 }],
  meta_data: [
    {
      key: "_vol_checkout_terms_version_presented",
      value: "checkout-v1",
    },
    {
      key: "_vol_checkout_terms_presented_at",
      value: "2026-07-26T08:59:00+00:00",
    },
    {
      key: "_vol_checkout_terms_acceptance_source",
      value: "classic-required-terms-checkbox",
    },
    {
      key: "_vol_reading_product_id",
      value: 789,
    },
    {
      key: "_vol_reading_product_sku",
      value: "vol-astrology-synastry",
    },
    {
      key: "_vol_billing_email_confirmation_digest",
      value: "a".repeat(64),
    },
    {
      key: "_vol_billing_email_confirmed_at",
      value: "2026-07-26T08:58:00+00:00",
    },
    {
      key: "_vol_billing_email_confirmation_acceptance_source",
      value: "classic-checkout-server-validation",
    },
  ],
  number: "123",
  status: "processing",
  total: "1280.00",
  transaction_id: "gateway-reference",
};

const deliverySnapshot = {
  amountMinor: 1280,
  billingEmail: "buyer@example.com",
  billingEmailConfirmationAcceptanceSource:
    "classic-checkout-server-validation" as const,
  billingEmailConfirmationDigest: "a".repeat(64),
  billingEmailConfirmedAt: "2026-07-26T08:58:00.000Z",
  checkoutTermsAcceptanceSource:
    "classic-required-terms-checkbox" as const,
  checkoutTermsPresentedAt: "2026-07-26T08:59:00.000Z",
  checkoutTermsVersionPresented: "checkout-v1",
  currency: "TWD",
  paidAt: "2026-07-26T09:00:00.000Z",
  productId: 789,
};

test("verified Woo order uses server-owned product, paid status, and billing email", () => {
  const verified = verifyWooCommerceOrder(paidOrder, environment);
  assert.equal(verified.amountMinor, 1280);
  assert.equal(verified.billingEmail, "buyer@example.com");
  assert.equal(
    verified.checkoutTermsAcceptanceSource,
    "classic-required-terms-checkbox"
  );
  assert.equal(
    verified.billingEmailConfirmationAcceptanceSource,
    "classic-checkout-server-validation"
  );
  assert.equal(verified.normalizedStatus, "processing");
  assert.equal(verified.productId, 789);
});

test("unpaid or wrong-product Woo orders never create entitlement", () => {
  assert.throws(
    () => verifyWooCommerceOrder({ ...paidOrder, status: "pending" }, environment),
    (error: unknown) =>
      error instanceof WooCommerceVerificationError &&
      error.code === "ORDER_NOT_PAID"
  );
  assert.throws(
    () =>
      verifyWooCommerceOrder(
        { ...paidOrder, line_items: [{ product_id: 999, quantity: 1 }] },
        environment
      ),
    (error: unknown) =>
      error instanceof WooCommerceVerificationError &&
      error.code === "ORDER_PRODUCT_MISMATCH"
  );
});

test("missing or mismatched presented terms metadata fails closed", () => {
  assert.throws(
    () => verifyWooCommerceOrder({ ...paidOrder, meta_data: [] }, environment),
    (error: unknown) =>
      error instanceof WooCommerceVerificationError &&
      error.code === "ORDER_TERMS_PRESENTATION_MISSING"
  );
  assert.throws(
    () =>
      verifyWooCommerceOrder(
        {
          ...paidOrder,
          meta_data: paidOrder.meta_data.map((entry) =>
            entry.key === "_vol_checkout_terms_version_presented"
              ? { ...entry, value: "old-terms" }
              : entry
          ),
        },
        environment
      ),
    (error: unknown) =>
      error instanceof WooCommerceVerificationError &&
      error.code === "ORDER_TERMS_VERSION_MISMATCH"
  );
});

test("checkout evidence must come from a validated acceptance boundary", () => {
  assert.throws(
    () =>
      verifyWooCommerceOrder(
        {
          ...paidOrder,
          meta_data: paidOrder.meta_data.map((entry) =>
            entry.key === "_vol_checkout_terms_acceptance_source"
              ? { ...entry, value: "client-claimed" }
              : entry
          ),
        },
        environment
      ),
    (error: unknown) =>
      error instanceof WooCommerceVerificationError &&
      error.code === "ORDER_TERMS_ACCEPTANCE_SOURCE_INVALID"
  );
});

test("stamped reading product evidence must match the purchased product", () => {
  assert.throws(
    () =>
      verifyWooCommerceOrder(
        {
          ...paidOrder,
          meta_data: paidOrder.meta_data.map((entry) =>
            entry.key === "_vol_reading_product_id"
              ? { ...entry, value: "999" }
              : entry
          ),
        },
        environment
      ),
    (error: unknown) =>
      error instanceof WooCommerceVerificationError &&
      error.code === "ORDER_PRODUCT_MISMATCH"
  );
  assert.throws(
    () =>
      verifyWooCommerceOrder(
        {
          ...paidOrder,
          meta_data: paidOrder.meta_data.map((entry) =>
            entry.key === "_vol_reading_product_sku"
              ? { ...entry, value: "different-product" }
              : entry
          ),
        },
        environment
      ),
    (error: unknown) =>
      error instanceof WooCommerceVerificationError &&
      error.code === "ORDER_PRODUCT_EVIDENCE_MISMATCH"
  );
});

test("a paid order remains valid after the product configured for new sales changes", () => {
  const verified = verifyWooCommerceOrder(paidOrder, {
    ...environment,
    VALEOFLIGHT_WOOCOMMERCE_PRODUCT_ID: 456789,
  });
  assert.equal(verified.productId, 789);
});

test("delivery uses the paid snapshot after current price, currency, and terms policy move on", () => {
  assert.throws(
    () =>
      verifyWooCommerceOrder(paidOrder, {
        ...environment,
        VALLEY_ACCEPTED_CHECKOUT_TERMS_VERSIONS: ["checkout-v2"],
        VALEOFLIGHT_WOOCOMMERCE_EXPECTED_AMOUNT_MINOR: 1680,
        VALEOFLIGHT_WOOCOMMERCE_EXPECTED_CURRENCY: "USD",
        VALEOFLIGHT_WOOCOMMERCE_PRODUCT_ID: 456789,
      }),
    WooCommerceVerificationError
  );

  const verified = verifyWooCommerceOrderForDelivery(
    paidOrder,
    deliverySnapshot
  );
  assert.equal(verified.checkoutTermsVersionPresented, "checkout-v1");
  assert.equal(verified.amountMinor, 1280);
  assert.equal(verified.currency, "TWD");
  assert.equal(verified.productId, 789);
});

test("delivery rejects Woo evidence that no longer matches the stored paid snapshot", () => {
  assert.throws(
    () =>
      verifyWooCommerceOrderForDelivery(
        { ...paidOrder, total: "1680.00" },
        deliverySnapshot
      ),
    WooCommerceVerificationError
  );
  assert.throws(
    () =>
      verifyWooCommerceOrderForDelivery(
        {
          ...paidOrder,
          meta_data: paidOrder.meta_data.map((entry) =>
            entry.key === "_vol_checkout_terms_version_presented"
              ? { ...entry, value: "checkout-v2" }
              : entry
          ),
        },
        deliverySnapshot
      ),
    WooCommerceVerificationError
  );
  assert.throws(
    () =>
      verifyWooCommerceOrderForDelivery(
        { ...paidOrder, status: "refunded" },
        deliverySnapshot
      ),
    (error: unknown) =>
      error instanceof WooCommerceVerificationError
      && error.code === "ORDER_NOT_PAID"
  );
});

test("server-validated billing email confirmation evidence is required", () => {
  assert.throws(
    () =>
      verifyWooCommerceOrder(
        {
          ...paidOrder,
          meta_data: paidOrder.meta_data.filter(
            (entry) =>
              !entry.key.startsWith("_vol_billing_email_confirmation")
          ),
        },
        environment
      ),
    (error: unknown) =>
      error instanceof WooCommerceVerificationError &&
      error.code === "ORDER_BILLING_EMAIL_CONFIRMATION_MISSING"
  );
  assert.throws(
    () =>
      verifyWooCommerceOrder(
        {
          ...paidOrder,
          meta_data: paidOrder.meta_data.map((entry) =>
            entry.key ===
            "_vol_billing_email_confirmation_acceptance_source"
              ? { ...entry, value: "client-only" }
              : entry
          ),
        },
        environment
      ),
    (error: unknown) =>
      error instanceof WooCommerceVerificationError &&
      error.code === "ORDER_BILLING_EMAIL_CONFIRMATION_SOURCE_INVALID"
  );
});

test("billing email confirmation digest and timestamp fail closed", () => {
  assert.throws(
    () =>
      verifyWooCommerceOrder(
        {
          ...paidOrder,
          meta_data: paidOrder.meta_data.map((entry) =>
            entry.key === "_vol_billing_email_confirmation_digest"
              ? { ...entry, value: "not-a-digest" }
              : entry
          ),
        },
        environment
      ),
    (error: unknown) =>
      error instanceof WooCommerceVerificationError &&
      error.code === "ORDER_BILLING_EMAIL_CONFIRMATION_INVALID"
  );
  assert.throws(
    () =>
      verifyWooCommerceOrder(
        {
          ...paidOrder,
          meta_data: paidOrder.meta_data.map((entry) =>
            entry.key === "_vol_billing_email_confirmed_at"
              ? { ...entry, value: "2026-07-26T09:01:00+00:00" }
              : entry
          ),
        },
        environment
      ),
    (error: unknown) =>
      error instanceof WooCommerceVerificationError &&
      error.code === "ORDER_BILLING_EMAIL_CONFIRMATION_TIMESTAMP_INVALID"
  );
});

test("an explicitly retained prior terms version remains valid during payment drain", () => {
  const verified = verifyWooCommerceOrder(
    {
      ...paidOrder,
      meta_data: paidOrder.meta_data.map((entry) =>
        entry.key === "_vol_checkout_terms_version_presented"
          ? { ...entry, value: "checkout-v1" }
          : entry
      ),
    },
    {
      ...environment,
      VALLEY_ACCEPTED_CHECKOUT_TERMS_VERSIONS: [
        "checkout-v2",
        "checkout-v1",
      ],
    }
  );
  assert.equal(verified.checkoutTermsVersionPresented, "checkout-v1");
});

test("refunded, cancelled, and failed orders become revocation events", () => {
  for (const status of ["refunded", "cancelled", "failed"] as const) {
    const verified = verifyWooCommerceEvent(
      {
        ...paidOrder,
        date_modified_gmt: "2026-07-27T09:00:00",
        status,
      },
      environment
    );
    assert.equal(verified.kind, "revoked");
    if (verified.kind === "revoked") {
      assert.equal(verified.order.normalizedStatus, status);
      assert.equal(verified.order.orderId, "123");
    }
  }
});

test("historical refund verification does not depend on current catalog shape", () => {
  const verified = verifyWooCommerceEvent(
    {
      date_modified_gmt: "2026-07-27T09:00:00",
      id: 123,
      status: "refunded",
    },
    {
      ...environment,
      VALEOFLIGHT_WOOCOMMERCE_EXPECTED_AMOUNT_MINOR: 999999,
      VALEOFLIGHT_WOOCOMMERCE_EXPECTED_CURRENCY: "USD",
      VALEOFLIGHT_WOOCOMMERCE_PRODUCT_ID: 456789,
    }
  );
  assert.deepEqual(verified, {
    kind: "revoked",
    order: {
      eventAt: "2026-07-27T09:00:00.000Z",
      matchesExpectedProduct: false,
      normalizedStatus: "refunded",
      orderId: "123",
    },
  });
});

test("unknown target-product refunds can be fenced without trusting price or currency", () => {
  const verified = verifyWooCommerceEvent(
    {
      currency: "USD",
      date_modified_gmt: "2026-07-27T09:00:00",
      id: 123,
      line_items: [{ product_id: 789, quantity: 1 }],
      status: "refunded",
      total: "0.01",
    },
    environment
  );
  assert.equal(verified.kind, "revoked");
  if (verified.kind === "revoked") {
    assert.equal(verified.order.matchesExpectedProduct, true);
  }
});

test("reconciliation event IDs are deterministic across object key order", () => {
  const first = buildWooCommerceReconciliationEvent({
    id: 123,
    nested: { beta: 2, alpha: 1 },
    status: "processing",
  });
  const second = buildWooCommerceReconciliationEvent({
    status: "processing",
    nested: { alpha: 1, beta: 2 },
    id: 123,
  });
  assert.deepEqual(first, second);
  assert.match(first.deliveryId, /^reconciliation:[0-9a-f]{64}$/);
  assert.equal(first.payloadHash, first.deliveryId.split(":")[1]);
});
