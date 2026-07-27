import { z } from "zod";
import { getPaidReadingDatabase } from "@/lib/paid-reading/supabase";

const paidOrderResultSchema = z.object({
  duplicate_event: z.boolean(),
  grant_rotated: z.boolean(),
  is_new_entitlement: z.boolean(),
  reading_id: z.string().uuid(),
  commerce_order_id: z.string().uuid(),
  grant_id: z.string().uuid(),
  grant_expires_at: z.string().datetime({ offset: true }),
  billing_email: z.string().email(),
  order_number: z.string().min(1),
  provider_order_id: z.string().regex(/^[1-9][0-9]{0,18}$/),
});

const readingLookupSchema = z.object({
  reading_id: z.string().uuid(),
  public_id: z.string().uuid(),
  reading_status: z.string().min(1),
  draft_payload: z.unknown(),
  intake_submitted_at: z.string().datetime({ offset: true }).nullable().optional(),
  fulfillment_status: z.string().nullable().optional(),
  result_payload: z.unknown().nullable(),
});

const submitResultSchema = z.object({
  reading_id: z.string().uuid(),
  fulfillment_id: z.string().uuid(),
  reading_status: z.literal("queued"),
});

const storedResultSchema = z.object({
  duplicate_result: z.boolean(),
  reading_id: z.string().uuid(),
  billing_email: z.string().email(),
  order_number: z.string().min(1),
  grant_id: z.string().uuid(),
  grant_expires_at: z.string().datetime({ offset: true }),
  provider_order_id: z.string().regex(/^[1-9][0-9]{0,18}$/),
});

const emailClaimSchema = z.discriminatedUnion("claimed", [
  z.object({
    claimed: z.literal(false),
    reason: z.string().optional(),
  }),
  z.object({
    attempt_count: z.number().int().positive(),
    claimed: z.literal(true),
    delivery_id: z.string().uuid(),
    provider_generation: z.number().int().positive(),
  }),
]);

const emailCommerceSnapshotSchema = z.object({
  amount_minor: z.number().int().nonnegative(),
  billing_email: z.string().email(),
  billing_email_confirmation_acceptance_source: z.enum([
    "classic-checkout-server-validation",
    "store-api-server-validation",
  ]),
  billing_email_confirmation_digest: z
    .string()
    .regex(/^[0-9a-f]{64}$/),
  billing_email_confirmed_at: z.string().datetime({ offset: true }),
  checkout_terms_acceptance_source: z.enum([
    "classic-required-terms-checkbox",
    "store-api-validated-checkout",
  ]),
  checkout_terms_presented_at: z.string().datetime({ offset: true }),
  checkout_terms_version_presented: z.string().min(1).max(80),
  currency: z.string().regex(/^[A-Z]{3}$/),
  paid_at: z.string().datetime({ offset: true }),
  product_id: z.number().int().positive(),
  provider_order_id: z.string().regex(/^[1-9][0-9]{0,18}$/),
  reading_id: z.string().uuid(),
});

export type EmailCommerceSnapshot = z.infer<
  typeof emailCommerceSnapshotSchema
>;

const emailReconciliationCandidateSchema = z.object({
  billing_email: z.string().email(),
  grant_expires_at: z.string().datetime({ offset: true }),
  grant_id: z.string().uuid(),
  message_kind: z.enum([
    "intake_invitation",
    "result_ready",
    "access_recovery",
  ]),
  order_number: z.string().min(1),
  provider_order_id: z.string().regex(/^[1-9][0-9]{0,18}$/),
  reading_id: z.string().uuid(),
  template_version: z.string().min(1).max(120),
});

const recoveryResultSchema = z.discriminatedUnion("eligible", [
  z.object({ eligible: z.literal(false) }),
  z.object({
    billing_email: z.string().email(),
    eligible: z.literal(true),
    grant_expires_at: z.string().datetime({ offset: true }),
    grant_id: z.string().uuid(),
    order_number: z.string().min(1),
    provider_order_id: z.string().regex(/^[1-9][0-9]{0,18}$/),
    reading_id: z.string().uuid(),
    reading_status: z.string().min(1),
  }),
]);

const revokedOrderResultSchema = z.object({
  duplicate_event: z.boolean(),
  entitlement_found: z.boolean(),
  revoked: z.boolean(),
});

const wooCommerceReconciliationLeaseSchema = z.discriminatedUnion("acquired", [
  z.object({ acquired: z.literal(false) }),
  z.object({
    acquired: z.literal(true),
    page: z.number().int().positive(),
    run_id: z.string().uuid(),
    window_end: z.string().datetime({ offset: true }),
    window_start: z.string().datetime({ offset: true }),
  }),
]);

