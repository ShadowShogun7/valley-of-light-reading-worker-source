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
import {
  buildPrecisionSnapshot,
  finalIntakeSchema,
} from "@/lib/paid-reading/intake";
import {
  DATA_CONFIRMATION_COPY_SHA256,
  SERVICE_START_CONSENT_COPY_SHA256,
} from "@/lib/paid-reading/consent";
import {
  PaidReadingDatabaseError,
  RateLimitExceededError,
  submitIntake,
  takeRateLimit,
} from "@/lib/paid-reading/repository";
import { dispatchReadingFulfillment } from "@/lib/paid-reading/worker";
import { paidReadingTokenFromRequest } from "@/lib/paid-reading/session";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  try {
    const environment = getPaidAccessEnvironment();
    if (
      !isTrustedJsonMutation(request, environment.VALEOFLIGHT_APP_BASE_URL)
    ) {
      return privateJson({ error: "UNTRUSTED_MUTATION" }, { status: 403 });
    }
    await takeRateLimit({
      keyHash: requestFingerprint(request, environment.VALLEY_ACCESS_SIGNING_SECRET),
      maxRequests: 10,
      scope: "reading-intake-submit",
      windowSeconds: 60,
    });
    const token = paidReadingTokenFromRequest(request);
    if (!token) return unavailable();
    const verifiedToken = authorizeReadingToken(token);
    if (!verifiedToken) return unavailable();

    const rawBody = await readRawBody(request, 64 * 1024);
    let body: unknown;
    try {
      body = parseJsonBody(rawBody);
    } catch {
      return privateJson({ error: "INVALID_FINAL_INTAKE" }, { status: 400 });
    }
    const parsed = finalIntakeSchema.safeParse(body);
    if (
      !parsed.success ||
      parsed.data.dataConfirmationVersion !==
        environment.VALLEY_DATA_CONFIRMATION_VERSION ||
      parsed.data.generationConsentVersion !==
        environment.VALLEY_GENERATION_CONSENT_VERSION
    ) {
      return privateJson({ error: "INVALID_FINAL_INTAKE" }, { status: 400 });
    }

    const acceptedAt = new Date().toISOString();
    const submitted = await submitIntake({
      dataConfirmationAcceptedAt: acceptedAt,
      dataConfirmationSha256: DATA_CONFIRMATION_COPY_SHA256,
      dataConfirmationVersion: parsed.data.dataConfirmationVersion,
      expiresAt: verifiedToken.expiresAt,
      finalPayload: parsed.data,
      grantId: verifiedToken.grantId,
      intakeVersion: environment.VALLEY_INTAKE_VERSION,
      precisionSnapshot: buildPrecisionSnapshot(parsed.data),
      serviceStartConsentAcceptedAt: acceptedAt,
      serviceStartConsentSha256: SERVICE_START_CONSENT_COPY_SHA256,
      serviceStartConsentVersion: parsed.data.generationConsentVersion,
      tokenHash: verifiedToken.tokenHash,
    });
    const dispatch = await dispatchReadingFulfillment({
      fulfillmentId: submitted.fulfillment_id,
      readingId: submitted.reading_id,
    });

    return privateJson(
      {
        state: "processing",
        workerAccepted: dispatch.dispatched,
      },
      { status: 202 }
    );
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
      return privateJson(
        { error: error.code, state: "processing" },
        { status: 409 }
      );
    }
    console.error("Paid intake submit failed", safeErrorCode(error));
    return privateJson({ error: "INTAKE_SUBMIT_FAILED" }, { status: 503 });
  }
}

function unavailable() {
  return privateJson({ error: "READING_LINK_UNAVAILABLE" }, { status: 404 });
}
