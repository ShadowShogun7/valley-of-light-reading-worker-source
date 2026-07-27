import type { NextRequest } from "next/server";
import { authorizeReadingToken } from "@/lib/paid-reading/access";
import { sanitizeCustomerResult } from "@/lib/paid-reading/customer-result";
import { getPaidAccessEnvironment } from "@/lib/paid-reading/env";
import {
  privateJson,
  requestFingerprint,
  safeErrorCode,
} from "@/lib/paid-reading/http";
import {
  emptyIntakeDraft,
  intakeDraftSchema,
} from "@/lib/paid-reading/intake";
import {
  getPaidReading,
  PaidReadingDatabaseError,
  RateLimitExceededError,
  takeRateLimit,
} from "@/lib/paid-reading/repository";
import { customerStateFor } from "@/lib/paid-reading/state";
import { paidReadingTokenFromRequest } from "@/lib/paid-reading/session";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  try {
    const environment = getPaidAccessEnvironment();
    await takeRateLimit({
      keyHash: requestFingerprint(request, environment.VALLEY_ACCESS_SIGNING_SECRET),
      maxRequests: 60,
      scope: "reading-lookup",
      windowSeconds: 60,
    });
    const token = paidReadingTokenFromRequest(request);
    if (!token) return unavailable();
    const verifiedToken = authorizeReadingToken(token);
    if (!verifiedToken) return unavailable();

    const stored = await getPaidReading(verifiedToken);
    const state = customerStateFor(stored.reading_status);
    if (state === "unavailable") return unavailable();
    if (state === "ready") {
      if (!stored.result_payload) {
        return privateJson({ error: "READING_RESULT_UNAVAILABLE" }, { status: 503 });
      }
      return privateJson({
        result: sanitizeCustomerResult(stored.result_payload),
        state,
      });
    }
    if (state === "intake") {
      const parsedDraft = intakeDraftSchema.safeParse(stored.draft_payload);
      const draft =
        parsedDraft.success
          ? parsedDraft.data
          : isEmptyObject(stored.draft_payload)
            ? emptyIntakeDraft()
            : null;
      if (!draft) {
        return privateJson({ error: "READING_INTAKE_UNAVAILABLE" }, { status: 503 });
      }
      return privateJson({
        consentVersion: environment.VALLEY_GENERATION_CONSENT_VERSION,
        draft,
        state,
      });
    }
    return privateJson({ state });
  } catch (error) {
    if (error instanceof RateLimitExceededError) {
      return privateJson({ error: error.code }, { status: 429 });
    }
    if (
      error instanceof PaidReadingDatabaseError &&
      error.code === "READING_LINK_UNAVAILABLE"
    ) {
      return unavailable();
    }
    console.error("Paid reading lookup failed", safeErrorCode(error));
    return privateJson({ error: "READING_LOOKUP_FAILED" }, { status: 503 });
  }
}

function unavailable() {
  return privateJson({ error: "READING_LINK_UNAVAILABLE" }, { status: 404 });
}

function isEmptyObject(value: unknown) {
  return (
    Boolean(value) &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    Object.keys(value as Record<string, unknown>).length === 0
  );
}
