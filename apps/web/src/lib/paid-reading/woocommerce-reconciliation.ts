import { randomUUID } from "node:crypto";
import type { CommerceEnvironment } from "@/lib/paid-reading/env";
import { safeErrorCode } from "@/lib/paid-reading/http";
import {
  beginWooCommerceReconciliation,
  failWooCommerceReconciliation,
  finishWooCommerceReconciliation,
  recordWooCommerceEvent,
} from "@/lib/paid-reading/repository";
import {
  buildWooCommerceReconciliationEvent,
  fetchWooCommerceReconciliationPage,
  verifyWooCommerceEvent,
  WooCommerceVerificationError,
} from "@/lib/paid-reading/woocommerce";
import { applyRevalidatedWooCommerceOrder } from "@/lib/paid-reading/woocommerce-sync";

const ignoredOrderCodes = new Set([
  "ORDER_NOT_PAID",
  "ORDER_HAS_NO_PAID_TIMESTAMP",
  "ORDER_PRODUCT_MISMATCH",
]);

export async function reconcileWooCommerceOrders(
  environment: CommerceEnvironment
) {
  const requestId = randomUUID();
  const lease = await beginWooCommerceReconciliation({
    leaseSeconds: 300,
    lookbackSeconds:
      environment.VALLEY_WOOCOMMERCE_RECONCILIATION_LOOKBACK_HOURS * 3600,
    requestId,
    windowLagSeconds:
      environment.VALLEY_WOOCOMMERCE_RECONCILIATION_WINDOW_LAG_SECONDS,
  });
  if (!lease.acquired) {
    return { acquired: false as const };
  }

  const counts = {
    failedOrders: 0,
    ignoredOrders: 0,
    paidOrders: 0,
    revokedOrders: 0,
    scannedOrders: 0,
  };

  try {
    const page = await fetchWooCommerceReconciliationPage(
      {
        modifiedAfter: lease.window_start,
        modifiedBefore: lease.window_end,
        page: lease.page,
        perPage:
          environment.VALLEY_WOOCOMMERCE_RECONCILIATION_BATCH_SIZE,
      },
      environment
    );

    for (const order of page.orders) {
      counts.scannedOrders += 1;
      const event = buildWooCommerceReconciliationEvent(order);
      let verified;
      try {
        verified = verifyWooCommerceEvent(order, environment);
      } catch (error) {
        if (!(error instanceof WooCommerceVerificationError)) throw error;
        const ignored = ignoredOrderCodes.has(error.code);
        await recordWooCommerceEvent({
          ...event,
          errorCode: error.code,
          processingStatus: ignored ? "ignored" : "failed",
        });
        if (ignored) {
          counts.ignoredOrders += 1;
        } else {
          counts.failedOrders += 1;
        }
        continue;
      }

      const outcome = await applyRevalidatedWooCommerceOrder({
        deliveryId: event.deliveryId,
        environment,
        event: verified,
        payloadHash: event.payloadHash,
        topic: event.topic,
      });
      if (outcome.action === "paid") counts.paidOrders += 1;
      if (outcome.action === "revoked") counts.revokedOrders += 1;
      if (outcome.action === "ignored") counts.ignoredOrders += 1;
    }

    const windowComplete =
      page.orders.length === 0 || lease.page >= page.totalPages;
    await finishWooCommerceReconciliation({
      ...counts,
      nextPage: lease.page + 1,
      requestId,
      runId: lease.run_id,
      windowComplete,
    });
    return {
      acquired: true as const,
      ...counts,
      page: lease.page,
      windowComplete,
    };
  } catch (error) {
    await failWooCommerceReconciliation({
      errorCode: safeErrorCode(error),
      requestId,
      runId: lease.run_id,
    }).catch(() => undefined);
    throw error;
  }
}
