import { z } from "zod";
import { sha256Hex } from "@/lib/paid-reading/crypto";
import type { CommerceEnvironment } from "@/lib/paid-reading/env";

const EXPECTED_READING_PRODUCT_SKU = "vol-astrology-synastry";

const wooCommerceOrderIdentitySchema = z
  .object({
    id: z.number().int().positive(),
    status: z.string().min(1),
    date_modified: z.string().nullable().optional(),
    date_modified_gmt: z.string().nullable().optional(),
  })
  .passthrough();

const wooCommercePaidOrderSchema = wooCommerceOrderIdentitySchema.extend({
    number: z.string().min(1),
    currency: z.string().regex(/^[A-Z]{3}$/),
    total: z.string().regex(/^\d+(?:\.\d{1,8})?$/),
    transaction_id: z.string().default(""),
    date_paid: z.string().nullable().optional(),
    date_paid_gmt: z.string().nullable().optional(),
    billing: z.object({
      email: z.string().email(),
    }),
    line_items: z.array(
      z.object({
        product_id: z.number().int().positive(),
        quantity: z.number().int().positive(),
      })
    ),
    meta_data: z
      .array(
        z.object({
          key: z.string(),
          value: z.unknown(),
        })
      )
      .default([]),
});

export type VerifiedWooCommerceOrder = {
  amountMinor: number;
  billingEmail: string;
  billingEmailConfirmationAcceptanceSource:
    | "classic-checkout-server-validation"
    | "store-api-server-validation";
  billingEmailConfirmationDigest: string;
  billingEmailConfirmedAt: string;
  checkoutTermsAcceptanceSource:
    | "classic-required-terms-checkbox"
    | "store-api-validated-checkout";
  checkoutTermsPresentedAt: string;
  checkoutTermsVersionPresented: string;
  currency: string;
  gatewayTransactionId: string;
  normalizedStatus: "processing" | "completed";
  orderId: string;
  orderNumber: string;
  paidAt: string;
  productId: number;
};

export type WooCommerceDeliverySnapshot = {
  amountMinor: number;
  billingEmail: string;
  billingEmailConfirmationAcceptanceSource:
    | "classic-checkout-server-validation"
    | "store-api-server-validation";
  billingEmailConfirmationDigest: string;
  billingEmailConfirmedAt: string;
  checkoutTermsAcceptanceSource:
    | "classic-required-terms-checkbox"
    | "store-api-validated-checkout";
  checkoutTermsPresentedAt: string;
  checkoutTermsVersionPresented: string;
  currency: string;
  paidAt: string;
  productId: number;
};

export type RevokedWooCommerceOrder = {
  eventAt: string;
  matchesExpectedProduct: boolean;
  normalizedStatus: "refunded" | "cancelled" | "failed";
  orderId: string;
};

export type RevalidatedWooCommerceOrder =
  | { kind: "paid"; order: VerifiedWooCommerceOrder }
  | { kind: "revoked"; order: RevokedWooCommerceOrder };

type WooCommerceOrderPolicy = Pick<
  CommerceEnvironment,
  | "VALEOFLIGHT_WOOCOMMERCE_EXPECTED_AMOUNT_MINOR"
  | "VALEOFLIGHT_WOOCOMMERCE_EXPECTED_CURRENCY"
  | "VALEOFLIGHT_WOOCOMMERCE_PRODUCT_ID"
> & {
  readonly VALLEY_ACCEPTED_CHECKOUT_TERMS_VERSIONS: readonly string[];
};

export class WooCommerceVerificationError extends Error {
  readonly code: string;

  constructor(code: string) {
    super(code);
    this.name = "WooCommerceVerificationError";
    this.code = code;
  }
}

export function extractWooCommerceOrderId(payload: unknown) {
  const parsed = z.object({ id: z.number().int().positive() }).passthrough().safeParse(payload);
  if (!parsed.success) throw new WooCommerceVerificationError("INVALID_WOOCOMMERCE_EVENT");
  return parsed.data.id;
}

