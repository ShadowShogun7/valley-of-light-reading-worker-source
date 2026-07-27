import type { NextRequest } from "next/server";
import { authorizeReadingToken } from "@/lib/paid-reading/access";
import { getPaidAccessEnvironment } from "@/lib/paid-reading/env";
import {
  parseJsonBody,
  isTrustedJsonMutation,
  privateJson,
  readRawBody,
  requestFingerprint,
  RequestBodyTooLargeError,
  safeErrorCode,
} from "@/lib/paid-reading/http";
import { intakeDraftSchema } from "@/lib/paid-reading/intake";
import {
  PaidReadingDatabaseError,
  RateLimitExceededError,
  saveIntakeDraft,
  takeRateLimit,
} from "@/lib/paid-reading/repository";
import { paidReadingTokenFromRequest } from "@/lib/paid-reading/session";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function PATCH(request: NextRequest) {
  try {
    const environment = getPaidAccessEnvironment();
    if (
      !isTrustedJsonMutation(request, environment.VALEOFLIGHT_APP_BASE_URL)
    ) {
      return privateJson({ error: "UNTRUSTED_MUTATION" }, { status: 403 });
    }
    await takeRateLimit({
      keyHash: requestFingerprint(request, environment.VALLEY_ACCESS_SIGNING_SECRET),
      maxRequests: 30,
      scope: "reading-intake-draft",
      windowSeconds: 60,
    });
    const token = paidReadingTokenFromRequest(request);
    if (!token) return unavailable();
    const verifiedToken = authorizeReadingToken(token);
    if (!verifiedToken) return unavailable();

    const rawBody = await readRawBody(request, 32 * 1024);
    let body: unknown;
    try {
      body = parseJsonBody(rawBody);
    } catch {
      return privateJson({ error: "INVALID_INTAKE_DRAFT" }, { status: 400 });
    }
    const parsed = intakeDraftSchema.safeParse(body);
    if (!parsed.success) {
      return privateJson({ error: "INVALID_INTAKE_DRAFT" }, { status: 400 });
    }

    await saveIntakeDraft({
      draft: parsed.data,
      ...verifiedToken,
    });
    return privateJson({ saved: true, state: "intake" });
  } catch (error) {
    if (error instanceof RequestBodyTooLargeError) {
      return privateJson({ error: error.code }, { status: 413 });
    }
    if (error instanceof RateLimitExceededError) {
      return privateJson({ error: error.code }, { status: 429 });
    }
    if (
      error instanceof PaidReadingDatabaseError &&
      error.code === "READING_LINK_UNAVAILABLE"
    ) {
      return unavailable();
    }
    if (
      error instanceof PaidReadingDatabaseError &&
      error.code === "INTAKE_LOCKED"
    ) {
      return privateJson({ error: error.code }, { status: 409 });
    }
    console.error("Paid intake draft save failed", safeErrorCode(error));
    return privateJson({ error: "INTAKE_DRAFT_SAVE_FAILED" }, { status: 503 });
  }
}

function unavailable() {
  return privateJson({ error: "READING_LINK_UNAVAILABLE" }, { status: 404 });
}
