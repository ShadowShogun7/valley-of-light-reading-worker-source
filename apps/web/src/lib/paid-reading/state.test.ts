import assert from "node:assert/strict";
import test from "node:test";
import {
  sanitizeCustomerResult,
  validateCustomerResultContract,
} from "@/lib/paid-reading/customer-result";
import { customerStateFor } from "@/lib/paid-reading/state";
import { isTrustedJsonMutation } from "@/lib/paid-reading/http";

test("one link routes to intake, processing, result, or unavailable", () => {
  assert.equal(customerStateFor("awaiting_intake"), "intake");
  assert.equal(customerStateFor("intake_in_progress"), "intake");
  assert.equal(customerStateFor("queued"), "processing");
  assert.equal(customerStateFor("needs_review"), "processing");
  assert.equal(customerStateFor("ready"), "ready");
  assert.equal(customerStateFor("delivered"), "ready");
  assert.equal(customerStateFor("refunded"), "unavailable");
  assert.equal(customerStateFor("revoked"), "unavailable");
  assert.equal(customerStateFor("erased"), "unavailable");
});

test("customer result removes debug and draft fields recursively", () => {
  assert.deepEqual(
    sanitizeCustomerResult({
      debug: { serviceRoleKey: "never" },
      nested: { draft: "never", headline: "可以顯示" },
      title: "結果",
    }),
    {
      nested: { headline: "可以顯示" },
      title: "結果",
    }
  );
});

test("paid result contract rejects unknown top-level fields", () => {
  const shell = {
    brand: { subtitle: "Valley of Light", title: "光之谷" },
    calculationSteps: [],
    chance: {},
    chapterEvidence: {},
    context: {},
    contractVersion: "complete-relationship-result-v1",
    donts: [],
    evidence: { western: {} },
    id: "reading-1",
    includedReadingRows: [],
    insights: [],
    label: "完整關係解讀",
    metrics: [{}],
    reading: {
      answer: "這是一段解讀。",
      badge: "完整解讀",
      question: "我們還有機會嗎？",
      safety: "保留現實界線。",
      score: 60,
      stage: "剛分手",
    },
    reasons: [],
    sources: [],
    thoughts: [],
    timeline: [],
  };
  assert.equal(validateCustomerResultContract(shell).id, "reading-1");
  assert.throws(
    () =>
      validateCustomerResultContract({
        ...shell,
        internalPrompt: "never",
      }),
    /INVALID_CUSTOMER_RESULT/
  );
});

test("cookie-authenticated mutations require the exact app origin and JSON", () => {
  const appBaseUrl = "https://app.valeoflight.com";
  assert.equal(
    isTrustedJsonMutation(
      new Request(`${appBaseUrl}/api/reading-access/submit`, {
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          Origin: appBaseUrl,
        },
        method: "POST",
      }),
      appBaseUrl
    ),
    true
  );
  assert.equal(
    isTrustedJsonMutation(
      new Request(`${appBaseUrl}/api/reading-access/submit`, {
        headers: {
          "Content-Type": "text/plain",
          Origin: "https://www.valeoflight.com",
        },
        method: "POST",
      }),
      appBaseUrl
    ),
    false
  );
});