export async function fetchRevalidatedWooCommerceOrder(
  orderId: number,
  environment: CommerceEnvironment
): Promise<RevalidatedWooCommerceOrder> {
  const body = await fetchWooCommerceOrderBody(orderId, environment);
  const verified = verifyWooCommerceEvent(body, environment);
  if (verified.order.orderId !== String(orderId)) {
    throw new WooCommerceVerificationError("WOOCOMMERCE_ORDER_ID_MISMATCH");
  }
  return verified;
}

export async function fetchWooCommerceOrderForDelivery(
  orderId: number,
  environment: CommerceEnvironment,
  snapshot: WooCommerceDeliverySnapshot
) {
  const body = await fetchWooCommerceOrderBody(orderId, environment);
  const verified = verifyWooCommerceOrderForDelivery(body, snapshot);
  if (verified.orderId !== String(orderId)) {
    throw new WooCommerceVerificationError("WOOCOMMERCE_ORDER_ID_MISMATCH");
  }
  return verified;
}

async function fetchWooCommerceOrderBody(
  orderId: number,
  environment: CommerceEnvironment
) {
  const baseUrl = environment.VALEOFLIGHT_WOOCOMMERCE_REST_API_URL.replace(/\/+$/, "");
  const target = new URL(`${baseUrl}/orders/${orderId}`);
  target.searchParams.set("context", "edit");
  assertSafeWooCommerceTarget(target, environment);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  let response: Response;
  try {
    response = await fetch(target, {
      cache: "no-store",
      headers: wooCommerceAuthorizationHeaders(environment),
      signal: controller.signal,
    });
  } catch {
    throw new WooCommerceVerificationError("WOOCOMMERCE_API_UNAVAILABLE");
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) throw new WooCommerceVerificationError("WOOCOMMERCE_ORDER_RECHECK_FAILED");
  return response.json().catch(() => null);
}

export async function fetchWooCommerceReconciliationPage(
  input: {
    modifiedAfter: string;
    modifiedBefore: string;
    page: number;
    perPage: number;
  },
  environment: CommerceEnvironment
) {
  if (
    !Number.isInteger(input.page) ||
    input.page < 1 ||
    !Number.isInteger(input.perPage) ||
    input.perPage < 1 ||
    input.perPage > 100
  ) {
    throw new WooCommerceVerificationError(
      "INVALID_WOOCOMMERCE_RECONCILIATION_PAGE"
    );
  }

  const baseUrl =
    environment.VALEOFLIGHT_WOOCOMMERCE_REST_API_URL.replace(/\/+$/, "");
  const target = new URL(`${baseUrl}/orders`);
  target.searchParams.set("context", "edit");
  target.searchParams.set("dates_are_gmt", "true");
  target.searchParams.set("modified_after", input.modifiedAfter);
  target.searchParams.set("modified_before", input.modifiedBefore);
  target.searchParams.set("order", "asc");
  target.searchParams.set("orderby", "modified");
  target.searchParams.set("page", String(input.page));
  target.searchParams.set("per_page", String(input.perPage));
  target.searchParams.set("status", "any");
  assertSafeWooCommerceTarget(target, environment);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  let response: Response;
  try {
    response = await fetch(target, {
      cache: "no-store",
      headers: wooCommerceAuthorizationHeaders(environment),
      signal: controller.signal,
    });
  } catch {
    throw new WooCommerceVerificationError("WOOCOMMERCE_API_UNAVAILABLE");
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    if (
      response.status === 400 &&
      z
        .object({ code: z.literal("rest_post_invalid_page_number") })
        .passthrough()
        .safeParse(errorBody).success
    ) {
      return { orders: [] as unknown[], totalPages: input.page - 1 };
    }
    throw new WooCommerceVerificationError(
      "WOOCOMMERCE_RECONCILIATION_FETCH_FAILED"
    );
  }

  const body = await response.json().catch(() => null);
  if (!Array.isArray(body)) {
    throw new WooCommerceVerificationError(
      "INVALID_WOOCOMMERCE_RECONCILIATION_RESPONSE"
    );
  }
  const rawTotalPages = response.headers.get("x-wp-totalpages");
  const totalPages = Number(rawTotalPages);
  if (
    !rawTotalPages ||
    !Number.isSafeInteger(totalPages) ||
    totalPages < 0 ||
    totalPages > 1_000_000
  ) {
    throw new WooCommerceVerificationError(
      "INVALID_WOOCOMMERCE_RECONCILIATION_RESPONSE"
    );
  }
  return { orders: body as unknown[], totalPages };
}

