import {
  getLaunchEnvironment,
  ServerConfigurationError,
} from "@/lib/paid-reading/env";
import { privateJson, safeErrorCode } from "@/lib/paid-reading/http";
import { paidAccessHealth } from "@/lib/paid-reading/repository";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  try {
    const environment = getLaunchEnvironment();
    await paidAccessHealth(
      environment.VALLEY_RETENTION_POLICY_VERSION,
      environment.VALLEY_EMAIL_QUEUE_MAX_AGE_MINUTES * 60,
      environment.VALLEY_WOOCOMMERCE_RECONCILIATION_MAX_AGE_MINUTES * 60
    );
    const workerHealthUrl = new URL("/healthz", environment.VALLEY_WORKER_URL);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    try {
      const workerResponse = await fetch(workerHealthUrl, {
        cache: "no-store",
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
      if (!workerResponse.ok) throw new Error("WORKER_NOT_READY");
      const workerHealth = (await workerResponse.json()) as unknown;
      if (
        typeof workerHealth !== "object" ||
        workerHealth === null ||
        !("ready" in workerHealth) ||
        (workerHealth as { ready?: unknown }).ready !== true
      ) {
        throw new Error("WORKER_NOT_READY");
      }
      const sourceResponse = await fetch(
        new URL("/source", environment.VALLEY_WORKER_URL),
        {
          cache: "no-store",
          headers: { Accept: "application/json" },
          signal: controller.signal,
        }
      );
      if (!sourceResponse.ok) throw new Error("WORKER_SOURCE_NOT_AVAILABLE");
      const source = (await sourceResponse.json()) as {
        sourceCodeSha256?: unknown;
        sourceCodeUrl?: unknown;
      };
      if (
        source.sourceCodeUrl !== environment.VALLEY_AGPL_SOURCE_URL ||
        source.sourceCodeSha256 !== environment.VALLEY_AGPL_SOURCE_SHA256
      ) {
        throw new Error("WORKER_SOURCE_RELEASE_MISMATCH");
      }
    } finally {
      clearTimeout(timeout);
    }
    return privateJson({
      ok: true,
      service: "paid-reading",
    });
  } catch (error) {
    if (!(error instanceof ServerConfigurationError)) {
      console.error("Paid reading health check failed", safeErrorCode(error));
    }
    return privateJson(
      {
        ok: false,
        service: "paid-reading",
      },
      { status: 503 }
    );
  }
}