const fulfillmentClaimSchema = z.discriminatedUnion("claimed", [
  z.object({ claimed: z.literal(false) }),
  z.object({
    analysis_datetime: z.string().datetime({ offset: true }),
    analysis_timezone: z.literal("Asia/Taipei"),
    attempt_count: z.number().int().positive(),
    claimed: z.literal(true),
    final_payload: z.unknown(),
    fulfillment_id: z.string().uuid(),
    generation_consent_version: z.string().min(1),
    intake_version: z.string().min(1),
    lease_expires_at: z.string().datetime({ offset: true }),
    precision_snapshot: z.unknown(),
    public_reading_id: z.string().uuid(),
    reading_id: z.string().uuid(),
    version: z.literal("paid-reading-job-v1"),
    worker_id: z.string().min(1).max(120),
  }),
]);

const fulfillmentFailureSchema = z.object({
  accepted: z.literal(true),
  duplicate: z.boolean(),
  fulfillment_id: z.string().uuid(),
  reading_id: z.string().uuid(),
  status: z.enum(["retrying", "needs_review"]),
});

const fulfillmentLeaseRenewalSchema = z.object({
  renewed: z.literal(true),
  fulfillment_id: z.string().uuid(),
  reading_id: z.string().uuid(),
  lease_expires_at: z.string().datetime({ offset: true }),
});

const resendEventResultSchema = z.object({
  recorded: z.literal(true),
  duplicate: z.boolean(),
  matched: z.boolean(),
  delivery_status: z
    .enum([
      "sent",
      "failed",
      "delivered",
      "bounced",
      "complained",
      "suppressed",
    ])
    .optional(),
});

export class PaidReadingDatabaseError extends Error {
  readonly code: string;

  constructor(code: string) {
    super(code);
    this.name = "PaidReadingDatabaseError";
    this.code = code;
  }
}

export class RateLimitExceededError extends Error {
  readonly code = "RATE_LIMITED";

  constructor() {
    super("RATE_LIMITED");
    this.name = "RateLimitExceededError";
  }
}

export async function paidAccessHealth(
  retentionPolicyVersion: string,
  emailQueueMaximumAgeSeconds: number,
  wooReconciliationMaximumAgeSeconds: number
) {
  const data = await rpc("valley_paid_access_health", {
    p_email_queue_max_age_seconds: emailQueueMaximumAgeSeconds,
    p_retention_policy_version: retentionPolicyVersion,
    p_woo_reconciliation_max_age_seconds:
      wooReconciliationMaximumAgeSeconds,
  });
  return z
    .object({
      ok: z.literal(true),
      email_attention_count: z.literal(0),
      email_due_count: z.literal(0),
      email_health_semantics: z.literal("provider-aware-v1"),
      email_queue_ok: z.literal(true),
      provider_confirmation_due_count: z.literal(0),
      reconciliation_ok: z.literal(true),
      retention_ok: z.literal(true),
      retention_policy_version: z.literal(retentionPolicyVersion),
      schema_version: z.literal("paid-reading-delivery-v2"),
      woocommerce_accepted_count: z.number().int().nonnegative(),
      woocommerce_delivery_tracking: z.literal("acceptance-only"),
    })
    .parse(data);
}

export async function takeRateLimit({
  keyHash,
  maxRequests,
  scope,
  windowSeconds,
}: {
  keyHash: string;
  maxRequests: number;
  scope: string;
  windowSeconds: number;
}) {
  const data = await rpc("valley_take_rate_limit", {
    p_key_hash: keyHash,
    p_max_requests: maxRequests,
    p_scope: scope,
    p_window_seconds: windowSeconds,
  });
  if (data !== true) throw new RateLimitExceededError();
}

export async function recordWooCommerceEvent(input: {
  deliveryId: string;
  errorCode?: string;
  orderId: string;
  payloadHash: string;
  processingStatus: "ignored" | "failed";
  topic: string;
}) {
  return rpc("valley_record_woocommerce_event", {
    p_delivery_id: input.deliveryId,
    p_error_code: input.errorCode ?? null,
    p_payload_hash: input.payloadHash,
    p_processing_status: input.processingStatus,
    p_provider_order_id: input.orderId,
    p_topic: input.topic,
  });
}

