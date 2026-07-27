import { z } from "zod";
import {
  sha256Hex,
  signWordPressEmailBody,
} from "@/lib/paid-reading/crypto";
import { getCommerceEnvironment } from "@/lib/paid-reading/env";
import {
  claimEmailDelivery,
  finishEmailDelivery,
  getEmailCommerceSnapshot,
} from "@/lib/paid-reading/repository";
import { fetchWooCommerceOrderForDelivery } from "@/lib/paid-reading/woocommerce";

export const INTAKE_TEMPLATE_VERSION = "woo-paid-intake-v1";
export const RESULT_TEMPLATE_VERSION = "woo-result-ready-v1";
export const RECOVERY_TEMPLATE_VERSION = "woo-access-recovery-v1";

type NotificationInput = {
  billingEmail: string;
  grantExpiresAt: string;
  grantId: string;
  orderId: string;
  readingId: string;
};

export function buildWooEmailProviderRequest(input: Omit<
  NotificationInput,
  "billingEmail" | "readingId"
> & {
  messageKind:
    | "intake_invitation"
    | "result_ready"
    | "access_recovery";
  templateVersion: string;
}) {
  return {
    version: "woo-access-email-v1" as const,
    orderId: input.orderId,
    grantId: input.grantId,
    grantExpiresAt: input.grantExpiresAt,
    messageKind: input.messageKind,
    templateVersion: input.templateVersion,
  };
}

export function wooBillingEmailMatchesStored(
  storedBillingEmail: string,
  currentWooBillingEmail: string
) {
  return storedBillingEmail.trim().toLowerCase()
    === currentWooBillingEmail.trim().toLowerCase();
}

const notificationResponseSchema = z
  .object({
    accepted: z.literal(true),
    duplicate: z.boolean(),
    messageKind: z.enum([
      "intake_invitation",
      "result_ready",
      "access_recovery",
    ]),
    providerMessageId: z
      .string()
      .regex(/^[A-Za-z0-9._:-]{8,160}$/),
  })
  .strict();

export async function sendIntakeInvitation(input: NotificationInput) {
  return sendClaimedWooEmail({
    ...input,
    idempotencyKey: `woo-intake-${input.readingId}-${INTAKE_TEMPLATE_VERSION}`,
    messageKind: "intake_invitation",
    templateVersion: INTAKE_TEMPLATE_VERSION,
  });
}

export async function sendResultReadyEmail(input: NotificationInput) {
  return sendClaimedWooEmail({
    ...input,
    idempotencyKey: `woo-result-${input.readingId}-${RESULT_TEMPLATE_VERSION}`,
    messageKind: "result_ready",
    templateVersion: RESULT_TEMPLATE_VERSION,
  });
}

export async function sendAccessRecoveryEmail(input: NotificationInput) {
  const templateVersion = `${RECOVERY_TEMPLATE_VERSION}:${input.grantId}`;
  return sendClaimedWooEmail({
    ...input,
    idempotencyKey: `woo-recovery-${input.grantId}`,
    messageKind: "access_recovery",
    templateVersion,
  });
}