export function verifyWooCommerceEvent(
  value: unknown,
  environment: WooCommerceOrderPolicy
): RevalidatedWooCommerceOrder {
  const identity = wooCommerceOrderIdentitySchema.safeParse(value);
  if (!identity.success) {
    throw new WooCommerceVerificationError("INVALID_WOOCOMMERCE_ORDER");
  }
  const order = identity.data;
  if (
    order.status === "refunded" ||
    order.status === "cancelled" ||
    order.status === "failed"
  ) {
    const eventAtRaw = order.date_modified_gmt ?? order.date_modified;
    if (!eventAtRaw) {
      throw new WooCommerceVerificationError(
        "ORDER_HAS_NO_EVENT_TIMESTAMP"
      );
    }
    const eventAt = parseWooCommerceDate(eventAtRaw);
    if (!Number.isFinite(eventAt.getTime())) {
      throw new WooCommerceVerificationError("ORDER_HAS_INVALID_EVENT_TIMESTAMP");
    }
    return {
      kind: "revoked",
      order: {
        eventAt: eventAt.toISOString(),
        matchesExpectedProduct: refundedOrderMatchesExpectedProduct(
          value,
          environment.VALEOFLIGHT_WOOCOMMERCE_PRODUCT_ID
        ),
        normalizedStatus: order.status,
        orderId: String(order.id),
      },
    };
  }
  return { kind: "paid", order: verifyWooCommerceOrder(order, environment) };
}

export function verifyWooCommerceOrder(
  value: unknown,
  environment: WooCommerceOrderPolicy
): VerifiedWooCommerceOrder {
  return verifyWooCommerceOrderAgainstPolicy(value, {
    acceptedTermsVersions:
      environment.VALLEY_ACCEPTED_CHECKOUT_TERMS_VERSIONS,
    expectedAmountMinor:
      environment.VALEOFLIGHT_WOOCOMMERCE_EXPECTED_AMOUNT_MINOR,
    expectedCurrency:
      environment.VALEOFLIGHT_WOOCOMMERCE_EXPECTED_CURRENCY,
    fallbackProductId:
      environment.VALEOFLIGHT_WOOCOMMERCE_PRODUCT_ID,
  });
}

export function verifyWooCommerceOrderForDelivery(
  value: unknown,
  snapshot: WooCommerceDeliverySnapshot
): VerifiedWooCommerceOrder {
  const verified = verifyWooCommerceOrderAgainstPolicy(value, {
    acceptedTermsVersions: [
      snapshot.checkoutTermsVersionPresented,
    ],
    expectedAmountMinor: snapshot.amountMinor,
    expectedCurrency: snapshot.currency,
    fallbackProductId: snapshot.productId,
  });
  if (
    verified.amountMinor !== snapshot.amountMinor
    || verified.billingEmail
      !== snapshot.billingEmail.trim().toLowerCase()
    || verified.billingEmailConfirmationAcceptanceSource
      !== snapshot.billingEmailConfirmationAcceptanceSource
    || verified.billingEmailConfirmationDigest
      !== snapshot.billingEmailConfirmationDigest
    || !timestampsEqual(
      verified.billingEmailConfirmedAt,
      snapshot.billingEmailConfirmedAt
    )
    || verified.checkoutTermsAcceptanceSource
      !== snapshot.checkoutTermsAcceptanceSource
    || !timestampsEqual(
      verified.checkoutTermsPresentedAt,
      snapshot.checkoutTermsPresentedAt
    )
    || verified.checkoutTermsVersionPresented
      !== snapshot.checkoutTermsVersionPresented
    || verified.currency !== snapshot.currency
    || !timestampsEqual(verified.paidAt, snapshot.paidAt)
    || verified.productId !== snapshot.productId
  ) {
    throw new WooCommerceVerificationError(
      "ORDER_DELIVERY_SNAPSHOT_MISMATCH"
    );
  }

  return verified;
}