export async function processPaidWooCommerceOrder(input: {
  amountMinor: number;
  billingEmail: string;
  billingEmailConfirmationAcceptanceSource:
    | "classic-checkout-server-validation"
    | "store-api-server-validation";
  billingEmailConfirmationDigest: string;
  billingEmailConfirmedAt: string;
  candidateGrantId: string;
  checkoutTermsAcceptanceSource:
    | "classic-required-terms-checkbox"
    | "store-api-validated-checkout";
  checkoutTermsPresentedAt: string;
  checkoutTermsVersionPresented: string;
  currency: string;
  deliveryId: string;
  gatewayTransactionId: string;
  grantExpiresAt: string;
  normalizedStatus: "processing" | "completed";
  orderId: string;
  orderNumber: string;
  paidAt: string;
  payloadHash: string;
  productId: number;
  topic: string;
}) {
  const data = await rpc("valley_process_paid_woocommerce_order", {
    p_amount_minor: input.amountMinor,
    p_billing_email: input.billingEmail,
    p_billing_email_confirmation_acceptance_source:
      input.billingEmailConfirmationAcceptanceSource,
    p_billing_email_confirmation_digest:
      input.billingEmailConfirmationDigest,
    p_billing_email_confirmed_at: input.billingEmailConfirmedAt,
    p_candidate_grant_id: input.candidateGrantId,
    p_checkout_terms_acceptance_source:
      input.checkoutTermsAcceptanceSource,
    p_checkout_terms_presented_at: input.checkoutTermsPresentedAt,
    p_checkout_terms_version_presented: input.checkoutTermsVersionPresented,
    p_currency: input.currency,
    p_delivery_id: input.deliveryId,
    p_gateway_transaction_id: input.gatewayTransactionId,
    p_grant_expires_at: input.grantExpiresAt,
    p_normalized_status: input.normalizedStatus,
    p_order_number: input.orderNumber,
    p_paid_at: input.paidAt,
    p_payload_hash: input.payloadHash,
    p_product_id: input.productId,
    p_provider_order_id: input.orderId,
    p_topic: input.topic,
  });
  return paidOrderResultSchema.parse(data);
}

export async function revokePaidWooCommerceOrder(input: {
  deliveryId: string;
  eventAt: string;
  matchesExpectedProduct: boolean;
  normalizedStatus: "refunded" | "cancelled" | "failed";
  orderId: string;
  payloadHash: string;
  topic: string;
}) {
  const data = await rpc("valley_revoke_paid_woocommerce_order", {
    p_delivery_id: input.deliveryId,
    p_event_at: input.eventAt,
    p_matches_expected_product: input.matchesExpectedProduct,
    p_normalized_status: input.normalizedStatus,
    p_payload_hash: input.payloadHash,
    p_provider_order_id: input.orderId,
    p_topic: input.topic,
  });
  return revokedOrderResultSchema.parse(data);
}

export async function beginWooCommerceReconciliation(input: {
  leaseSeconds: number;
  lookbackSeconds: number;
  requestId: string;
  windowLagSeconds: number;
}) {
  const data = await rpc("valley_begin_woocommerce_reconciliation", {
    p_lease_seconds: input.leaseSeconds,
    p_lookback_seconds: input.lookbackSeconds,
    p_request_id: input.requestId,
    p_window_lag_seconds: input.windowLagSeconds,
  });
  return wooCommerceReconciliationLeaseSchema.parse(data);
}

export async function finishWooCommerceReconciliation(input: {
  failedOrders: number;
  ignoredOrders: number;
  nextPage: number;
  paidOrders: number;
  requestId: string;
  revokedOrders: number;
  runId: string;
  scannedOrders: number;
  windowComplete: boolean;
}) {
  const data = await rpc("valley_finish_woocommerce_reconciliation", {
    p_failed_orders: input.failedOrders,
    p_ignored_orders: input.ignoredOrders,
    p_next_page: input.nextPage,
    p_paid_orders: input.paidOrders,
    p_request_id: input.requestId,
    p_revoked_orders: input.revokedOrders,
    p_run_id: input.runId,
    p_scanned_orders: input.scannedOrders,
    p_window_complete: input.windowComplete,
  });
  if (data !== true) {
    throw new PaidReadingDatabaseError(
      "WOOCOMMERCE_RECONCILIATION_NOT_FINISHED"
    );
  }
}

export async function failWooCommerceReconciliation(input: {
  errorCode: string;
  requestId: string;
  runId: string;
}) {
  const data = await rpc("valley_fail_woocommerce_reconciliation", {
    p_error_code: input.errorCode,
    p_request_id: input.requestId,
    p_run_id: input.runId,
  });
  if (data !== true) {
    throw new PaidReadingDatabaseError(
      "WOOCOMMERCE_RECONCILIATION_NOT_FAILED"
    );
  }
}

