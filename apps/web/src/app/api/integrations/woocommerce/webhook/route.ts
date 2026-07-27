import {
  sha256Hex,
  verifyWooCommerceSignature,
} from "@/lib/paid-reading/crypto";
import {
  getCommerceEnvironment,
  ServerConfigurationError,
} from "@/lib/paid-reading/env";
import {
  parseJsonBody,
  privateJson,
  readRawBody,
  requestFingerprint,
  RequestBodyTooLargeError,
  safeErrorCode,
} from "@/lib/paid-reading/http";
import {
  PaidReadingDatabaseError,
  recordWooCommerceEvent,
  takeRateLimit,
} from "@/lib/paid-reading/repository";
import {
  extractWooCommerceOrderId,
  fetchRevalidatedWooCommerceOrder,
  WooCommerceVerificationError,
} from "@/lib/paid-reading/woocommerce";
import { applyRevalidatedWooCommerceOrder } from "@/lib/paid-reading/woocommerce-sync";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const ignoredOrderCodes = new Set([
  "ORDER_NOT_PAID",
  "ORDER_HAS_NO_PAID_TIMESTAMP",
  "ORDER_PRODUCT_MISMATCH",
]);
const orderReviewCodes = new Set([
  "ORDER_CONTAINS_UNEXPECTED_PRODUCTS",
  "ORDER_CURRENCY_MISMATCH",
  "ORDER_AMOUNT_MISMATCH",
  "ORDER_TERMS_PRESENTATION_MISSING",
  "ORDER_TERMS_VERSION_MISMATCH",
  "ORDER_TERMS_TIMESTAMP_INVALID",
  "ORDER_TERMS_ACCEPTANCE_SOURCE_INVALID",
  "ORDER_PRODUCT_EVIDENCE_MISMATCH",
  "ORDER_BILLING_EMAIL_CONFIRMATION_MISSING",
  "ORDER_BILLING_EMAIL_CONFIRMATION_INVALID",
  "ORDER_BILLING_EMAIL_CONFIRMATION_SOURCE_INVALID",
  "ORDER_BILLING_EMAIL_CONFIRMATION_TIMESTAMP_INVALID",
]);
const acceptedTopics = new Set(["order.created", "order.updated"]);

export async function POST(request: Request) {
  try {
    const environment = getCommerceEnvironment();
    await takeRateLimit({
      keyHash: requestFingerprint(request, environment.VALLEY_ACCESS_SIGNING_SECRET),
      maxRequests: 180,
      scope: "woocommerce-webhook",
      windowSeconds: 60,
    });

    const rawBody = await readRawBody(request, 1024 * 1024);
    const suppliedSignature = request.headers.get("x-wc-webhook-signature");
    if (
      !verifyWooCommerceSignature(
        rawBody,
        suppliedSignature,
        environment.VALEOFLIGHT_WOOCOMMERCE_WEBHOOK_SECRET
      )
    ) {
      return privateJson(
        { error: "INVALID_WEBHOOK_SIGNATURE" },
        { status: 401 }
      );
    }

    const deliveryId = safeHeader(
      request.headers.get("x-wc-webhook-delivery-id"),
      128
    );
    const topic = safeHeader(request.headers.get("x-wc-webhook-topic"), 80);
    if (!deliveryId || !topic || !acceptedTopics.has(topic)) {
      return privateJson({ error: "INVALID_WEBHOOK_HEADERS" }, { status: 400 });
    }

    let payload: unknown;
    try {
      payload = parseJsonBody(rawBody);
    } catch {
      return privateJson({ error: "INVALID_WEBHOOK_PAYLOAD" }, { status: 400 });
    }
    const orderId = extractWooCommerceOrderId(payload);
    const payloadHash = sha256Hex(rawBody);

    let verifiedEvent;
    try {
      verifiedEvent = await fetchRevalidatedWooCommerceOrder(
        orderId,
        environment
      );
    } catch (error) {
      if (
        error instanceof WooCommerceVerificationError &&
        ignoredOrderCodes.has(error.code)
      ) {
        await recordWooCommerceEvent({
          deliveryId,
          errorCode: error.code,
          orderId: String(orderId),
          payloadHash,
          processingStatus: "ignored",
          topic,
        });
        return privateJson({ received: true }, { status: 202 });
      }
      if (
        error instanceof WooCommerceVerificationError &&
        orderReviewCodes.has(error.code)
      ) {
        await recordWooCommerceEvent({
          deliveryId,
          errorCode: error.code,
          orderId: String(orderId),
          payloadHash,
          processingStatus: "failed",
          topic,
        });
        console.error("Paid WooCommerce order requires review", error.code);
        return privateJson(
          { error: "WOOCOMMERCE_ORDER_REQUIRES_REVIEW" },
          { status: 503 }
        );
      }
      throw error;
    }

    await applyRevalidatedWooCommerceOrder({
      deliveryId,
      environment,
      event: verifiedEvent,
      payloadHash,
      topic,
    });

    return privateJson({ received: true });
  } catch (error) {
    if (error instanceof RequestBodyTooLargeError) {
      return privateJson({ error: error.code }, { status: 413 });
    }
    if (error instanceof ServerConfigurationError) {
      return privateJson({ error: error.code }, { status: 503 });
    }
    if (
      error instanceof PaidReadingDatabaseError &&
      error.code === "ORDER_ACCESS_REVOKED"
    ) {
      return privateJson({ ignored: true, received: true }, { status: 202 });
    }
    if (
      error instanceof WooCommerceVerificationError &&
      error.code === "INVALID_WOOCOMMERCE_EVENT"
    ) {
      return privateJson({ error: error.code }, { status: 400 });
    }
    console.error("Paid WooCommerce webhook failed", safeErrorCode(error));
    return privateJson({ error: "WEBHOOK_PROCESSING_FAILED" }, { status: 503 });
  }
}

function safeHeader(value: string | null, maximumLength: number) {
  const normalized = value?.trim() ?? "";
  if (!normalized || normalized.length > maximumLength) return null;
  if (!/^[A-Za-z0-9._:/-]+$/.test(normalized)) return null;
  return normalized;
}
