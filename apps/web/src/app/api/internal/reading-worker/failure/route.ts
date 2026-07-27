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
import { failReadingFulfillment } from "@/lib/paid-reading/repository";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const workerFailureSchema = z
  .object({
    attemptCount: z.number().int().positive(),
    errorCode: z.string().regex(/^[A-Z0-9_]{2,80}$/),
    fulfillmentId: z.string().uuid(),
    readingId: z.string().uuid(),
    retryable: z.boolean(),
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
      return privateJson({ error: "INVALID_WORKER_FAILURE" }, { status: 400 });
    }

    const parsed = workerFailureSchema.safeParse(body);
    if (!parsed.success) {
      return privateJson({ error: "INVALID_WORKER_FAILURE" }, { status: 400 });
    }

    const result = await failReadingFulfillment(parsed.data);
    return privateJson(result);
  } catch (error) {
    if (error instanceof RequestBodyTooLargeError) {
      return privateJson({ error: error.code }, { status: 413 });
    }
    if (error instanceof ServerConfigurationError) {
      return privateJson({ error: error.code }, { status: 503 });
    }
    console.error("Reading worker failure callback failed", safeErrorCode(error));
    return privateJson({ error: "WORKER_FAILURE_CALLBACK_FAILED" }, { status: 503 });
  }
}