export async function setAccessGrantTokenHash(grantId: string, tokenHash: string) {
  const data = await rpc("valley_set_access_grant_token_hash", {
    p_grant_id: grantId,
    p_token_hash: tokenHash,
  });
  if (data !== true) throw new PaidReadingDatabaseError("ACCESS_GRANT_HASH_NOT_STORED");
}

export async function getPaidReading(input: {
  expiresAt: string;
  grantId: string;
  tokenHash: string;
}) {
  const data = await rpc("valley_get_paid_reading", {
    p_expires_at: input.expiresAt,
    p_grant_id: input.grantId,
    p_token_hash: input.tokenHash,
  });
  return readingLookupSchema.parse(data);
}

export async function saveIntakeDraft(input: {
  draft: unknown;
  expiresAt: string;
  grantId: string;
  tokenHash: string;
}) {
  const data = await rpc("valley_save_reading_intake_draft", {
    p_draft_payload: input.draft,
    p_expires_at: input.expiresAt,
    p_grant_id: input.grantId,
    p_token_hash: input.tokenHash,
  });
  return z
    .object({
      reading_status: z.literal("intake_in_progress"),
      saved: z.literal(true),
    })
    .parse(data);
}

export async function submitIntake(input: {
  consentAcceptedAt: string;
  consentVersion: string;
  expiresAt: string;
  finalPayload: unknown;
  grantId: string;
  intakeVersion: string;
  precisionSnapshot: unknown;
  tokenHash: string;
}) {
  const data = await rpc("valley_submit_reading_intake", {
    p_expires_at: input.expiresAt,
    p_final_payload: input.finalPayload,
    p_generation_consent_accepted_at: input.consentAcceptedAt,
    p_generation_consent_version: input.consentVersion,
    p_grant_id: input.grantId,
    p_intake_version: input.intakeVersion,
    p_precision_snapshot: input.precisionSnapshot,
    p_token_hash: input.tokenHash,
  });
  return submitResultSchema.parse(data);
}

export async function claimReadingFulfillment(input: {
  leaseSeconds: number;
  requestId: string;
  workerId: string;
}) {
  const data = await rpc("valley_claim_reading_fulfillment", {
    p_lease_seconds: input.leaseSeconds,
    p_request_id: input.requestId,
    p_worker_id: input.workerId,
  });
  return fulfillmentClaimSchema.parse(data);
}

export async function failReadingFulfillment(input: {
  attemptCount: number;
  errorCode: string;
  fulfillmentId: string;
  readingId: string;
  retryable: boolean;
  workerId: string;
}) {
  const data = await rpc("valley_fail_reading_fulfillment", {
    p_attempt_count: input.attemptCount,
    p_error_code: input.errorCode,
    p_fulfillment_id: input.fulfillmentId,
    p_reading_id: input.readingId,
    p_retryable: input.retryable,
    p_worker_id: input.workerId,
  });
  return fulfillmentFailureSchema.parse(data);
}

export async function renewReadingFulfillmentLease(input: {
  attemptCount: number;
  fulfillmentId: string;
  leaseSeconds: number;
  readingId: string;
  workerId: string;
}) {
  const data = await rpc("valley_renew_reading_fulfillment_lease", {
    p_attempt_count: input.attemptCount,
    p_fulfillment_id: input.fulfillmentId,
    p_lease_seconds: input.leaseSeconds,
    p_reading_id: input.readingId,
    p_worker_id: input.workerId,
  });
  return fulfillmentLeaseRenewalSchema.parse(data);
}

export async function recordResendEmailEvent(input: {
  eventAt: string;
  eventId: string;
  eventType:
    | "email.sent"
    | "email.delivered"
    | "email.delivery_delayed"
    | "email.failed"
    | "email.bounced"
    | "email.complained"
    | "email.suppressed";
  payloadHash: string;
  providerMessageId: string;
}) {
  const data = await rpc("valley_record_resend_email_event", {
    p_event_at: input.eventAt,
    p_event_id: input.eventId,
    p_event_type: input.eventType,
    p_payload_hash: input.payloadHash,
    p_provider_message_id: input.providerMessageId,
  });
  return resendEventResultSchema.parse(data);
}

export async function claimEmailDelivery(input: {
  grantId: string;
  messageKind: "intake_invitation" | "result_ready" | "access_recovery";
  provider: "resend" | "woocommerce";
  providerRequestHash: string;
  readingId: string;
  recipientHash: string;
  templateVersion: string;
}) {
  const data = await rpc("valley_claim_email_delivery", {
    p_access_grant_id: input.grantId,
    p_message_kind: input.messageKind,
    p_provider: input.provider,
    p_provider_request_hash: input.providerRequestHash,
    p_reading_id: input.readingId,
    p_recipient_hash: input.recipientHash,
    p_template_version: input.templateVersion,
  });
  return emailClaimSchema.parse(data);
}

