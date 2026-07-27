import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import {
  buildWooEmailProviderRequest,
  wooBillingEmailMatchesStored,
} from "@/lib/paid-reading/email";

test("Woo email notification contains references but no raw link or personal data", () => {
  const request = buildWooEmailProviderRequest({
    grantExpiresAt: "2026-08-25T12:00:00.000Z",
    grantId: "123e4567-e89b-42d3-a456-426614174000",
    messageKind: "intake_invitation",
    orderId: "13",
    templateVersion: "woo-paid-intake-v1",
  });
  assert.deepEqual(Object.keys(request), [
    "version",
    "orderId",
    "grantId",
    "grantExpiresAt",
    "messageKind",
    "templateVersion",
  ]);
  const serialized = JSON.stringify(request);
  assert.doesNotMatch(serialized, /buyer@|billing|accessUrl|\/r#|token/i);
});

test("a Woo email can be claimed only for the billing address Woo currently owns", () => {
  assert.equal(
    wooBillingEmailMatchesStored(
      "buyer@example.com",
      "Buyer@Example.com"
    ),
    true
  );
  assert.equal(
    wooBillingEmailMatchesStored(
      "corrected@example.com",
      "buyer@example.com"
    ),
    false
  );
});

test("Woo recipient revalidation happens before the durable email claim", async () => {
  const source = await readFile(
    path.resolve(
      process.cwd(),
      "src/lib/paid-reading/email.ts"
    ),
    "utf8"
  );
  const sender = source.slice(
    source.indexOf("async function sendClaimedWooEmail")
  );
  const revalidation = sender.indexOf(
    "await fetchWooCommerceOrderForDelivery"
  );
  const snapshot = sender.indexOf(
    "await getEmailCommerceSnapshot"
  );
  const claim = sender.indexOf("await claimEmailDelivery");
  assert.ok(snapshot >= 0);
  assert.ok(revalidation >= 0);
  assert.ok(revalidation > snapshot);
  assert.ok(claim > revalidation);
});
