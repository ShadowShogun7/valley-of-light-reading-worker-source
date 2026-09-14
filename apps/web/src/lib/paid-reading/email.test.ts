import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import {
  buildWooEmailProviderRequest,
  RECOVERY_TEMPLATE_VERSION,
  wooBillingEmailMatchesStored,
} from "@/lib/paid-reading/email";

test("recovery requests and email claims use the database's provider-neutral identity", async () => {
  assert.equal(RECOVERY_TEMPLATE_VERSION, "paid-access-recovery-v1");
  const sql = await readFile(path.resolve(
    process.cwd(),
    "../../supabase/migrations/20260726170000_add_paid_reading_delivery.sql"
  ), "utf8");
  for (const fragment of [
    `'^${RECOVERY_TEMPLATE_VERSION}:[0-9a-f-]{36}$'`,
    `'${RECOVERY_TEMPLATE_VERSION}:' || p_candidate_grant_id::text`,
    `'${RECOVERY_TEMPLATE_VERSION}:' || v_grant.id::text`,
    `'${RECOVERY_TEMPLATE_VERSION}:' || p_replacement_grant_id::text`,
  ]) {
    assert.ok(sql.includes(fragment), fragment);
  }
  for (const file of [
    "src/app/api/reading-access/recover/route.ts",
    "src/lib/paid-reading/email.ts",
  ]) {
    const source = await readFile(path.resolve(process.cwd(), file), "utf8");
    assert.match(source, /`\$\{RECOVERY_TEMPLATE_VERSION\}:\$\{/);
    assert.doesNotMatch(source, /woo-access-recovery-v1/);
  }
});

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
