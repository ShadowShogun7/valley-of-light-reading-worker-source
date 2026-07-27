import { Resend } from "resend";
import { z } from "zod";
import { sha256Hex } from "@/lib/paid-reading/crypto";
import {
  getResendEnvironment,
  ServerConfigurationError,
} from "@/lib/paid-reading/env";
import {
  privateJson,
  readRawBody,
  RequestBodyTooLargeError,
  safeErrorCode,
} from "@/lib/paid-reading/http";
import { recordResendEmailEvent } from "@/lib/paid-reading/repository";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const trackedEventSchema = z.object({
  created_at: z.string().datetime({ offset: true }),
  data: z.object({
    email_id: z.string().regex(/^[A-Za-z0-9._:-]{8,160}$/),
  }),
  type: z.enum([
    "email.sent",
    "email.delivered",
    "email.delivery_delayed",
    "email.failed",
    "email.bounced",
    "email.complained",
    "email.suppressed",
  ]),
});

export async function POST(request: Request) {
  try {
    const environment = getResendEnvironment();
    const eventId = request.headers.get("svix-id")?.trim() ?? "";
    const timestamp = request.headers.get("svix-timestamp")?.trim() ?? "";
    const signature = request.headers.get("svix-signature")?.trim() ?? "";
    if (
      !/^[A-Za-z0-9._:-]{8,160}$/.test(eventId) ||
      !timestamp ||
      !signature
    ) {
      return privateJson({ error: "INVALID_RESEND_SIGNATURE" }, { status: 401 });
    }

    const rawBody = await readRawBody(request, 256 * 1024);
    let verified: unknown;
    try {
      verified = new Resend(environment.RESEND_API_KEY).webhooks.verify({
        headers: {
          id: eventId,
          signature,
          timestamp,
        },
        payload: new TextDecoder("utf-8", { fatal: true }).decode(rawBody),
        webhookSecret: environment.RESEND_WEBHOOK_SECRET,
      });
    } catch {
      return privateJson({ error: "INVALID_RESEND_SIGNATURE" }, { status: 401 });
    }

    const parsed = trackedEventSchema.safeParse(verified);
    if (!parsed.success) {
      return privateJson({ received: true }, { status: 202 });
    }
    const outcome = await recordResendEmailEvent({
      eventAt: new Date(parsed.data.created_at).toISOString(),
      eventId,
      eventType: parsed.data.type,
      payloadHash: sha256Hex(rawBody),
      providerMessageId: parsed.data.data.email_id,
    });
    if (!outcome.matched) {
      return privateJson(
        { error: "RESEND_MESSAGE_NOT_READY" },
        { status: 503 }
      );
    }
    return privateJson({ received: true });
  } catch (error) {
    if (error instanceof RequestBodyTooLargeError) {
      return privateJson({ error: error.code }, { status: 413 });
    }
    if (error instanceof ServerConfigurationError) {
      return privateJson({ error: error.code }, { status: 503 });
    }
    console.error("Resend webhook failed", safeErrorCode(error));
    return privateJson({ error: "RESEND_WEBHOOK_FAILED" }, { status: 503 });
  }
}
