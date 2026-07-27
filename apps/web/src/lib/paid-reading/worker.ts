import { signWorkerBody } from "@/lib/paid-reading/crypto";
import { getPaidAccessEnvironment } from "@/lib/paid-reading/env";

export type WorkerDispatchResult =
  | { dispatched: true }
  | { dispatched: false; reason: "not_configured" | "unavailable" };

export async function dispatchReadingFulfillment(input: {
  fulfillmentId: string;
  readingId: string;
}): Promise<WorkerDispatchResult> {
  const environment = getPaidAccessEnvironment();
  if (!environment.VALLEY_WORKER_URL || !environment.VALLEY_WORKER_SIGNING_SECRET) {
    return { dispatched: false, reason: "not_configured" };
  }

  const body = new TextEncoder().encode(
    JSON.stringify({
      fulfillmentId: input.fulfillmentId,
      readingId: input.readingId,
      version: "paid-reading-job-v1",
    })
  );
  const timestamp = String(Math.floor(Date.now() / 1000));
  const signature = signWorkerBody(
    body,
    timestamp,
    environment.VALLEY_WORKER_SIGNING_SECRET
  );
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch(environment.VALLEY_WORKER_URL, {
      body,
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": input.fulfillmentId,
        "X-Valley-Worker-Signature": signature,
        "X-Valley-Worker-Timestamp": timestamp,
      },
      method: "POST",
      signal: controller.signal,
    });
    return response.ok
      ? { dispatched: true }
      : { dispatched: false, reason: "unavailable" };
  } catch {
    return { dispatched: false, reason: "unavailable" };
  } finally {
    clearTimeout(timeout);
  }
}