async function sendClaimedWooEmail(input: NotificationInput & {
  idempotencyKey: string;
  messageKind:
    | "intake_invitation"
    | "result_ready"
    | "access_recovery";
  templateVersion: string;
}) {
  const environment = getCommerceEnvironment();
  const numericOrderId = Number(input.orderId);
  if (
    !Number.isSafeInteger(numericOrderId)
    || numericOrderId <= 0
  ) {
    throw new Error("WOOCOMMERCE_EMAIL_ORDER_INVALID");
  }
  const snapshot = await getEmailCommerceSnapshot(input.readingId);
  if (
    snapshot.reading_id !== input.readingId
    || snapshot.provider_order_id !== input.orderId
    || !wooBillingEmailMatchesStored(
      input.billingEmail,
      snapshot.billing_email
    )
  ) {
    throw new Error("WOOCOMMERCE_EMAIL_SNAPSHOT_MISMATCH");
  }
  const currentOrder = await fetchWooCommerceOrderForDelivery(
    numericOrderId,
    environment,
    {
      amountMinor: snapshot.amount_minor,
      billingEmail: snapshot.billing_email,
      billingEmailConfirmationAcceptanceSource:
        snapshot.billing_email_confirmation_acceptance_source,
      billingEmailConfirmationDigest:
        snapshot.billing_email_confirmation_digest,
      billingEmailConfirmedAt:
        snapshot.billing_email_confirmed_at,
      checkoutTermsAcceptanceSource:
        snapshot.checkout_terms_acceptance_source,
      checkoutTermsPresentedAt:
        snapshot.checkout_terms_presented_at,
      checkoutTermsVersionPresented:
        snapshot.checkout_terms_version_presented,
      currency: snapshot.currency,
      paidAt: snapshot.paid_at,
      productId: snapshot.product_id,
    }
  );
  if (
    !wooBillingEmailMatchesStored(
      input.billingEmail,
      currentOrder.billingEmail
    )
  ) {
    throw new Error("WOOCOMMERCE_EMAIL_RECIPIENT_MISMATCH");
  }
  const recipientHash = sha256Hex(
    input.billingEmail.trim().toLowerCase()
  );
  const providerRequest = buildWooEmailProviderRequest({
    orderId: input.orderId,
    grantId: input.grantId,
    grantExpiresAt: input.grantExpiresAt,
    messageKind: input.messageKind,
    templateVersion: input.templateVersion,
  });
  const claim = await claimEmailDelivery({
    grantId: input.grantId,
    messageKind: input.messageKind,
    provider: "woocommerce",
    providerRequestHash: sha256Hex(JSON.stringify(providerRequest)),
    readingId: input.readingId,
    recipientHash,
    templateVersion: input.templateVersion,
  });
  if (!claim.claimed) {
    return { reason: claim.reason, sent: false, skipped: true };
  }

  const request = {
    ...providerRequest,
    idempotencyKey:
      `${input.idempotencyKey}-g${claim.provider_generation}`,
  };
  const rawBody = JSON.stringify(request);
  const timestamp = String(Math.floor(Date.now() / 1000));
  const signature = signWordPressEmailBody(
    rawBody,
    timestamp,
    environment.VALEOFLIGHT_WORDPRESS_EMAIL_SIGNING_SECRET
  );

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10_000);
    let response: Response;
    try {
      response = await fetch(
        environment.VALEOFLIGHT_WORDPRESS_EMAIL_API_URL,
        {
          body: rawBody,
          cache: "no-store",
          headers: {
            "content-type": "application/json",
            "x-vol-signature": signature,
            "x-vol-timestamp": timestamp,
          },
          method: "POST",
          redirect: "error",
          signal: controller.signal,
        }
      );
    } finally {
      clearTimeout(timeout);
    }
    if (!response.ok) throw new Error("WOOCOMMERCE_EMAIL_REQUEST_FAILED");
    const contentLength = Number(response.headers.get("content-length") ?? 0);
    if (contentLength > 16 * 1024) {
      throw new Error("WOOCOMMERCE_EMAIL_RESPONSE_INVALID");
    }
    const responseText = await response.text();
    if (responseText.length > 16 * 1024) {
      throw new Error("WOOCOMMERCE_EMAIL_RESPONSE_INVALID");
    }
    const parsed = notificationResponseSchema.safeParse(
      JSON.parse(responseText)
    );
    if (
      !parsed.success
      || parsed.data.messageKind !== input.messageKind
    ) {
      throw new Error("WOOCOMMERCE_EMAIL_RESPONSE_INVALID");
    }

    const finished = await finishEmailDelivery({
      accessGrantId: input.grantId,
      attemptCount: claim.attempt_count,
      deliveryId: claim.delivery_id,
      provider: "woocommerce",
      providerMessageId: parsed.data.providerMessageId,
      status: "sent",
    });
    if (finished !== true) throw new Error("EMAIL_DELIVERY_ATTEMPT_STALE");
    return {
      providerMessageId: parsed.data.providerMessageId,
      reason: undefined,
      sent: true,
      skipped: false,
    };
  } catch {
    await finishEmailDelivery({
      accessGrantId: input.grantId,
      attemptCount: claim.attempt_count,
      deliveryId: claim.delivery_id,
      errorCode: "WOOCOMMERCE_EMAIL_SEND_FAILED",
      provider: "woocommerce",
      status: "failed",
    }).catch(() => undefined);
    throw new Error("TRANSACTIONAL_EMAIL_FAILED");
  }
}