function verifyWooCommerceOrderAgainstPolicy(
  value: unknown,
  policy: {
    readonly acceptedTermsVersions: readonly string[];
    expectedAmountMinor: number;
    expectedCurrency: string;
    fallbackProductId: number;
  }
): VerifiedWooCommerceOrder {
  const parsed = wooCommercePaidOrderSchema.safeParse(value);
  if (!parsed.success) throw new WooCommerceVerificationError("INVALID_WOOCOMMERCE_ORDER");
  const order = parsed.data;
  if (order.status !== "processing" && order.status !== "completed") {
    throw new WooCommerceVerificationError("ORDER_NOT_PAID");
  }

  const paidAtRaw = order.date_paid_gmt ?? order.date_paid;
  if (!paidAtRaw) throw new WooCommerceVerificationError("ORDER_HAS_NO_PAID_TIMESTAMP");
  const paidAt = parseWooCommerceDate(paidAtRaw);
  if (!Number.isFinite(paidAt.getTime())) {
    throw new WooCommerceVerificationError("ORDER_HAS_INVALID_PAID_TIMESTAMP");
  }

  const checkoutTermsVersionPresented = stringMetadata(
    order.meta_data,
    "_vol_checkout_terms_version_presented"
  );
  const checkoutTermsPresentedAt = stringMetadata(
    order.meta_data,
    "_vol_checkout_terms_presented_at"
  );
  const checkoutTermsAcceptanceSource = stringMetadata(
    order.meta_data,
    "_vol_checkout_terms_acceptance_source"
  );
  const stampedProductId = integerMetadata(
    order.meta_data,
    "_vol_reading_product_id"
  );
  const stampedProductSku = stringMetadata(
    order.meta_data,
    "_vol_reading_product_sku"
  );
  const { amountMinor, productId } = verifyOrderShape(
    order,
    policy,
    stampedProductId
      ?? policy.fallbackProductId
  );
  if (
    !checkoutTermsVersionPresented ||
    !checkoutTermsPresentedAt ||
    !checkoutTermsAcceptanceSource ||
    stampedProductId === undefined ||
    !stampedProductSku
  ) {
    throw new WooCommerceVerificationError("ORDER_TERMS_PRESENTATION_MISSING");
  }
  if (
    checkoutTermsAcceptanceSource !== "classic-required-terms-checkbox" &&
    checkoutTermsAcceptanceSource !== "store-api-validated-checkout"
  ) {
    throw new WooCommerceVerificationError(
      "ORDER_TERMS_ACCEPTANCE_SOURCE_INVALID"
    );
  }
  if (
    stampedProductId !== productId ||
    stampedProductSku !== EXPECTED_READING_PRODUCT_SKU
  ) {
    throw new WooCommerceVerificationError("ORDER_PRODUCT_EVIDENCE_MISMATCH");
  }
  const billingEmailConfirmationDigest = stringMetadata(
    order.meta_data,
    "_vol_billing_email_confirmation_digest"
  );
  const billingEmailConfirmedAt = stringMetadata(
    order.meta_data,
    "_vol_billing_email_confirmed_at"
  );
  const billingEmailConfirmationAcceptanceSource = stringMetadata(
    order.meta_data,
    "_vol_billing_email_confirmation_acceptance_source"
  );
  if (
    !billingEmailConfirmationDigest ||
    !billingEmailConfirmedAt ||
    !billingEmailConfirmationAcceptanceSource
  ) {
    throw new WooCommerceVerificationError(
      "ORDER_BILLING_EMAIL_CONFIRMATION_MISSING"
    );
  }
  if (!/^[0-9a-f]{64}$/.test(billingEmailConfirmationDigest)) {
    throw new WooCommerceVerificationError(
      "ORDER_BILLING_EMAIL_CONFIRMATION_INVALID"
    );
  }
  if (
    billingEmailConfirmationAcceptanceSource !==
      "classic-checkout-server-validation" &&
    billingEmailConfirmationAcceptanceSource !==
      "store-api-server-validation"
  ) {
    throw new WooCommerceVerificationError(
      "ORDER_BILLING_EMAIL_CONFIRMATION_SOURCE_INVALID"
    );
  }
  const billingEmailConfirmedAtDate = new Date(billingEmailConfirmedAt);
  if (
    !Number.isFinite(billingEmailConfirmedAtDate.getTime()) ||
    billingEmailConfirmedAtDate.getTime() > paidAt.getTime()
  ) {
    throw new WooCommerceVerificationError(
      "ORDER_BILLING_EMAIL_CONFIRMATION_TIMESTAMP_INVALID"
    );
  }
  if (
    !policy.acceptedTermsVersions.includes(
      checkoutTermsVersionPresented
    )
  ) {
    throw new WooCommerceVerificationError("ORDER_TERMS_VERSION_MISMATCH");
  }
  const checkoutTermsPresentedAtDate = new Date(checkoutTermsPresentedAt);
  if (
    !Number.isFinite(checkoutTermsPresentedAtDate.getTime()) ||
    checkoutTermsPresentedAtDate.getTime() > paidAt.getTime()
  ) {
    throw new WooCommerceVerificationError("ORDER_TERMS_TIMESTAMP_INVALID");
  }

  return {
    amountMinor,
    billingEmail: order.billing.email.trim().toLowerCase(),
    billingEmailConfirmationAcceptanceSource,
    billingEmailConfirmationDigest,
    billingEmailConfirmedAt: billingEmailConfirmedAtDate.toISOString(),
    checkoutTermsAcceptanceSource,
    checkoutTermsPresentedAt: checkoutTermsPresentedAtDate.toISOString(),
    checkoutTermsVersionPresented,
    currency: order.currency,
    gatewayTransactionId: order.transaction_id,
    normalizedStatus: order.status,
    orderId: String(order.id),
    orderNumber: order.number,
    paidAt: paidAt.toISOString(),
    productId,
  };
}

