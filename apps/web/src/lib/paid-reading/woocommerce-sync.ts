import { buildReadingAccess } from "@/lib/paid-reading/access";
import { createGrantId, sha256Hex } from "@/lib/paid-reading/crypto";
import {
  sendAccessRecoveryEmail,
  sendIntakeInvitation,
} from "@/lib/paid-reading/email";
import type { CommerceEnvironment } from "@/lib/paid-reading/env";
import {
  processPaidWooCommerceOrder,
  revokePaidWooCommerceOrder,
  setAccessGrantTokenHash,
} from "@/lib/paid-reading/repository";
import { addDays, toWholeSecondIso } from "@/lib/paid-reading/time";
import type { RevalidatedWooCommerceOrder } from "@/lib/paid-reading/woocommerce";

export async function applyRevalidatedWooCommerceOrder(input: {
  deliveryId: string;
  environment: CommerceEnvironment;
  event: RevalidatedWooCommerceOrder;
  payloadHash: string;
  topic: string;
}) {
  if (input.event.kind === "revoked") {
    const outcome = await revokePaidWooCommerceOrder({
      deliveryId: input.deliveryId,
      payloadHash: input.payloadHash,
      topic: input.topic,
      ...input.event.order,
    });
    return {
      action: outcome.revoked ? ("revoked" as const) : ("ignored" as const),
      duplicateEvent: outcome.duplicate_event,
    };
  }

  const candidateGrantId = createGrantId();
  const candidateExpiry = toWholeSecondIso(
    addDays(new Date(), input.environment.VALLEY_ACCESS_GRANT_TTL_DAYS)
  );
  const entitlement = await processPaidWooCommerceOrder({
    ...input.event.order,
    candidateGrantId,
    deliveryId: input.deliveryId,
    grantExpiresAt: candidateExpiry,
    payloadHash: input.payloadHash,
    topic: input.topic,
  });
  const access = buildReadingAccess({
    expiresAt: entitlement.grant_expires_at,
    grantId: entitlement.grant_id,
  });
  await setAccessGrantTokenHash(
    entitlement.grant_id,
    sha256Hex(access.token)
  );

  if (entitlement.grant_rotated) {
    await sendAccessRecoveryEmail({
      billingEmail: entitlement.billing_email,
      grantExpiresAt: entitlement.grant_expires_at,
      grantId: entitlement.grant_id,
      orderId: entitlement.provider_order_id,
      readingId: entitlement.reading_id,
    });
  } else {
    await sendIntakeInvitation({
      billingEmail: entitlement.billing_email,
      grantExpiresAt: entitlement.grant_expires_at,
      grantId: entitlement.grant_id,
      orderId: entitlement.provider_order_id,
      readingId: entitlement.reading_id,
    });
  }

  return {
    action: "paid" as const,
    duplicateEvent: entitlement.duplicate_event,
    grantRotated: entitlement.grant_rotated,
  };
}
