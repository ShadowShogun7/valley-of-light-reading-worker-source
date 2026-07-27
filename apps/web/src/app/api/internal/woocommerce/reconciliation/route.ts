import { timingSafeEqual } from "node:crypto";
import {
  getCommerceEnvironment,
  ServerConfigurationError,
} from "@/lib/paid-reading/env";
import { privateJson, safeErrorCode } from "@/lib/paid-reading/http";
import { reconcileWooCommerceOrders } from "@/lib/paid-reading/woocommerce-reconciliation";

export const dynamic = "force-dynamic";
export const maxDuration = 300;
export const runtime = "nodejs";

export async function GET(request: Request) {
  try {
    const environment = getCommerceEnvironment();
    if (
      !environment.CRON_SECRET ||
      !matchesCronSecret(
        request.headers.get("authorization"),
        environment.CRON_SECRET
      )
    ) {
      return privateJson({ error: "UNAUTHORIZED" }, { status: 401 });
    }

    const outcome = await reconcileWooCommerceOrders(environment);
    return privateJson({
      accepted: true,
      acquired: outcome.acquired,
      ...(outcome.acquired
        ? {
            failed: outcome.failedOrders,
            ignored: outcome.ignoredOrders,
            paid: outcome.paidOrders,
            revoked: outcome.revokedOrders,
            scanned: outcome.scannedOrders,
            windowComplete: outcome.windowComplete,
          }
        : {}),
    });
  } catch (error) {
    if (error instanceof ServerConfigurationError) {
      return privateJson({ error: error.code }, { status: 503 });
    }
    console.error(
      "WooCommerce reconciliation failed",
      safeErrorCode(error)
    );
    return privateJson(
      { error: "WOOCOMMERCE_RECONCILIATION_FAILED" },
      { status: 503 }
    );
  }
}

function matchesCronSecret(
  authorization: string | null,
  cronSecret: string
) {
  const supplied = authorization ?? "";
  const expected = `Bearer ${cronSecret}`;
  const suppliedBuffer = Buffer.from(supplied);
  const expectedBuffer = Buffer.from(expected);
  return (
    suppliedBuffer.length === expectedBuffer.length &&
    timingSafeEqual(suppliedBuffer, expectedBuffer)
  );
}
