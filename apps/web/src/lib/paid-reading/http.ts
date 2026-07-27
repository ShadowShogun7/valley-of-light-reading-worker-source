import { hmacHex } from "@/lib/paid-reading/crypto";

export class RequestBodyTooLargeError extends Error {
  readonly code = "REQUEST_BODY_TOO_LARGE";
}

export async function readRawBody(request: Request, maxBytes: number) {
  const advertisedSize = Number(request.headers.get("content-length") ?? "0");
  if (Number.isFinite(advertisedSize) && advertisedSize > maxBytes) {
    throw new RequestBodyTooLargeError();
  }
  const body = new Uint8Array(await request.arrayBuffer());
  if (body.byteLength > maxBytes) throw new RequestBodyTooLargeError();
  return body;
}

export function parseJsonBody(rawBody: Uint8Array) {
  return JSON.parse(new TextDecoder().decode(rawBody)) as unknown;
}

export function privateJson(data: unknown, init: ResponseInit = {}) {
  const headers = new Headers(init.headers);
  headers.set("Cache-Control", "private, no-store, max-age=0");
  headers.set("Pragma", "no-cache");
  headers.set("Referrer-Policy", "no-referrer");
  headers.set("X-Content-Type-Options", "nosniff");
  headers.set("X-Robots-Tag", "noindex, nofollow, noarchive");
  return Response.json(data, { ...init, headers });
}

export function requestFingerprint(request: Request, signingSecret: string) {
  const forwardedFor = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  const address =
    forwardedFor ||
    request.headers.get("x-real-ip")?.trim() ||
    request.headers.get("cf-connecting-ip")?.trim() ||
    "unknown";
  return hmacHex(`request-address:v1:${address}`, signingSecret);
}

export function isTrustedJsonMutation(request: Request, appBaseUrl: string) {
  const contentType = request.headers
    .get("content-type")
    ?.split(";", 1)[0]
    ?.trim()
    .toLowerCase();
  if (contentType !== "application/json") return false;

  try {
    const expectedOrigin = new URL(appBaseUrl).origin;
    return request.headers.get("origin") === expectedOrigin;
  } catch {
    return false;
  }
}

export function safeErrorCode(error: unknown) {
  if (typeof error === "object" && error && "code" in error) {
    const code = String((error as { code?: unknown }).code ?? "");
    if (/^[A-Z0-9_]{2,80}$/.test(code)) return code;
  }
  if (error instanceof Error && /^[A-Z0-9_]{2,80}$/.test(error.message)) {
    return error.message;
  }
  return "INTERNAL_ERROR";
}