function verifyOrderShape(
  order: z.infer<typeof wooCommercePaidOrderSchema>,
  policy: {
    expectedAmountMinor: number;
    expectedCurrency: string;
  },
  productId: number
) {
  const matchingLine = order.line_items.find(
    (lineItem) => lineItem.product_id === productId && lineItem.quantity === 1
  );
  if (!matchingLine) {
    throw new WooCommerceVerificationError("ORDER_PRODUCT_MISMATCH");
  }
  if (order.line_items.length !== 1) {
    throw new WooCommerceVerificationError(
      "ORDER_CONTAINS_UNEXPECTED_PRODUCTS"
    );
  }
  if (order.currency !== policy.expectedCurrency) {
    throw new WooCommerceVerificationError("ORDER_CURRENCY_MISMATCH");
  }

  const amountMinor = decimalAmountToMinor(order.total, order.currency);
  if (amountMinor !== policy.expectedAmountMinor) {
    throw new WooCommerceVerificationError("ORDER_AMOUNT_MISMATCH");
  }
  return { amountMinor, productId };
}

export function buildWooCommerceReconciliationEvent(value: unknown) {
  const identity = wooCommerceOrderIdentitySchema.safeParse(value);
  if (!identity.success) {
    throw new WooCommerceVerificationError("INVALID_WOOCOMMERCE_ORDER");
  }
  const canonicalPayload = canonicalJson(value);
  const payloadHash = sha256Hex(canonicalPayload);
  return {
    deliveryId: `reconciliation:${payloadHash}`,
    orderId: String(identity.data.id),
    payloadHash,
    topic: "order.reconciled",
  };
}

