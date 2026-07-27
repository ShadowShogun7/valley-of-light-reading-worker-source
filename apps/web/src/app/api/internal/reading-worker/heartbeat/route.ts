import { z } from "zod";
import { verifyWorkerSignature } from "@/lib/paid-reading/crypto";
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
import { renewReadingFulfillmentLease } from "@/lib/paid-reading/repository";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const workerHeartbeatSchema = z
  .object({
    attemptCount: z.number().int().positive(),
    fulfillmentId: z.string().uuid(),
    leaseSeconds: z.number().int().min(60).max(1800),
    readingId: z.string().uuid(),
    workerId: z.string().regex(/^[A-Za-z0-9._:-]{1,120}$/),
  })
  .strict();

export async function POST(request: Request) {
  try {
    const environment = getPaidAccessEnvironment();
    if (!environment.VALLEY_WORKER_SIGNING_SECRET) {
      throw new ServerConfigurationError(["VALLEY_WORKER_SIGNING_SECRET"]);
    }

    const rawBody = await readRawBody(request, 16 * 1024);
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
      return privateJson({ error: "INVALID_WORKER_HEARTBEAT" }, { status: 400 });
    }
    const parsed = workerHeartbeatSchema.safeParse(body);
    if (!parsed.success) {
      return privateJson({ error: "INVALID_WORKER_HEARTBEAT" }, { status: 400 });
    }

    const result = await renewReadingFulfillmentLease(parsed.data);
    return privateJson(result);
  } catch (error) {
    if (error instanceof RequestBodyTooLargeError) {
      return privateJson({ error: error.code }, { status: 413 });
    }
    if (error instanceof ServerConfigurationError) {
      return privateJson({ error: error.code }, { status: 503 });
    }
    console.error("Reading worker heartbeat failed", safeErrorCode(error));
    return privateJson({ error: "WORKER_HEARTBEAT_FAILED" }, { status: 503 });
  }
}