export async function getEmailCommerceSnapshot(readingId: string) {
  const data = await rpc("valley_get_email_commerce_snapshot", {
    p_reading_id: readingId,
  });
  return emailCommerceSnapshotSchema.parse(data);
}

export async function recoverPaidReading(input: {
  billingEmail: string;
  candidateGrantExpiresAt: string;
  candidateGrantId: string;
  orderNumber: string;
  recipientHash: string;
  recoveryTemplateVersion: string;
}) {
  const data = await rpc("valley_recover_paid_reading", {
    p_billing_email: input.billingEmail,
    p_candidate_grant_expires_at: input.candidateGrantExpiresAt,
    p_candidate_grant_id: input.candidateGrantId,
    p_order_number: input.orderNumber,
    p_recipient_hash: input.recipientHash,
    p_recovery_template_version: input.recoveryTemplateVersion,
  });
  return recoveryResultSchema.parse(data);
}

export async function finishEmailDelivery(input: {
  accessGrantId: string;
  attemptCount: number;
  deliveryId: string;
  errorCode?: string;
  providerMessageId?: string;
  provider: "resend" | "woocommerce";
  status: "sent" | "failed";
}) {
  return rpc("valley_finish_email_delivery", {
    p_access_grant_id: input.accessGrantId,
    p_attempt_count: input.attemptCount,
    p_delivery_id: input.deliveryId,
    p_error_code: input.errorCode ?? null,
    p_provider: input.provider,
    p_provider_message_id: input.providerMessageId ?? null,
    p_status: input.status,
  });
}

export async function getEmailReconciliationCandidates(input: {
  intakeTemplateVersion: string;
  limit: number;
  resultTemplateVersion: string;
}) {
  const data = await rpc("valley_email_reconciliation_candidates", {
    p_intake_template_version: input.intakeTemplateVersion,
    p_limit: input.limit,
    p_result_template_version: input.resultTemplateVersion,
  });
  return z.array(emailReconciliationCandidateSchema).parse(data);
}

export async function storeReadingResult(input: {
  attemptCount: number;
  candidateGrantExpiresAt: string;
  candidateGrantId: string;
  contractVersion: string;
  fulfillmentId: string;
  readingId: string;
  resultHash: string;
  resultPayload: unknown;
  runtimeVersion: string;
  sourceFingerprints: unknown;
  workerId: string;
}) {
  const data = await rpc("valley_store_reading_result", {
    p_attempt_count: input.attemptCount,
    p_candidate_grant_expires_at: input.candidateGrantExpiresAt,
    p_candidate_grant_id: input.candidateGrantId,
    p_contract_version: input.contractVersion,
    p_fulfillment_id: input.fulfillmentId,
    p_reading_id: input.readingId,
    p_result_hash: input.resultHash,
    p_result_payload: input.resultPayload,
    p_runtime_version: input.runtimeVersion,
    p_source_fingerprints: input.sourceFingerprints,
    p_worker_id: input.workerId,
  });
  return storedResultSchema.parse(data);
}

async function rpc(name: string, parameters: Record<string, unknown>) {
  const { data, error } = await getPaidReadingDatabase().rpc(name, parameters);
  if (error) throw databaseError(error.message);
  return data;
}

function databaseError(message: string) {
  const knownCodes = [
    "READING_LINK_UNAVAILABLE",
    "INTAKE_LOCKED",
    "INTEGRATION_DELIVERY_ID_CONFLICT",
    "INVALID_READING_RECOVERY_REQUEST",
    "ORDER_NOT_PAID",
    "ORDER_ACCESS_REVOKED",
    "ORDER_TERMS_PRESENTATION_INVALID",
    "INVALID_BILLING_EMAIL",
    "ACCESS_GRANT_HASH_MISMATCH",
    "FULFILLMENT_NOT_FOUND",
    "FULFILLMENT_INTAKE_NOT_FOUND",
    "INVALID_WORKER_FAILURE",
    "WORKER_CLAIM_REQUEST_CONFLICT",
    "FULFILLMENT_NOT_ACCEPTING_RESULT",
    "FULFILLMENT_LEASE_MISMATCH",
    "READING_ACCESS_REVOKED",
    "RESULT_ALREADY_STORED",
  ];
  const code = knownCodes.find((candidate) => message.includes(candidate)) ?? "DATABASE_OPERATION_FAILED";
  return new PaidReadingDatabaseError(code);
}
