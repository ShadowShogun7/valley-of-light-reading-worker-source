import { z } from "zod";
import { buildReadingAccess } from "@/lib/paid-reading/access";
import { sha256Hex, verifyWorkerSignature } from "@/lib/paid-reading/crypto";
import {
  INTAKE_TEMPLATE_VERSION,
  sendAccessRecoveryEmail,
  RESULT_TEMPLATE_VERSION,
  sendIntakeInvitation,
  sendResultReadyEmail,
} from "@/lib/paid-reading/email";
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
  getEmailReconciliationCandidates,
  setAccessGrantTokenHash,
} from "@/lib/paid-reading/repository";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const reconciliationRequestSchema = z
  .object({
    limit: z.number().int().min(1).max(20).default(5),
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
      return privateJson(
        { error: "INVALID_EMAIL_RECONCILIATION_REQUEST" },
        { status: 400 }
      );
    }
    const parsed = reconciliationRequestSchema.safeParse(body);
    if (!parsed.success) {
      return privateJson(
        { error: "INVALID_EMAIL_RECONCILIATION_REQUEST" },
        { status: 400 }
      );
    }

    const candidates = await getEmailReconciliationCandidates({
      intakeTemplateVersion: INTAKE_TEMPLATE_VERSION,
      limit: parsed.data.limit,
      resultTemplateVersion: RESULT_TEMPLATE_VERSION,
    });
    let providerAccepted = 0;
    let failed = 0;
    let skipped = 0;

    for (const candidate of candidates) {
      try {
        const access = buildReadingAccess({
          expiresAt: candidate.grant_expires_at,
          grantId: candidate.grant_id,
        });
        await setAccessGrantTokenHash(
          candidate.grant_id,
          sha256Hex(access.token)
        );

        const outcome =
          candidate.message_kind === "intake_invitation"
            ? await sendIntakeInvitation({
                billingEmail: candidate.billing_email,
                grantExpiresAt: candidate.grant_expires_at,
                grantId: candidate.grant_id,
                orderId: candidate.provider_order_id,
                readingId: candidate.reading_id,
              })
            : candidate.message_kind === "result_ready"
              ? await sendResultReadyEmail({
                  billingEmail: candidate.billing_email,
                  grantExpiresAt: candidate.grant_expires_at,
                  grantId: candidate.grant_id,
                  orderId: candidate.provider_order_id,
                  readingId: candidate.reading_id,
                })
              : await sendAccessRecoveryEmail({
                billingEmail: candidate.billing_email,
                grantExpiresAt: candidate.grant_expires_at,
                grantId: candidate.grant_id,
                orderId: candidate.provider_order_id,
                readingId: candidate.reading_id,
              });

        if (outcome.sent || outcome.reason === "already_sent") {
          providerAccepted += 1;
        } else {
          skipped += 1;
        }
      } catch (error) {
        failed += 1;
        console.error(
          "Email reconciliation candidate failed",
          safeErrorCode(error)
        );
      }
    }

    return privateJson({
      accepted: true,
      candidates: candidates.length,
      providerAccepted,
      failed,
      skipped,
    });
  } catch (error) {
    if (error instanceof RequestBodyTooLargeError) {
      return privateJson({ error: error.code }, { status: 413 });
    }
    if (error instanceof ServerConfigurationError) {
      return privateJson({ error: error.code }, { status: 503 });
    }
    console.error("Email reconciliation failed", safeErrorCode(error));
    return privateJson(
      { error: "EMAIL_RECONCILIATION_FAILED" },
      { status: 503 }
    );
  }
}
