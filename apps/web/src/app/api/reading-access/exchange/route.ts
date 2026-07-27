import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { authorizeReadingToken } from "@/lib/paid-reading/access";
import {
  getPaidAccessEnvironment,
  ServerConfigurationError,
} from "@/lib/paid-reading/env";
import {
  isTrustedJsonMutation,
  parseJsonBody,
  readRawBody,
  requestFingerprint,
  RequestBodyTooLargeError,
  safeErrorCode,
} from "@/lib/paid-reading/http";
import {
  RateLimitExceededError,
  takeRateLimit,
} from "@/lib/paid-reading/repository";
import {
  paidReadingCookieName,
  paidReadingCookieOptions,
} from "@/lib/paid-reading/session";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const exchangeSchema = z
  .object({
    token: z.string().min(1).max(256),
  })
  .strict();

export async function POST(request: NextRequest) {
  try {
    const environment = getPaidAccessEnvironment();
    if (!isTrustedJsonMutation(request, environment.VALEOFLIGHT_APP_BASE_URL)) {
      return response({ error: "INVALID_REQUEST_ORIGIN" }, 403);
    }
    await takeRateLimit({
      keyHash: requestFingerprint(
        request,
        environment.VALLEY_ACCESS_SIGNING_SECRET
      ),
      maxRequests: 20,
      scope: "reading-link-exchange",
      windowSeconds: 60,
    });
    const rawBody = await readRawBody(request, 4 * 1024);
    let body: unknown;
    try {
      body = parseJsonBody(rawBody);
    } catch {
      return response({ error: "READING_LINK_UNAVAILABLE" }, 404);
    }
    const parsed = exchangeSchema.safeParse(body);
    const verified = parsed.success
      ? authorizeReadingToken(parsed.data.token)
      : null;
    if (!verified || !parsed.success) {
      const unavailable = response(
        { error: "READING_LINK_UNAVAILABLE" },
        404
      );
      unavailable.cookies.delete(paidReadingCookieName());
      return unavailable;
    }

    const accepted = response({ accepted: true }, 200);
    accepted.cookies.set(
      paidReadingCookieName(),
      parsed.data.token,
      paidReadingCookieOptions(verified.expiresAt)
    );
    return accepted;
  } catch (error) {
    if (error instanceof RequestBodyTooLargeError) {
      return response({ error: error.code }, 413);
    }
    if (error instanceof RateLimitExceededError) {
      return response({ error: error.code }, 429);
    }
    if (error instanceof ServerConfigurationError) {
      return response({ error: error.code }, 503);
    }
    console.error("Reading link exchange failed", safeErrorCode(error));
    return response({ error: "READING_LINK_EXCHANGE_FAILED" }, 503);
  }
}

function response(payload: unknown, status: number) {
  const result = NextResponse.json(payload, { status });
  result.headers.set("Cache-Control", "private, no-store, max-age=0");
  result.headers.set("Pragma", "no-cache");
  result.headers.set("Referrer-Policy", "no-referrer");
  result.headers.set("X-Content-Type-Options", "nosniff");
  result.headers.set("X-Robots-Tag", "noindex, nofollow, noarchive");
  return result;
}
