import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";
import {
  DATA_CONFIRMATION_COPY,
  DATA_CONFIRMATION_COPY_SHA256,
  SERVICE_START_CONSENT_COPY,
  SERVICE_START_CONSENT_COPY_SHA256,
} from "@/lib/paid-reading/consent";

test("stored consent fingerprints match the exact visible Traditional Chinese copy", () => {
  assert.equal(sha256(DATA_CONFIRMATION_COPY), DATA_CONFIRMATION_COPY_SHA256);
  assert.equal(
    sha256(SERVICE_START_CONSENT_COPY),
    SERVICE_START_CONSENT_COPY_SHA256
  );
});

function sha256(value: string) {
  return createHash("sha256").update(value, "utf8").digest("hex");
}