function canonicalJson(value: unknown): string {
  return JSON.stringify(canonicalize(value));
}

function canonicalize(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, nested]) => [key, canonicalize(nested)])
    );
  }
  return value;
}

function assertSafeWooCommerceTarget(
  target: URL,
  environment: Pick<CommerceEnvironment, "NODE_ENV">
) {
  if (
    environment.NODE_ENV === "production" &&
    (target.protocol !== "https:" || target.username || target.password)
  ) {
    throw new WooCommerceVerificationError("INVALID_WOOCOMMERCE_API_URL");
  }
}

function wooCommerceAuthorizationHeaders(environment: CommerceEnvironment) {
  return {
    Accept: "application/json",
    Authorization: `Basic ${Buffer.from(
      `${environment.VALEOFLIGHT_WOOCOMMERCE_CONSUMER_KEY}:${environment.VALEOFLIGHT_WOOCOMMERCE_CONSUMER_SECRET}`
    ).toString("base64")}`,
  };
}

function decimalAmountToMinor(value: string, currency: string) {
  const exponent = new Set(["TWD", "JPY", "KRW"]).has(currency) ? 0 : 2;
  const [integerPart, fractionalPart = ""] = value.split(".");
  if (/[1-9]/.test(fractionalPart.slice(exponent))) {
    throw new WooCommerceVerificationError("ORDER_AMOUNT_INVALID");
  }
  const paddedFraction = `${fractionalPart}${"0".repeat(exponent)}`.slice(0, exponent);
  const amount = Number(integerPart) * 10 ** exponent + Number(paddedFraction || "0");
  if (!Number.isSafeInteger(amount)) {
    throw new WooCommerceVerificationError("ORDER_AMOUNT_INVALID");
  }
  return amount;
}

function stringMetadata(
  metadata: Array<{ key: string; value: unknown }>,
  key: string
) {
  const value = metadata.find((entry) => entry.key === key)?.value;
  return typeof value === "string" && value.trim() ? value.trim() : undefined;
}

function integerMetadata(
  metadata: Array<{ key: string; value: unknown }>,
  key: string
) {
  const value = metadata.find((entry) => entry.key === key)?.value;
  const parsed =
    typeof value === "number"
      ? value
      : typeof value === "string" && /^\d+$/.test(value.trim())
        ? Number(value.trim())
        : Number.NaN;
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : undefined;
}

function parseWooCommerceDate(value: string) {
  const explicitTimezone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(value);
  return new Date(explicitTimezone ? value : `${value}Z`);
}

function timestampsEqual(left: string, right: string) {
  const leftTime = new Date(left).getTime();
  const rightTime = new Date(right).getTime();

  return Number.isFinite(leftTime)
    && Number.isFinite(rightTime)
    && leftTime === rightTime;
}

function refundedOrderMatchesExpectedProduct(
  value: unknown,
  expectedProductId: number
) {
  const parsed = z
    .object({
      line_items: z.array(
        z
          .object({
            product_id: z.number().int().positive(),
            quantity: z.number().int().positive(),
          })
          .passthrough()
      ),
      meta_data: z
        .array(
          z.object({
            key: z.string(),
            value: z.unknown(),
          })
        )
        .default([]),
    })
    .passthrough()
    .safeParse(value);
  if (!parsed.success) return false;
  const stampedProductId = integerMetadata(
    parsed.data.meta_data,
    "_vol_reading_product_id"
  );
  const stampedProductSku = stringMetadata(
    parsed.data.meta_data,
    "_vol_reading_product_sku"
  );
  const productId =
    stampedProductId !== undefined
    && stampedProductSku === EXPECTED_READING_PRODUCT_SKU
      ? stampedProductId
      : expectedProductId;

  return (
    parsed.data.line_items.some(
      (lineItem) => lineItem.product_id === productId
    )
  );
}
