import {
  createHash,
  createHmac,
  randomUUID,
  timingSafeEqual,
} from "node:crypto";

const ACCESS_TOKEN_VERSION = "v1";
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const SIGNATURE_PATTERN = /^[A-Za-z0-9_-]{43}$/;
const HASH_PATTERN = /^[0-9a-f]{64}$/;

export type VerifiedAccessToken = {
  expiresAt: string;
  expiresAtEpochSeconds: number;
  grantId: string;
  tokenHash: string;
};

export function createGrantId() {
  return randomUUID();
}

export function buildAccessToken({
  expiresAt,
  grantId,
  signingSecret,
}: {
  expiresAt: Date | string;
  grantId: string;
  signingSecret: string;
}) {
  if (!UUID_PATTERN.test(grantId)) throw new Error("INVALID_GRANT_ID");
  const expiresAtDate = expiresAt instanceof Date ? expiresAt : new Date(expiresAt);
  const expiresAtEpochSeconds = Math.floor(expiresAtDate.getTime() / 1000);
  if (!Number.isSafeInteger(expiresAtEpochSeconds)) throw new Error("INVALID_GRANT_EXPIRY");
  const signature = accessSignature(grantId, expiresAtEpochSeconds, signingSecret);
  return `${ACCESS_TOKEN_VERSION}.${grantId}.${expiresAtEpochSeconds}.${signature}`;
}

export function verifyAccessToken(
  token: string,
  signingSecret: string,
  now = new Date()
): VerifiedAccessToken | null {
  if (token.length > 256) return null;
  const [version, grantId, expiresAtRaw, suppliedSignature, extra] = token.split(".");
  if (
    extra !== undefined ||
    version !== ACCESS_TOKEN_VERSION ||
    !UUID_PATTERN.test(grantId ?? "") ||
    !/^\d{10,12}$/.test(expiresAtRaw ?? "") ||
    !SIGNATURE_PATTERN.test(suppliedSignature ?? "")
  ) {
    return null;
  }

  const expiresAtEpochSeconds = Number(expiresAtRaw);
  if (!Number.isSafeInteger(expiresAtEpochSeconds)) return null;
  if (expiresAtEpochSeconds <= Math.floor(now.getTime() / 1000)) return null;

  const expectedSignature = accessSignature(grantId, expiresAtEpochSeconds, signingSecret);
  if (!constantTimeEqual(suppliedSignature, expectedSignature)) return null;

  return {
    expiresAt: new Date(expiresAtEpochSeconds * 1000).toISOString(),
    expiresAtEpochSeconds,
    grantId,
    tokenHash: sha256Hex(token),
  };
}

export function verifyWooCommerceSignature(
  rawBody: Uint8Array,
  suppliedSignature: string | null,
  webhookSecret: string
) {
  if (!suppliedSignature || suppliedSignature.length > 128) return false;
  const expected = createHmac("sha256", webhookSecret).update(rawBody).digest("base64");
  return constantTimeEqual(suppliedSignature.trim(), expected);
}

export function signWorkerBody(rawBody: Uint8Array, timestamp: string, signingSecret: string) {
  return createHmac("sha256", signingSecret)
    .update(timestamp)
    .update(".")
    .update(rawBody)
    .digest("base64url");
}

export function signWordPressEmailBody(
  rawBody: string,
  timestamp: string,
  signingSecret: string
) {
  return createHmac("sha256", signingSecret)
    .update(timestamp)
    .update(".")
    .update(rawBody)
    .digest("base64url");
}

export function verifyWorkerSignature({
  now = new Date(),
  rawBody,
  signingSecret,
  suppliedSignature,
  timestamp,
}: {
  now?: Date;
  rawBody: Uint8Array;
  signingSecret: string;
  suppliedSignature: string | null;
  timestamp: string | null;
}) {
  if (
    !timestamp ||
    !suppliedSignature ||
    !/^\d{10}$/.test(timestamp) ||
    !SIGNATURE_PATTERN.test(suppliedSignature)
  ) {
    return false;
  }
  const timestampSeconds = Number(timestamp);
  const nowSeconds = Math.floor(now.getTime() / 1000);
  if (Math.abs(nowSeconds - timestampSeconds) > 300) return false;
  return constantTimeEqual(
    suppliedSignature,
    signWorkerBody(rawBody, timestamp, signingSecret)
  );
}

export function sha256Hex(value: string | Uint8Array) {
  return createHash("sha256").update(value).digest("hex");
}

export function hmacHex(value: string, signingSecret: string) {
  return createHmac("sha256", signingSecret).update(value).digest("hex");
}

export function assertSha256(value: string) {
  return HASH_PATTERN.test(value);
}

function accessSignature(
  grantId: string,
  expiresAtEpochSeconds: number,
  signingSecret: string
) {
  return createHmac("sha256", signingSecret)
    .update(`${ACCESS_TOKEN_VERSION}\n${grantId}\n${expiresAtEpochSeconds}`)
    .digest("base64url");
}

function constantTimeEqual(left: string, right: string) {
  const leftBuffer = Buffer.from(left);
  const rightBuffer = Buffer.from(right);
  return leftBuffer.length === rightBuffer.length && timingSafeEqual(leftBuffer, rightBuffer);
}
