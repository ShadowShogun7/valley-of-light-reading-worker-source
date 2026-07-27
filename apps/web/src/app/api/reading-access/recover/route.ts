import type { NextRequest } from "next/server";
import { z } from "zod";
import {
  createGrantId,
  hmacHex,
  sha256Hex,
} from "@/lib/paid-reading/crypto";
import { RECOVERY_TEMPLATE_VERSION } from "@/lib/paid-reading/email";
import {
  getPaidAccessEnvironment,
  ServerConfigurationError,
} from "@/lib/paid-reading/env";
import {
  isTrustedJsonMutation,
  parseJsonBody,
  privateJson,
  readRawBody,
  requestFingerprint,
  RequestBodyTooLargeError,
  safeErrorCode,
} from "@/lib/paid-reading/http";
import {
  RateLimitExceededError,
  recoverPaidReading,
  takeRateLimit,
} from "@/lib/paid-reading/repository";
import { addDays, toWholeSecondIso } from "@/lib/paid-reading/time";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const recoveryRequestSchema = z
  .object({
    billingEmail: z.string().trim().email().max(254).transform((value) => value.toLowerCase()),
    orderNumber: z.string().trim().min(1).max(80),
  })
  .strict();

export async function POST(request: NextRequest) {
  try {
    const environment = getPaidAccessEnvironment();
    if (
      !isTrustedJsonMutation(request, environment.VALEOFLIGHT_APP_BASE_URL)
    ) {
      return privateJson({ error: "UNTRUSTED_MUTATION" }, { status: 403 });
    }

    await takeRateLimit({
      keyHash: requestFingerprint(
        request,
        environment.VALLEY_ACCESS_SIGNING_SECRET
      ),
      maxRequests: 5,
      scope: "reading-access-recovery-address",
      windowSeconds: 3600,
    });

    const rawBody = await readRawBody(request, 8 * 1024);
    let body: unknown;
    try {
      body = parseJsonBody(rawBody);
    } catch {
      return accepted();
    }
    const parsed = recoveryRequestSchema.safeParse(body);
    if (!parsed.success) return accepted();

    await takeRateLimit({
      keyHash: hmacHex(
        `recovery:v1:${parsed.data.billingEmail}:${parsed.data.orderNumber}`,
        environment.VALLEY_ACCESS_SIGNING_SECRET
      ),
      maxRequests: 3,
      scope: "reading-access-recovery-order",
      windowSeconds: 3600,
    });

    const candidateGrantId = createGrantId();
    const candidateGrantExpiresAt = toWholeSecondIso(
      addDays(new Date(), environment.VALLEY_ACCESS_GRANT_TTL_DAYS)
    );
    const recoveryTemplateVersion = `${RECOVERY_TEMPLATE_VERSION}:${candidateGrantId}`;
    await recoverPaidReading({
      billingEmail: parsed.data.billingEmail,
      candidateGrantExpiresAt,
      candidateGrantId,
      orderNumber: parsed.data.orderNumber,
      recipientHash: sha256Hex(parsed.data.billingEmail),
      recoveryTemplateVersion,
    });

    return accepted();
  } catch (error) {
    if (error instanceof RequestBodyTooLargeError) {
      return accepted();
    }
    if (error instanceof RateLimitExceededError) {
      return privateJson({ error: error.code }, { status: 429 });
    }
    if (error instanceof ServerConfigurationError) {
      return privateJson({ error: error.code }, { status: 503 });
    }
    console.error("Reading access recovery failed", safeErrorCode(error));
    return privateJson(
      { error: "RECOVERY_TEMPORARILY_UNAVAILABLE" },
      { status: 503 }
    );
  }
}

function accepted() {
  return privateJson(
    {
      accepted: true,
      message:
        "如果資料與可使用的訂單相符，我們會把安全連結寄到付款信箱。",
    },
    { status: 202 }
  );
}
