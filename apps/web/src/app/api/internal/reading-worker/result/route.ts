import { z } from "zod";
import { buildReadingAccess } from "@/lib/paid-reading/access";
import {
  createGrantId,
  assertSha256,
  sha256Hex,
  verifyWorkerSignature,
} from "@/lib/paid-reading/crypto";
import { validateCustomerResultContract } from "@/lib/paid-reading/customer-result";
import { sendResultReadyEmail } from "@/lib/paid-reading/email";
import {
  getPaidAccessEnvironment,
  ServerConfigurationError,
} from "@/lib/paid-reading/env";
import {
  parseJsonBody,
  privateJson,
  readRawBody,
  RequestBodyTooLargeError,
  safeErrorCode,
} from "@/lib/paid-reading/http";
import {
  setAccessGrantTokenHash,
  storeReadingResult,
} from "@/lib/paid-reading/repository";
import { addDays, toWholeSecondIso } from "@/lib/paid-reading/time";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const workerResultSchema = z
  .object({
    attemptCount: z.number().int().positive(),
    contractVersion: z.literal("complete-relationship-result-v1"),
    fulfillmentId: z.string().uuid(),
    readingId: z.string().uuid(),
    resultHash: z.string().refine(assertSha256).optional(),
    resultPayload: z.record(z.string(), z.unknown()),
    runtimeVersion: z.string().min(1).max(120),
    sourceFingerprints: z.record(z.string(), z.unknown()).default({}),
    workerId: z.string().regex(/^[A-Za-z0-9._:-]{1,120}$/),
  })
  .strict();

export async function POST(request: Request) {
  try {
    const environment = getPaidAccessEnvironment();
    if (!environment.VALLEY_WORKER_SIGNING_SECRET) {
      throw new ServerConfigurationError(["VALLEY_WORKER_SIGNING_SECRET"]);
    }

    const rawBody = await readRawBody(request, 4 * 1024 * 1024);
    if (
      !verifyWorkerSignature({
        rawBody,
        signingSecret: environment.VALLEY_WORKER_SIGNING_SECRET,
        suppliedSignature: request.headers.get("x-valley-worker-signature"),
        timestamp: request.headers.get("x-valley-worker-timestamp"),
      })
    ) {
      return privateJson({ error: "INVALID_WORKER_SIGNATURE" }, { status: 401 });
    }

    let body: unknown;
    try {
      body = parseJsonBody(rawBody);
    } catch {
      return privateJson({ error: "INVALID_WORKER_RESULT" }, { status: 400 });
    }
    const parsed = workerResultSchema.safeParse(body);
    if (!parsed.success) {
      return privateJson({ error: "INVALID_WORKER_RESULT" }, { status: 400 });
    }

    const customerResult = validateCustomerResultContract(
      parsed.data.resultPayload
    );
    const computedHash = sha256Hex(JSON.stringify(customerResult));
    if (parsed.data.resultHash && parsed.data.resultHash !== computedHash) {
      return privateJson({ error: "RESULT_HASH_MISMATCH" }, { status: 400 });
    }

    const candidateGrantId = createGrantId();
    const candidateGrantExpiresAt = toWholeSecondIso(
      addDays(new Date(), environment.VALLEY_ACCESS_GRANT_TTL_DAYS)
    );
    const stored = await storeReadingResult({
      attemptCount: parsed.data.attemptCount,
      candidateGrantExpiresAt,
      candidateGrantId,
      contractVersion: parsed.data.contractVersion,
      fulfillmentId: parsed.data.fulfillmentId,
      readingId: parsed.data.readingId,
      resultHash: computedHash,
      resultPayload: customerResult,
      runtimeVersion: parsed.data.runtimeVersion,
      sourceFingerprints: parsed.data.sourceFingerprints,
      workerId: parsed.data.workerId,
    });
    if (new Date(stored.grant_expires_at).getTime() <= Date.now()) {
      throw new Error("ACCESS_GRANT_EXPIRED");
    }
    const access = buildReadingAccess({
      expiresAt: stored.grant_expires_at,
      grantId: stored.grant_id,
    });
    await setAccessGrantTokenHash(stored.grant_id, sha256Hex(access.token));
    const emailOutcome = await sendResultReadyEmail({
      billingEmail: stored.billing_email,
      grantExpiresAt: stored.grant_expires_at,
      grantId: stored.grant_id,
      orderId: stored.provider_order_id,
      readingId: stored.reading_id,
    });
    return privateJson({
      accepted: true,
      emailAccepted:
        emailOutcome.sent || emailOutcome.reason === "already_sent",
    });
  } catch (error) {
    if (error instanceof RequestBodyTooLargeError) {
      return privateJson({ error: error.code }, { status: 413 });
    }
    if (error instanceof ServerConfigurationError) {
      return privateJson({ error: error.code }, { status: 503 });
    }
    console.error("Reading worker result callback failed", safeErrorCode(error));
    return privateJson({ error: "WORKER_RESULT_FAILED" }, { status: 503 });
  }
}
