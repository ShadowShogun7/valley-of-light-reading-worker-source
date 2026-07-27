import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";

const migrationPath = path.resolve(
  process.cwd(),
  "../../supabase/migrations/20260726170000_add_paid_reading_delivery.sql"
);

test("paid-reading migration contains private state and one-intake invariants", async () => {
  const sql = await readFile(migrationPath, "utf8");
  for (const requiredFragment of [
    "create schema if not exists private",
    "create table private.integration_events",
    "create table private.woocommerce_reconciliation_runs",
    "create table private.woocommerce_reconciliation_state",
    "create table private.commerce_order_tombstones",
    "create table private.commerce_orders",
    "create table private.reading_intakes",
    "create table private.reading_access_grants",
    "create table private.fulfillments",
    "create table private.reading_results",
    "create table private.email_provider_events",
    "create table private.email_recipient_suppressions",
    "create table private.reading_privacy_actions",
    "create table private.reading_retention_policies",
    "create or replace function private.enforce_retention_policy_immutability",
    "create trigger reading_retention_policies_immutable_after_approval",
    "'APPROVED_RETENTION_POLICY_IMMUTABLE'",
    "policy_snapshot jsonb not null",
    "incomplete_after is not null",
    "delivered_after is not null",
    "revoked_after is not null",
    "create or replace function private.valley_execute_reading_privacy_action",
    "create or replace function private.valley_clear_email_recipient_suppression",
    "create or replace function private.valley_correct_reading_billing_email",
    "'CONTACT_CORRECTION_UNSUPPORTED'",
    "create or replace function private.active_privacy_action_for_reading",
    "create or replace function public.valley_submit_reading_intake",
    "create or replace function public.valley_get_email_commerce_snapshot",
    "'amount_minor', commerce_order.amount_minor",
    "'checkout_terms_version_presented'",
    "'billing_email_confirmation_digest'",
    "create or replace function public.valley_begin_woocommerce_reconciliation",
    "create or replace function public.valley_finish_woocommerce_reconciliation",
    "create or replace function public.valley_fail_woocommerce_reconciliation",
    "create or replace function public.valley_claim_reading_fulfillment",
    "create or replace function public.valley_fail_reading_fulfillment",
    "create or replace function public.valley_renew_reading_fulfillment_lease",
    "create or replace function public.valley_record_resend_email_event",
    "create or replace function public.valley_email_reconciliation_candidates",
    "create or replace function public.valley_recover_paid_reading",
    "'provider_order_id', v_commerce_order.provider_order_id",
    "checkout_terms_acceptance_source text not null",
    "billing_email_confirmation_digest text not null",
    "billing_email_confirmation_acceptance_source text not null",
    "p_checkout_terms_acceptance_source text",
    "p_billing_email_confirmation_digest text",
    "raise exception 'ORDER_TERMS_EVIDENCE_CONFLICT'",
    "provider_request_hash text",
    "p_provider_request_hash text",
    "'recipient_suppressed'",
    "'RESEND_SEND_FAILED'",
    "'WOOCOMMERCE_EMAIL_SEND_FAILED'",
    "check (provider in ('resend', 'woocommerce'))",
    "provider <> 'woocommerce'",
    "status not in ('delivered', 'bounced', 'complained')",
    "provider = 'resend'\n            and status = 'sent'",
    "'email_health_semantics', 'provider-aware-v1'",
    "'woocommerce_delivery_tracking', 'acceptance-only'",
    "p_provider text",
    "suppression.cleared_at is not null",
    "v_delivery.last_error_code = 'RESEND_EMAIL_SUPPRESSED'",
    "email_recipient_suppressions_one_active",
    "p_limit is null",
    "'RETENTION_NO_LONGER_DUE'",
    "create or replace function private.assert_integration_event_replay",
    "and attempt_count = p_attempt_count",
    "'analysis_datetime', reading.intake_submitted_at",
    "'analysis_timezone', 'Asia/Taipei'",
    "raise exception 'FULFILLMENT_LEASE_MISMATCH'",
    "p_candidate_grant_expires_at",
    "create or replace function public.valley_revoke_paid_woocommerce_order",
    "date_trunc('second', p_grant_expires_at)",
    "raise exception 'INTAKE_LOCKED'",
    "raise exception 'PRIVACY_ACTION_REQUIRED'",
    "result_hash = null",
    "next_attempt_at",
    "fulfillment.next_attempt_at <= now()",
    "when v_next_status = 'retrying' then",
    "'retry_exhausted'",
    "delete from private.worker_claim_requests",
    "unique (provider, order_number)",
    "create trigger reading_results_immutable_update",
    "set revoked_at = coalesce(revoked_at, p_event_at, now())",
    "ORDER_REFUND_WITHOUT_ENTITLEMENT",
    "p_matches_expected_product boolean",
    "'grant_rotated', v_grant_rotated",
    "when p_window_complete and p_failed_orders = 0 then scan_window_end",
    "when p_failed_orders > 0 then next_page",
    "when status = 'erased' then 'erased'",
    "grant execute on function public.valley_get_paid_reading",
    "grant execute on function public.valley_get_email_commerce_snapshot",
    "grant execute on function public.valley_claim_reading_fulfillment",
    "grant execute on function public.valley_fail_reading_fulfillment",
    "grant execute on function public.valley_renew_reading_fulfillment_lease",
    "grant execute on function public.valley_record_resend_email_event",
    "grant execute on function public.valley_email_reconciliation_candidates",
    "grant execute on function public.valley_recover_paid_reading",
    "grant execute on function public.valley_revoke_paid_woocommerce_order",
    "grant execute on function public.valley_begin_woocommerce_reconciliation",
    "grant execute on function public.valley_finish_woocommerce_reconciliation",
    "grant execute on function public.valley_fail_woocommerce_reconciliation",
  ]) {
    assert.equal(sql.includes(requiredFragment), true, requiredFragment);
  }
});

test("content erasure stays private and cannot be called with the app service role", async () => {
  const sql = await readFile(migrationPath, "utf8");
  assert.match(
    sql,
    /revoke all on function private\.valley_execute_reading_privacy_action\(uuid\) from public, anon, authenticated, service_role/
  );
  assert.doesNotMatch(
    sql,
    /grant execute on function private\.valley_execute_reading_privacy_action/
  );
});

test("access grant schema stores a hash but no raw capability token", async () => {
  const sql = await readFile(migrationPath, "utf8");
  const grantTable = sql.slice(
    sql.indexOf("create table private.reading_access_grants"),
    sql.indexOf("create unique index reading_access_grants_one_active_per_reading")
  );
  assert.match(grantTable, /token_hash text/);
  assert.doesNotMatch(grantTable, /raw_token|token_value|access_url/);
});
