-- Private, accountless paid-reading delivery foundation.
--
-- This migration is intentionally not applied automatically. It keeps customer,
-- order, intake, access, email, and result records in a non-exposed schema.
-- The Vercel app reaches the data only through the service-role-only RPCs below.

create schema if not exists private;

revoke all on schema private from public, anon, authenticated;

create table private.integration_events (
  id uuid primary key default extensions.gen_random_uuid(),
  source text not null,
  delivery_id text not null,
  topic text not null,
  payload_hash text not null check (payload_hash ~ '^[0-9a-f]{64}$'),
  signature_verified boolean not null default false,
  provider_order_id text,
  processing_status text not null default 'received'
    check (processing_status in ('received', 'processed', 'ignored', 'failed')),
  error_code text,
  received_at timestamptz not null default now(),
  processed_at timestamptz,
  unique (source, delivery_id)
);

create table private.woocommerce_reconciliation_runs (
  id uuid primary key default extensions.gen_random_uuid(),
  request_id uuid not null unique,
  window_start timestamptz not null,
  window_end timestamptz not null,
  page integer not null check (page > 0),
  status text not null default 'running'
    check (status in ('running', 'completed', 'completed_with_errors', 'failed')),
  scanned_orders integer not null default 0 check (scanned_orders >= 0),
  paid_orders integer not null default 0 check (paid_orders >= 0),
  revoked_orders integer not null default 0 check (revoked_orders >= 0),
  ignored_orders integer not null default 0 check (ignored_orders >= 0),
  failed_orders integer not null default 0 check (failed_orders >= 0),
  error_code text,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  check (window_start < window_end)
);

create table private.woocommerce_reconciliation_state (
  source text primary key check (source = 'woocommerce'),
  high_water_modified_at timestamptz,
  scan_window_start timestamptz,
  scan_window_end timestamptz,
  next_page integer not null default 1 check (next_page > 0),
  active_run_id uuid references private.woocommerce_reconciliation_runs(id)
    on delete restrict,
  lease_owner uuid,
  lease_expires_at timestamptz,
  last_attempt_at timestamptz,
  last_clean_success_at timestamptz,
  last_failure_at timestamptz,
  last_error_code text,
  consecutive_failures integer not null default 0
    check (consecutive_failures >= 0),
  updated_at timestamptz not null default now(),
  check (
    (
      scan_window_start is null
      and scan_window_end is null
      and next_page = 1
    )
    or (
      scan_window_start is not null
      and scan_window_end is not null
      and scan_window_start < scan_window_end
    )
  ),
  check (
    (
      active_run_id is null
      and lease_owner is null
      and lease_expires_at is null
    )
    or (
      active_run_id is not null
      and lease_owner is not null
      and lease_expires_at is not null
    )
  )
);

insert into private.woocommerce_reconciliation_state (source)
values ('woocommerce')
on conflict (source) do nothing;

create table private.commerce_order_tombstones (
  provider text not null,
  provider_order_id text not null,
  normalized_status text not null check (normalized_status = 'refunded'),
  delivery_id text not null,
  payload_hash text not null check (payload_hash ~ '^[0-9a-f]{64}$'),
  event_at timestamptz not null,
  created_at timestamptz not null default now(),
  primary key (provider, provider_order_id)
);

create table private.readings (
  id uuid primary key default extensions.gen_random_uuid(),
  public_id uuid not null default extensions.gen_random_uuid() unique,
  status text not null default 'awaiting_intake'
    check (
      status in (
        'awaiting_intake',
        'intake_in_progress',
        'intake_submitted',
        'queued',
        'generating',
        'retrying',
        'needs_review',
        'ready',
        'delivered',
        'refunded',
        'revoked',
        'erased'
      )
  ),
  checkout_terms_version_presented text not null,
  checkout_terms_acceptance_source text not null
    check (
      checkout_terms_acceptance_source in (
        'classic-required-terms-checkbox',
        'store-api-validated-checkout'
      )
    ),
  checkout_terms_presented_at timestamptz not null,
  billing_email_confirmation_digest text not null
    check (billing_email_confirmation_digest ~ '^[0-9a-f]{64}$'),
  billing_email_confirmed_at timestamptz not null,
  billing_email_confirmation_acceptance_source text not null
    check (
      billing_email_confirmation_acceptance_source in (
        'classic-checkout-server-validation',
        'store-api-server-validation'
      )
    ),
  intake_started_at timestamptz,
  intake_submitted_at timestamptz,
  personal_data_erased_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (
    (status = 'erased' and personal_data_erased_at is not null)
    or (status <> 'erased' and personal_data_erased_at is null)
  )
);

create table private.commerce_orders (
  id uuid primary key default extensions.gen_random_uuid(),
  provider text not null default 'woocommerce',
  provider_order_id text not null,
  order_number text not null,
  reading_id uuid not null unique references private.readings(id) on delete restrict,
  product_id bigint not null,
  amount_minor bigint not null check (amount_minor >= 0),
  currency text not null check (currency ~ '^[A-Z]{3}$'),
  billing_email text not null check (billing_email = lower(billing_email)),
  normalized_status text not null
    check (normalized_status in ('processing', 'completed', 'refunded', 'cancelled', 'failed')),
  gateway_transaction_id text,
  paid_at timestamptz not null,
  refunded_at timestamptz,
  personal_data_erased_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (provider, provider_order_id),
  unique (provider, order_number)
);

create table private.reading_intakes (
  reading_id uuid primary key references private.readings(id) on delete restrict,
  intake_version text,
  draft_payload jsonb not null default '{}'::jsonb,
  final_payload jsonb,
  precision_snapshot jsonb,
  generation_consent_version text,
  generation_consent_accepted_at timestamptz,
  submitted_at timestamptz,
  erased_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (
    (
      erased_at is not null
      and draft_payload = '{}'::jsonb
      and final_payload is null
      and precision_snapshot is null
    )
    or (
      erased_at is null
      and (
        (submitted_at is null and final_payload is null)
        or (
          submitted_at is not null
          and final_payload is not null
          and intake_version is not null
          and generation_consent_version is not null
          and generation_consent_accepted_at is not null
        )
      )
    )
  )
);

create table private.reading_access_grants (
  id uuid primary key,
  reading_id uuid not null references private.readings(id) on delete restrict,
  purpose text not null default 'intake_and_result'
    check (purpose = 'intake_and_result'),
  token_version integer not null default 1 check (token_version > 0),
  token_hash text unique check (token_hash is null or token_hash ~ '^[0-9a-f]{64}$'),
  expires_at timestamptz not null,
  last_used_at timestamptz,
  revoked_at timestamptz,
  created_at timestamptz not null default now()
);

create unique index reading_access_grants_one_active_per_reading
  on private.reading_access_grants(reading_id)
  where revoked_at is null;

create table private.fulfillments (
  id uuid primary key default extensions.gen_random_uuid(),
  reading_id uuid not null unique references private.readings(id) on delete restrict,
  commerce_order_id uuid not null unique references private.commerce_orders(id) on delete restrict,
  status text not null default 'queued'
    check (status in ('queued', 'generating', 'retrying', 'needs_review', 'ready', 'delivered', 'failed', 'revoked')),
  attempt_count integer not null default 0 check (attempt_count >= 0),
  last_error_code text,
  runtime_version text,
  result_contract_version text,
  lease_owner text,
  lease_expires_at timestamptz,
  next_attempt_at timestamptz,
  started_at timestamptz,
  ready_at timestamptz,
  delivered_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (
    (status = 'retrying' and next_attempt_at is not null)
    or (status <> 'retrying' and next_attempt_at is null)
  )
);

create table private.reading_results (
  id uuid primary key default extensions.gen_random_uuid(),
  reading_id uuid not null references private.readings(id) on delete restrict,
  result_version integer not null default 1 check (result_version > 0),
  contract_version text not null,
  result_payload jsonb not null,
  result_hash text check (
    result_hash is null or result_hash ~ '^[0-9a-f]{64}$'
  ),
  source_fingerprints jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  revoked_at timestamptz,
  erased_at timestamptz,
  check (
    (
      erased_at is null
      and result_hash is not null
    )
    or (
      erased_at is not null
      and result_payload = '{}'::jsonb
      and result_hash is null
      and source_fingerprints = '{}'::jsonb
      and revoked_at is not null
    )
  ),
  unique (reading_id, result_version),
  unique (reading_id, result_hash)
);

create table private.email_deliveries (
  id uuid primary key default extensions.gen_random_uuid(),
  reading_id uuid not null references private.readings(id) on delete restrict,
  access_grant_id uuid not null references private.reading_access_grants(id) on delete restrict,
  message_kind text not null
    check (message_kind in ('intake_invitation', 'result_ready', 'access_recovery')),
  template_version text not null,
  provider text not null default 'woocommerce'
    check (provider in ('resend', 'woocommerce')),
  provider_message_id text,
  recipient_hash text not null check (recipient_hash ~ '^[0-9a-f]{64}$'),
  status text not null default 'pending'
    check (status in ('pending', 'sending', 'sent', 'failed', 'delivered', 'bounced', 'complained', 'suppressed')),
  attempt_count integer not null default 0 check (attempt_count >= 0),
  provider_generation integer not null default 1
    check (provider_generation > 0),
  provider_request_hash text check (
    provider_request_hash is null
    or provider_request_hash ~ '^[0-9a-f]{64}$'
  ),
  sending_started_at timestamptz,
  next_attempt_at timestamptz,
  sent_at timestamptz,
  delivered_at timestamptz,
  bounced_at timestamptz,
  complained_at timestamptz,
  last_error_code text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (
    provider <> 'woocommerce'
    or (
      status not in ('delivered', 'bounced', 'complained')
      and delivered_at is null
      and bounced_at is null
      and complained_at is null
    )
  ),
  check (
    provider_request_hash is not null
    or status in ('pending', 'suppressed')
  ),
  unique (reading_id, message_kind, template_version)
);

create table private.email_provider_messages (
  id uuid primary key default extensions.gen_random_uuid(),
  email_delivery_id uuid not null
    references private.email_deliveries(id) on delete restrict,
  provider text not null
    check (provider in ('resend', 'woocommerce')),
  provider_message_id text not null,
  provider_generation integer not null check (provider_generation > 0),
  recipient_hash text not null check (recipient_hash ~ '^[0-9a-f]{64}$'),
  bound_at timestamptz not null default now(),
  unique (provider, provider_message_id),
  unique (email_delivery_id, provider_generation)
);

create table private.email_provider_events (
  id uuid primary key default extensions.gen_random_uuid(),
  provider text not null default 'resend' check (provider = 'resend'),
  event_id text not null,
  event_type text not null
    check (
      event_type in (
        'email.sent',
        'email.delivered',
        'email.delivery_delayed',
        'email.failed',
        'email.bounced',
        'email.complained',
        'email.suppressed'
      )
    ),
  provider_message_id text not null,
  payload_hash text not null check (payload_hash ~ '^[0-9a-f]{64}$'),
  signature_verified boolean not null default false,
  processing_status text not null default 'received'
    check (processing_status in ('received', 'processed')),
  event_at timestamptz not null,
  received_at timestamptz not null default now(),
  processed_at timestamptz,
  unique (provider, event_id)
);

create table private.email_recipient_suppressions (
  id uuid primary key default extensions.gen_random_uuid(),
  recipient_hash text not null check (recipient_hash ~ '^[0-9a-f]{64}$'),
  suppression_kind text not null
    check (suppression_kind in ('bounced', 'complained', 'suppressed')),
  source_email_delivery_id uuid not null
    references private.email_deliveries(id) on delete restrict,
  source_email_event_id uuid not null
    references private.email_provider_events(id) on delete restrict,
  created_at timestamptz not null default now(),
  cleared_at timestamptz,
  cleared_by_hash text check (
    cleared_by_hash is null or cleared_by_hash ~ '^[0-9a-f]{64}$'
  ),
  clear_reason_code text check (
    clear_reason_code is null or clear_reason_code ~ '^[A-Z0-9_]{3,80}$'
  ),
  check (
    (
      cleared_at is null
      and cleared_by_hash is null
      and clear_reason_code is null
    )
    or (
      cleared_at is not null
      and cleared_by_hash is not null
      and clear_reason_code is not null
    )
  )
);

create unique index email_recipient_suppressions_one_active
  on private.email_recipient_suppressions(recipient_hash)
  where cleared_at is null;

create table private.request_rate_limits (
  scope text not null,
  key_hash text not null check (key_hash ~ '^[0-9a-f]{64}$'),
  bucket_start timestamptz not null,
  request_count integer not null default 1 check (request_count > 0),
  expires_at timestamptz not null,
  primary key (scope, key_hash, bucket_start)
);

create table private.worker_claim_requests (
  request_id uuid primary key,
  worker_id text not null,
  fulfillment_id uuid references private.fulfillments(id) on delete restrict,
  attempt_count integer,
  lease_expires_at timestamptz,
  created_at timestamptz not null default now()
);

create table private.reading_privacy_actions (
  id uuid primary key default extensions.gen_random_uuid(),
  reading_id uuid not null references private.readings(id) on delete restrict,
  commerce_order_id uuid not null references private.commerce_orders(id) on delete restrict,
  idempotency_key text not null unique
    check (idempotency_key ~ '^[A-Za-z0-9._:-]{8,160}$'),
  action_kind text not null
    check (action_kind in ('customer_request', 'scheduled_retention', 'operator')),
  actor_hash text not null check (actor_hash ~ '^[0-9a-f]{64}$'),
  reason_code text not null check (reason_code ~ '^[A-Z0-9_]{3,80}$'),
  policy_version text,
  status text not null default 'pending'
    check (status in ('pending', 'running', 'completed', 'skipped', 'failed')),
  previous_reading_status text,
  erased_components text[] not null default '{}'::text[],
  intake_rows_scrubbed integer not null default 0,
  result_rows_scrubbed integer not null default 0,
  error_code text,
  requested_at timestamptz not null default now(),
  started_at timestamptz,
  completed_at timestamptz
);

create table private.reading_contact_corrections (
  id uuid primary key default extensions.gen_random_uuid(),
  commerce_order_id uuid not null
    references private.commerce_orders(id) on delete restrict,
  reading_id uuid not null references private.readings(id) on delete restrict,
  idempotency_key text not null unique
    check (idempotency_key ~ '^[A-Za-z0-9._:-]{8,160}$'),
  previous_email_hash text not null
    check (previous_email_hash ~ '^[0-9a-f]{64}$'),
  corrected_email_hash text not null
    check (corrected_email_hash ~ '^[0-9a-f]{64}$'),
  actor_hash text not null check (actor_hash ~ '^[0-9a-f]{64}$'),
  verification_reference_hash text not null
    check (verification_reference_hash ~ '^[0-9a-f]{64}$'),
  reason_code text not null check (reason_code ~ '^[A-Z0-9_]{3,80}$'),
  replacement_grant_id uuid not null
    references private.reading_access_grants(id) on delete restrict,
  replacement_grant_expires_at timestamptz not null,
  recovery_template_version text not null
    check (
      recovery_template_version ~
        '^paid-access-recovery-v1:[0-9a-f-]{36}$'
    ),
  completed_at timestamptz not null default now(),
  check (previous_email_hash <> corrected_email_hash)
);

create table private.reading_retention_policies (
  version text primary key check (version ~ '^[A-Za-z0-9._:-]{3,80}$'),
  enabled boolean not null default false,
  anchor_version text,
  run_cadence interval,
  incomplete_after interval,
  delivered_after interval,
  revoked_after interval,
  approved_by_hash text check (
    approved_by_hash is null or approved_by_hash ~ '^[0-9a-f]{64}$'
  ),
  approved_at timestamptz,
  created_at timestamptz not null default now(),
  check (
    (approved_by_hash is null and approved_at is null)
    or (approved_by_hash is not null and approved_at is not null)
  ),
  check (
    not enabled
    or (
      anchor_version = 'reading-retention-anchor-v1'
      and run_cadence is not null
      and run_cadence >= interval '5 minutes'
      and run_cadence <= interval '1 day'
      and incomplete_after is not null
      and incomplete_after > interval '0 seconds'
      and delivered_after is not null
      and delivered_after > interval '0 seconds'
      and revoked_after is not null
      and revoked_after > interval '0 seconds'
      and approved_by_hash is not null
      and approved_at is not null
    )
  )
);

create or replace function private.enforce_retention_policy_immutability()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if tg_op = 'DELETE' then
    if old.enabled
      or old.approved_by_hash is not null
      or old.approved_at is not null then
      raise exception 'APPROVED_RETENTION_POLICY_IMMUTABLE'
        using errcode = 'P0001';
    end if;
    return old;
  end if;

  if old.enabled
    or old.approved_by_hash is not null
    or old.approved_at is not null then
    if new.version is distinct from old.version
      or new.anchor_version is distinct from old.anchor_version
      or new.run_cadence is distinct from old.run_cadence
      or new.incomplete_after is distinct from old.incomplete_after
      or new.delivered_after is distinct from old.delivered_after
      or new.revoked_after is distinct from old.revoked_after
      or new.approved_by_hash is distinct from old.approved_by_hash
      or new.approved_at is distinct from old.approved_at
      or new.created_at is distinct from old.created_at then
      raise exception 'APPROVED_RETENTION_POLICY_IMMUTABLE'
        using errcode = 'P0001';
    end if;
  end if;

  return new;
end;
$$;

create trigger reading_retention_policies_immutable_after_approval
before update or delete on private.reading_retention_policies
for each row execute function
  private.enforce_retention_policy_immutability();

create table private.reading_retention_runs (
  id uuid primary key default extensions.gen_random_uuid(),
  policy_version text not null
    references private.reading_retention_policies(version) on delete restrict,
  actor_hash text not null check (actor_hash ~ '^[0-9a-f]{64}$'),
  policy_snapshot jsonb not null,
  status text not null default 'running'
    check (status in ('running', 'completed', 'failed')),
  scanned_readings integer not null default 0
    check (scanned_readings >= 0),
  staged_actions integer not null default 0
    check (staged_actions >= 0),
  completed_actions integer not null default 0
    check (completed_actions >= 0),
  skipped_actions integer not null default 0
    check (skipped_actions >= 0),
  failed_actions integer not null default 0
    check (failed_actions >= 0),
  overdue_remaining integer not null default 0
    check (overdue_remaining >= 0),
  error_code text,
  started_at timestamptz not null default now(),
  finished_at timestamptz
);

create table private.reading_retention_holds (
  id uuid primary key default extensions.gen_random_uuid(),
  reading_id uuid not null references private.readings(id) on delete restrict,
  reason_code text not null check (reason_code ~ '^[A-Z0-9_]{3,80}$'),
  placed_by_hash text not null check (placed_by_hash ~ '^[0-9a-f]{64}$'),
  placed_at timestamptz not null default now(),
  released_by_hash text check (
    released_by_hash is null or released_by_hash ~ '^[0-9a-f]{64}$'
  ),
  released_at timestamptz,
  check (
    (released_at is null and released_by_hash is null)
    or (released_at is not null and released_by_hash is not null)
  )
);

create unique index reading_retention_policies_one_enabled
  on private.reading_retention_policies(enabled)
  where enabled;

create unique index reading_retention_holds_one_active
  on private.reading_retention_holds(reading_id)
  where released_at is null;

create index reading_retention_runs_started_idx
  on private.reading_retention_runs(policy_version, started_at desc);

alter table private.reading_privacy_actions
  add constraint reading_privacy_actions_policy_fk
  foreign key (policy_version)
  references private.reading_retention_policies(version)
  on delete restrict,
  add constraint reading_privacy_actions_scheduled_policy_check
  check (
    action_kind <> 'scheduled_retention'
    or policy_version is not null
  );

create index integration_events_order_idx
  on private.integration_events(source, provider_order_id, received_at desc);
create index woocommerce_reconciliation_runs_started_idx
  on private.woocommerce_reconciliation_runs(started_at desc);
create index commerce_orders_email_idx
  on private.commerce_orders(billing_email);
create index readings_status_idx
  on private.readings(status, updated_at);
create index fulfillments_status_idx
  on private.fulfillments(status, updated_at);
create index email_deliveries_status_idx
  on private.email_deliveries(status, updated_at);
create index email_provider_events_message_idx
  on private.email_provider_events(provider, provider_message_id, event_at desc);
create index email_provider_messages_delivery_idx
  on private.email_provider_messages(email_delivery_id, provider_generation desc);
create index email_recipient_suppressions_created_idx
  on private.email_recipient_suppressions(created_at desc);
create index request_rate_limits_expiry_idx
  on private.request_rate_limits(expires_at);
create index worker_claim_requests_created_idx
  on private.worker_claim_requests(created_at);

create or replace function private.active_privacy_action_for_reading(
  p_reading_id uuid
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_action_id_text text;
begin
  v_action_id_text := current_setting('valley.privacy_action_id', true);
  if v_action_id_text is null
    or v_action_id_text !~ '^[0-9a-fA-F-]{36}$' then
    return false;
  end if;

  return exists (
    select 1
    from private.reading_privacy_actions
    where id = v_action_id_text::uuid
      and reading_id = p_reading_id
      and status = 'running'
  );
exception
  when invalid_text_representation then
    return false;
end;
$$;

create or replace function private.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at := now();
  return new;
end;
$$;

create trigger readings_set_updated_at
before update on private.readings
for each row execute function private.set_updated_at();

create trigger commerce_orders_set_updated_at
before update on private.commerce_orders
for each row execute function private.set_updated_at();

create trigger reading_intakes_set_updated_at
before update on private.reading_intakes
for each row execute function private.set_updated_at();

create trigger fulfillments_set_updated_at
before update on private.fulfillments
for each row execute function private.set_updated_at();

create trigger email_deliveries_set_updated_at
before update on private.email_deliveries
for each row execute function private.set_updated_at();

create or replace function private.prevent_locked_intake_changes()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if old.erased_at is null and new.erased_at is not null then
    if not private.active_privacy_action_for_reading(old.reading_id) then
      raise exception 'PRIVACY_ACTION_REQUIRED' using errcode = 'P0001';
    end if;
    if new.draft_payload = '{}'::jsonb
      and new.final_payload is null
      and new.precision_snapshot is null
      and new.intake_version is not distinct from old.intake_version
      and new.generation_consent_version is not distinct from old.generation_consent_version
      and new.generation_consent_accepted_at is not distinct from old.generation_consent_accepted_at
      and new.submitted_at is not distinct from old.submitted_at
      and new.created_at = old.created_at then
      return new;
    end if;
    raise exception 'INVALID_INTAKE_ERASURE' using errcode = 'P0001';
  end if;

  if old.erased_at is not null and (
    new.reading_id is distinct from old.reading_id
    or new.intake_version is distinct from old.intake_version
    or new.draft_payload is distinct from old.draft_payload
    or new.final_payload is distinct from old.final_payload
    or new.precision_snapshot is distinct from old.precision_snapshot
    or new.generation_consent_version is distinct from old.generation_consent_version
    or new.generation_consent_accepted_at is distinct from old.generation_consent_accepted_at
    or new.submitted_at is distinct from old.submitted_at
    or new.erased_at is distinct from old.erased_at
    or new.created_at is distinct from old.created_at
  ) then
    raise exception 'PERSONAL_DATA_ERASED' using errcode = 'P0001';
  end if;
  if old.erased_at is not null then
    return new;
  end if;

  if old.submitted_at is not null and (
    new.intake_version is distinct from old.intake_version
    or new.draft_payload is distinct from old.draft_payload
    or new.final_payload is distinct from old.final_payload
    or new.precision_snapshot is distinct from old.precision_snapshot
    or new.generation_consent_version is distinct from old.generation_consent_version
    or new.generation_consent_accepted_at is distinct from old.generation_consent_accepted_at
    or new.submitted_at is distinct from old.submitted_at
  ) then
    raise exception 'INTAKE_LOCKED' using errcode = 'P0001';
  end if;
  return new;
end;
$$;

create trigger reading_intakes_lock_after_submit
before update on private.reading_intakes
for each row execute function private.prevent_locked_intake_changes();

create or replace function private.prevent_result_mutation()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if tg_op = 'UPDATE' then
    if old.revoked_at is null
      and new.revoked_at is not null
      and new.erased_at is not distinct from old.erased_at
      and new.id = old.id
      and new.reading_id = old.reading_id
      and new.result_version = old.result_version
      and new.contract_version = old.contract_version
      and new.result_payload = old.result_payload
      and new.result_hash = old.result_hash
      and new.source_fingerprints = old.source_fingerprints
      and new.created_at = old.created_at then
      return new;
    end if;

    if old.erased_at is null
      and new.erased_at is not null
      and private.active_privacy_action_for_reading(old.reading_id)
      and new.revoked_at is not null
      and new.id = old.id
      and new.reading_id = old.reading_id
      and new.result_version = old.result_version
      and new.contract_version = old.contract_version
      and new.result_payload = '{}'::jsonb
      and new.result_hash is null
      and new.source_fingerprints = '{}'::jsonb
      and new.created_at = old.created_at then
      return new;
    end if;
  end if;

  raise exception 'READING_RESULT_IMMUTABLE' using errcode = 'P0001';
end;
$$;

create trigger reading_results_immutable_update
before update on private.reading_results
for each row execute function private.prevent_result_mutation();

create trigger reading_results_immutable_delete
before delete on private.reading_results
for each row execute function private.prevent_result_mutation();

create or replace function private.authorized_reading_id(
  p_grant_id uuid,
  p_token_hash text,
  p_expires_at timestamptz
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_reading_id uuid;
begin
  select grant_row.reading_id
    into v_reading_id
  from private.reading_access_grants as grant_row
  where grant_row.id = p_grant_id
    and grant_row.token_hash = p_token_hash
    and grant_row.expires_at = p_expires_at
    and grant_row.expires_at > now()
    and grant_row.revoked_at is null;

  if v_reading_id is null then
    raise exception 'READING_LINK_UNAVAILABLE' using errcode = 'P0001';
  end if;

  return v_reading_id;
end;
$$;

create or replace function private.reading_retention_due(
  p_policy_version text
)
returns table (
  reading_id uuid,
  commerce_order_id uuid,
  retention_class text,
  due_at timestamptz
)
language sql
stable
security definer
set search_path = ''
as $$
  with policy as (
    select *
    from private.reading_retention_policies
    where version = p_policy_version
      and enabled
      and anchor_version = 'reading-retention-anchor-v1'
  ),
  classified as (
    select
      reading.id as reading_id,
      commerce_order.id as commerce_order_id,
      case
        when reading.status in (
          'awaiting_intake',
          'intake_in_progress',
          'intake_submitted',
          'queued',
          'generating',
          'retrying',
          'needs_review'
        ) then 'incomplete'
        when reading.status in ('ready', 'delivered') then 'delivered'
        when reading.status in ('refunded', 'revoked') then 'revoked'
        else null
      end as retention_class,
      case
        when reading.status in (
          'awaiting_intake',
          'intake_in_progress',
          'intake_submitted',
          'queued',
          'generating',
          'retrying',
          'needs_review'
        ) then
          greatest(
            commerce_order.paid_at,
            reading.updated_at,
            intake.updated_at
          ) + policy.incomplete_after
        when reading.status in ('ready', 'delivered') then
          coalesce(
            fulfillment.delivered_at,
            fulfillment.ready_at
          ) + policy.delivered_after
        when reading.status in ('refunded', 'revoked') then
          coalesce(
            commerce_order.refunded_at,
            reading.updated_at
          ) + policy.revoked_after
        else null
      end as due_at
    from policy
    join private.commerce_orders as commerce_order on true
    join private.readings as reading
      on reading.id = commerce_order.reading_id
    join private.reading_intakes as intake
      on intake.reading_id = reading.id
    left join private.fulfillments as fulfillment
      on fulfillment.reading_id = reading.id
    where reading.status <> 'erased'
      and not exists (
        select 1
        from private.reading_retention_holds as retention_hold
        where retention_hold.reading_id = reading.id
          and retention_hold.released_at is null
      )
  )
  select
    classified.reading_id,
    classified.commerce_order_id,
    classified.retention_class,
    classified.due_at
  from classified
  where classified.retention_class is not null
    and classified.due_at is not null
    and classified.due_at <= now()
  order by classified.due_at, classified.reading_id;
$$;

create or replace function public.valley_paid_access_health(
  p_retention_policy_version text,
  p_email_queue_max_age_seconds integer,
  p_woo_reconciliation_max_age_seconds integer
)
returns jsonb
language sql
security definer
set search_path = ''
as $$
  with email_metrics as (
    select
      count(*) filter (
        where
          (
            status = 'pending'
            and created_at <= now() - make_interval(
              secs => p_email_queue_max_age_seconds
            )
          )
          or (
            status = 'sending'
            and sending_started_at <= now() - make_interval(
              secs => p_email_queue_max_age_seconds
            )
          )
          or (
            status = 'failed'
            and next_attempt_at <= now() - make_interval(
              secs => p_email_queue_max_age_seconds
            )
          )
          or (
            provider = 'resend'
            and status = 'sent'
            and sent_at <= now() - make_interval(
              secs => p_email_queue_max_age_seconds
            )
          )
      )::integer as due_count,
      count(*) filter (
        where provider = 'resend'
          and status = 'sent'
          and sent_at <= now() - make_interval(
            secs => p_email_queue_max_age_seconds
          )
      )::integer as provider_confirmation_due_count,
      count(*) filter (
        where provider = 'woocommerce'
          and status = 'sent'
      )::integer as woocommerce_accepted_count,
      count(*) filter (
        where status = 'suppressed'
          and coalesce(last_error_code, '') not in (
              'ORDER_REFUNDED',
              'READING_CONTENT_ERASED',
              'ACCESS_GRANT_ROTATED'
          )
          and not exists (
            select 1
            from private.email_recipient_suppressions as suppression
            where suppression.source_email_delivery_id =
              email_deliveries.id
          )
      )::integer as attention_count
    from private.email_deliveries as email_deliveries
  ),
  suppression_metrics as (
    select count(*)::integer as active_count
    from private.email_recipient_suppressions as suppression
    where suppression.cleared_at is null
      and exists (
        select 1
        from private.commerce_orders as commerce_order
        join private.readings as reading
          on reading.id = commerce_order.reading_id
        where commerce_order.normalized_status in ('processing', 'completed')
          and reading.status not in ('refunded', 'revoked', 'erased')
          and suppression.recipient_hash = encode(
            extensions.digest(
              convert_to(commerce_order.billing_email, 'UTF8'),
              'sha256'
            ),
            'hex'
          )
      )
  ),
  health as (
    select
      (
        p_email_queue_max_age_seconds between 300 and 86400
        and email_metrics.due_count = 0
        and email_metrics.attention_count = 0
        and suppression_metrics.active_count = 0
      ) as email_queue_ok,
      email_metrics.due_count as email_due_count,
      email_metrics.provider_confirmation_due_count,
      email_metrics.woocommerce_accepted_count,
      (
        email_metrics.attention_count + suppression_metrics.active_count
      ) as email_attention_count,
      exists (
        select 1
        from private.reading_retention_policies as policy
        where policy.version = p_retention_policy_version
          and policy.enabled
          and policy.anchor_version = 'reading-retention-anchor-v1'
          and exists (
            select 1
            from private.reading_retention_runs as retention_run
            where retention_run.policy_version = policy.version
              and retention_run.status = 'completed'
              and retention_run.policy_snapshot = jsonb_build_object(
                'anchor_version', policy.anchor_version,
                'approved_at', policy.approved_at,
                'approved_by_hash', policy.approved_by_hash,
                'delivered_after', policy.delivered_after::text,
                'incomplete_after', policy.incomplete_after::text,
                'revoked_after', policy.revoked_after::text,
                'run_cadence', policy.run_cadence::text
              )
              and retention_run.overdue_remaining = 0
              and retention_run.finished_at >=
                now() - (policy.run_cadence * 2)
              and not exists (
                select 1
                from private.reading_retention_runs as later_failed_run
                where later_failed_run.policy_version = policy.version
                  and later_failed_run.status = 'failed'
                  and later_failed_run.started_at >
                    retention_run.started_at
              )
          )
          and not exists (
            select 1
            from private.reading_retention_due(policy.version)
          )
      ) as retention_ok,
      exists (
        select 1
        from private.woocommerce_reconciliation_state
        where source = 'woocommerce'
          and p_woo_reconciliation_max_age_seconds between 300 and 86400
          and high_water_modified_at >=
            now() - make_interval(
              secs => p_woo_reconciliation_max_age_seconds
            )
          and last_clean_success_at >=
            now() - make_interval(
              secs => p_woo_reconciliation_max_age_seconds
            )
          and (
            last_failure_at is null
            or last_clean_success_at >= last_failure_at
          )
          and not (
            active_run_id is not null
            and lease_expires_at <= now()
          )
      ) as reconciliation_ok
    from email_metrics
    cross join suppression_metrics
  )
  select jsonb_build_object(
    'ok', retention_ok and reconciliation_ok and email_queue_ok,
    'email_attention_count', email_attention_count,
    'email_due_count', email_due_count,
    'email_health_semantics', 'provider-aware-v1',
    'email_queue_ok', email_queue_ok,
    'provider_confirmation_due_count',
      provider_confirmation_due_count,
    'reconciliation_ok', reconciliation_ok,
    'retention_ok', retention_ok,
    'schema_version', 'paid-reading-delivery-v2',
    'woocommerce_accepted_count', woocommerce_accepted_count,
    'woocommerce_delivery_tracking', 'acceptance-only',
    'retention_policy_version', p_retention_policy_version
  )
  from health;
$$;

create or replace function public.valley_get_email_commerce_snapshot(
  p_reading_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_snapshot jsonb;
begin
  if p_reading_id is null then
    raise exception 'INVALID_EMAIL_COMMERCE_SNAPSHOT_REQUEST'
      using errcode = '22023';
  end if;

  select jsonb_build_object(
    'reading_id', reading.id,
    'provider_order_id', commerce_order.provider_order_id,
    'billing_email', commerce_order.billing_email,
    'product_id', commerce_order.product_id,
    'amount_minor', commerce_order.amount_minor,
    'currency', commerce_order.currency,
    'paid_at', commerce_order.paid_at,
    'checkout_terms_version_presented',
      reading.checkout_terms_version_presented,
    'checkout_terms_acceptance_source',
      reading.checkout_terms_acceptance_source,
    'checkout_terms_presented_at',
      reading.checkout_terms_presented_at,
    'billing_email_confirmation_digest',
      reading.billing_email_confirmation_digest,
    'billing_email_confirmed_at',
      reading.billing_email_confirmed_at,
    'billing_email_confirmation_acceptance_source',
      reading.billing_email_confirmation_acceptance_source
  )
    into v_snapshot
  from private.readings as reading
  join private.commerce_orders as commerce_order
    on commerce_order.reading_id = reading.id
  where reading.id = p_reading_id
    and reading.status not in ('refunded', 'revoked', 'erased')
    and commerce_order.provider = 'woocommerce'
    and commerce_order.normalized_status in ('processing', 'completed');

  if v_snapshot is null then
    raise exception 'EMAIL_COMMERCE_SNAPSHOT_UNAVAILABLE'
      using errcode = 'P0001';
  end if;

  return v_snapshot;
end;
$$;

create or replace function public.valley_begin_woocommerce_reconciliation(
  p_request_id uuid,
  p_lookback_seconds integer,
  p_window_lag_seconds integer,
  p_lease_seconds integer
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_state private.woocommerce_reconciliation_state%rowtype;
  v_run_id uuid;
  v_window_start timestamptz;
  v_window_end timestamptz;
  v_page integer;
begin
  if p_request_id is null
    or p_lookback_seconds is null
    or p_window_lag_seconds is null
    or p_lease_seconds is null
    or p_lookback_seconds < 3600
    or p_lookback_seconds > 604800
    or p_window_lag_seconds < 0
    or p_window_lag_seconds > 300
    or p_lease_seconds < 60
    or p_lease_seconds > 300 then
    raise exception 'INVALID_WOOCOMMERCE_RECONCILIATION_REQUEST'
      using errcode = '22023';
  end if;

  select * into v_state
  from private.woocommerce_reconciliation_state
  where source = 'woocommerce'
  for update;

  if not found then
    raise exception 'WOOCOMMERCE_RECONCILIATION_STATE_MISSING'
      using errcode = 'P0001';
  end if;

  if v_state.active_run_id is not null
    and v_state.lease_expires_at > now() then
    return jsonb_build_object('acquired', false);
  end if;

  if v_state.active_run_id is not null then
    update private.woocommerce_reconciliation_runs
    set
      status = 'failed',
      error_code = coalesce(error_code, 'RECONCILIATION_LEASE_EXPIRED'),
      finished_at = coalesce(finished_at, now())
    where id = v_state.active_run_id
      and status = 'running';
  end if;

  if v_state.scan_window_start is null then
    v_window_end := date_trunc(
      'second',
      now() - make_interval(secs => p_window_lag_seconds)
    );
    v_window_start := coalesce(
      v_state.high_water_modified_at -
        make_interval(secs => p_lookback_seconds),
      v_window_end - make_interval(secs => p_lookback_seconds)
    );
    v_page := 1;
  else
    v_window_start := v_state.scan_window_start;
    v_window_end := v_state.scan_window_end;
    v_page := v_state.next_page;
  end if;

  insert into private.woocommerce_reconciliation_runs (
    request_id,
    window_start,
    window_end,
    page
  )
  values (
    p_request_id,
    v_window_start,
    v_window_end,
    v_page
  )
  returning id into v_run_id;

  update private.woocommerce_reconciliation_state
  set
    scan_window_start = v_window_start,
    scan_window_end = v_window_end,
    next_page = v_page,
    active_run_id = v_run_id,
    lease_owner = p_request_id,
    lease_expires_at = now() + make_interval(secs => p_lease_seconds),
    last_attempt_at = now(),
    updated_at = now()
  where source = 'woocommerce';

  return jsonb_build_object(
    'acquired', true,
    'run_id', v_run_id,
    'window_start', v_window_start,
    'window_end', v_window_end,
    'page', v_page
  );
end;
$$;

create or replace function public.valley_finish_woocommerce_reconciliation(
  p_run_id uuid,
  p_request_id uuid,
  p_next_page integer,
  p_window_complete boolean,
  p_scanned_orders integer,
  p_paid_orders integer,
  p_revoked_orders integer,
  p_ignored_orders integer,
  p_failed_orders integer
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_state private.woocommerce_reconciliation_state%rowtype;
begin
  if p_window_complete is null
    or p_next_page is null
    or p_scanned_orders is null
    or p_paid_orders is null
    or p_revoked_orders is null
    or p_ignored_orders is null
    or p_failed_orders is null
    or p_next_page < 2
    or p_next_page > 1000000
    or p_scanned_orders < 0
    or p_scanned_orders > 25
    or p_paid_orders < 0
    or p_revoked_orders < 0
    or p_ignored_orders < 0
    or p_failed_orders < 0
    or p_paid_orders + p_revoked_orders + p_ignored_orders + p_failed_orders
      <> p_scanned_orders then
    raise exception 'INVALID_WOOCOMMERCE_RECONCILIATION_RESULT'
      using errcode = '22023';
  end if;

  select * into v_state
  from private.woocommerce_reconciliation_state
  where source = 'woocommerce'
  for update;

  if v_state.active_run_id is distinct from p_run_id
    or v_state.lease_owner is distinct from p_request_id
    or v_state.lease_expires_at <= now() then
    raise exception 'WOOCOMMERCE_RECONCILIATION_LEASE_MISMATCH'
      using errcode = 'P0001';
  end if;

  update private.woocommerce_reconciliation_runs
  set
    status = case
      when p_failed_orders > 0 then 'completed_with_errors'
      else 'completed'
    end,
    scanned_orders = p_scanned_orders,
    paid_orders = p_paid_orders,
    revoked_orders = p_revoked_orders,
    ignored_orders = p_ignored_orders,
    failed_orders = p_failed_orders,
    error_code = case
      when p_failed_orders > 0 then 'RECONCILIATION_REVIEW_REQUIRED'
      else null
    end,
    finished_at = now()
  where id = p_run_id
    and request_id = p_request_id
    and status = 'running';

  if not found then
    raise exception 'WOOCOMMERCE_RECONCILIATION_LEASE_MISMATCH'
      using errcode = 'P0001';
  end if;

  update private.woocommerce_reconciliation_state
  set
    high_water_modified_at = case
      when p_window_complete and p_failed_orders = 0 then scan_window_end
      else high_water_modified_at
    end,
    scan_window_start = case
      when p_window_complete and p_failed_orders = 0 then null
      else scan_window_start
    end,
    scan_window_end = case
      when p_window_complete and p_failed_orders = 0 then null
      else scan_window_end
    end,
    next_page = case
      when p_window_complete and p_failed_orders = 0 then 1
      when p_failed_orders > 0 then next_page
      else p_next_page
    end,
    active_run_id = null,
    lease_owner = null,
    lease_expires_at = null,
    last_clean_success_at = case
      when p_failed_orders = 0 then now()
      else last_clean_success_at
    end,
    last_failure_at = case
      when p_failed_orders > 0 then now()
      else last_failure_at
    end,
    last_error_code = case
      when p_failed_orders > 0 then 'RECONCILIATION_REVIEW_REQUIRED'
      else null
    end,
    consecutive_failures = case
      when p_failed_orders > 0 then consecutive_failures + 1
      else 0
    end,
    updated_at = now()
  where source = 'woocommerce';

  return true;
end;
$$;

create or replace function public.valley_fail_woocommerce_reconciliation(
  p_run_id uuid,
  p_request_id uuid,
  p_error_code text
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_state private.woocommerce_reconciliation_state%rowtype;
begin
  if p_error_code !~ '^[A-Z0-9_]{2,80}$' then
    raise exception 'INVALID_WOOCOMMERCE_RECONCILIATION_FAILURE'
      using errcode = '22023';
  end if;

  select * into v_state
  from private.woocommerce_reconciliation_state
  where source = 'woocommerce'
  for update;

  if v_state.active_run_id is distinct from p_run_id
    or v_state.lease_owner is distinct from p_request_id then
    raise exception 'WOOCOMMERCE_RECONCILIATION_LEASE_MISMATCH'
      using errcode = 'P0001';
  end if;

  update private.woocommerce_reconciliation_runs
  set
    status = 'failed',
    error_code = p_error_code,
    finished_at = now()
  where id = p_run_id
    and request_id = p_request_id
    and status = 'running';

  if not found then
    raise exception 'WOOCOMMERCE_RECONCILIATION_LEASE_MISMATCH'
      using errcode = 'P0001';
  end if;

  update private.woocommerce_reconciliation_state
  set
    active_run_id = null,
    lease_owner = null,
    lease_expires_at = null,
    last_failure_at = now(),
    last_error_code = p_error_code,
    consecutive_failures = consecutive_failures + 1,
    updated_at = now()
  where source = 'woocommerce';

  return true;
end;
$$;

create or replace function public.valley_take_rate_limit(
  p_scope text,
  p_key_hash text,
  p_window_seconds integer,
  p_max_requests integer
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_bucket_start timestamptz;
  v_count integer;
begin
  if p_scope is null
    or p_scope !~ '^[a-z0-9:_-]{1,80}$'
    or p_key_hash is null
    or p_key_hash !~ '^[0-9a-f]{64}$'
    or p_window_seconds is null
    or p_max_requests is null
    or p_window_seconds < 1
    or p_window_seconds > 86400
    or p_max_requests < 1
    or p_max_requests > 10000 then
    raise exception 'INVALID_RATE_LIMIT_POLICY' using errcode = '22023';
  end if;

  v_bucket_start := to_timestamp(
    floor(extract(epoch from now()) / p_window_seconds) * p_window_seconds
  );

  insert into private.request_rate_limits (
    scope,
    key_hash,
    bucket_start,
    request_count,
    expires_at
  )
  values (
    p_scope,
    p_key_hash,
    v_bucket_start,
    1,
    v_bucket_start + make_interval(secs => p_window_seconds * 2)
  )
  on conflict (scope, key_hash, bucket_start)
  do update set request_count = private.request_rate_limits.request_count + 1
  returning request_count into v_count;

  if random() < 0.01 then
    delete from private.request_rate_limits where expires_at < now();
  end if;

  return v_count <= p_max_requests;
end;
$$;

create or replace function private.assert_integration_event_replay(
  p_source text,
  p_delivery_id text,
  p_topic text,
  p_payload_hash text,
  p_provider_order_id text
)
returns void
language plpgsql
set search_path = ''
as $$
declare
  v_event private.integration_events%rowtype;
begin
  select * into v_event
  from private.integration_events
  where source = p_source
    and delivery_id = p_delivery_id;

  if not found
    or v_event.topic is distinct from p_topic
    or v_event.payload_hash is distinct from p_payload_hash
    or v_event.provider_order_id is distinct from p_provider_order_id then
    raise exception 'INTEGRATION_DELIVERY_ID_CONFLICT' using errcode = 'P0001';
  end if;
end;
$$;

create or replace function public.valley_record_woocommerce_event(
  p_delivery_id text,
  p_topic text,
  p_payload_hash text,
  p_provider_order_id text,
  p_processing_status text,
  p_error_code text default null
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_event_id uuid;
begin
  insert into private.integration_events (
    source,
    delivery_id,
    topic,
    payload_hash,
    signature_verified,
    provider_order_id,
    processing_status,
    error_code,
    processed_at
  )
  values (
    'woocommerce',
    p_delivery_id,
    p_topic,
    p_payload_hash,
    true,
    p_provider_order_id,
    p_processing_status,
    p_error_code,
    now()
  )
  on conflict (source, delivery_id) do nothing
  returning id into v_event_id;

  if v_event_id is null then
    perform private.assert_integration_event_replay(
      'woocommerce',
      p_delivery_id,
      p_topic,
      p_payload_hash,
      p_provider_order_id
    );
  end if;

  return jsonb_build_object(
    'recorded', v_event_id is not null,
    'duplicate', v_event_id is null
  );
end;
$$;

create or replace function public.valley_process_paid_woocommerce_order(
  p_delivery_id text,
  p_topic text,
  p_payload_hash text,
  p_provider_order_id text,
  p_order_number text,
  p_product_id bigint,
  p_amount_minor bigint,
  p_currency text,
  p_billing_email text,
  p_billing_email_confirmation_digest text,
  p_billing_email_confirmed_at timestamptz,
  p_billing_email_confirmation_acceptance_source text,
  p_normalized_status text,
  p_gateway_transaction_id text,
  p_paid_at timestamptz,
  p_checkout_terms_version_presented text,
  p_checkout_terms_acceptance_source text,
  p_checkout_terms_presented_at timestamptz,
  p_candidate_grant_id uuid,
  p_grant_expires_at timestamptz
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_event_id uuid;
  v_reading_id uuid;
  v_commerce_order_id uuid;
  v_existing_order_status text;
  v_existing_product_id bigint;
  v_existing_amount_minor bigint;
  v_existing_currency text;
  v_existing_checkout_terms_version text;
  v_existing_checkout_terms_acceptance_source text;
  v_existing_checkout_terms_presented_at timestamptz;
  v_existing_billing_email_confirmation_digest text;
  v_existing_billing_email_confirmed_at timestamptz;
  v_existing_billing_email_confirmation_acceptance_source text;
  v_billing_email text;
  v_order_number text;
  v_grant_id uuid;
  v_grant_expires_at timestamptz;
  v_reading_status text;
  v_is_new_entitlement boolean := false;
  v_grant_rotated boolean := false;
  v_duplicate_event boolean := false;
begin
  if p_normalized_status not in ('processing', 'completed') then
    raise exception 'ORDER_NOT_PAID' using errcode = 'P0001';
  end if;
  if p_paid_at is null then
    raise exception 'ORDER_HAS_NO_PAID_TIMESTAMP' using errcode = 'P0001';
  end if;
  if p_candidate_grant_id is null
    or p_grant_expires_at is null
    or p_grant_expires_at <= now() + interval '1 day'
    or p_grant_expires_at > now() + interval '91 days' then
    raise exception 'INVALID_ACCESS_GRANT_CANDIDATE' using errcode = '22023';
  end if;
  if nullif(trim(p_checkout_terms_version_presented), '') is null
    or p_checkout_terms_acceptance_source is null
    or p_checkout_terms_acceptance_source not in (
      'classic-required-terms-checkbox',
      'store-api-validated-checkout'
    )
    or p_checkout_terms_presented_at is null
    or p_checkout_terms_presented_at > p_paid_at then
    raise exception 'ORDER_TERMS_PRESENTATION_INVALID' using errcode = 'P0001';
  end if;
  if p_billing_email is null
    or p_billing_email <> lower(p_billing_email)
    or p_billing_email !~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$' then
    raise exception 'INVALID_BILLING_EMAIL' using errcode = '22023';
  end if;
  if p_billing_email_confirmation_digest is null
    or p_billing_email_confirmation_digest !~ '^[0-9a-f]{64}$'
    or p_billing_email_confirmed_at is null
    or p_billing_email_confirmed_at > p_paid_at
    or p_billing_email_confirmation_acceptance_source is null
    or p_billing_email_confirmation_acceptance_source not in (
      'classic-checkout-server-validation',
      'store-api-server-validation'
    ) then
    raise exception 'ORDER_BILLING_EMAIL_CONFIRMATION_INVALID'
      using errcode = 'P0001';
  end if;

  perform pg_advisory_xact_lock(
    hashtextextended('woocommerce:' || p_provider_order_id, 0)
  );

  if exists (
    select 1
    from private.commerce_order_tombstones
    where provider = 'woocommerce'
      and provider_order_id = p_provider_order_id
  ) then
    raise exception 'ORDER_ACCESS_REVOKED' using errcode = 'P0001';
  end if;

  insert into private.integration_events (
    source,
    delivery_id,
    topic,
    payload_hash,
    signature_verified,
    provider_order_id,
    processing_status
  )
  values (
    'woocommerce',
    p_delivery_id,
    p_topic,
    p_payload_hash,
    true,
    p_provider_order_id,
    'received'
  )
  on conflict (source, delivery_id) do nothing
  returning id into v_event_id;

  if v_event_id is null then
    v_duplicate_event := true;
    perform private.assert_integration_event_replay(
      'woocommerce',
      p_delivery_id,
      p_topic,
      p_payload_hash,
      p_provider_order_id
    );
    select id into v_event_id
    from private.integration_events
    where source = 'woocommerce'
      and delivery_id = p_delivery_id;
  end if;

  select
    commerce_order.id,
    commerce_order.reading_id,
    commerce_order.normalized_status,
    commerce_order.billing_email,
    commerce_order.order_number,
    commerce_order.product_id,
    commerce_order.amount_minor,
    commerce_order.currency,
    reading.checkout_terms_version_presented,
    reading.checkout_terms_acceptance_source,
    date_trunc('second', reading.checkout_terms_presented_at),
    reading.billing_email_confirmation_digest,
    date_trunc('second', reading.billing_email_confirmed_at),
    reading.billing_email_confirmation_acceptance_source
    into
      v_commerce_order_id,
      v_reading_id,
      v_existing_order_status,
      v_billing_email,
      v_order_number,
      v_existing_product_id,
      v_existing_amount_minor,
      v_existing_currency,
      v_existing_checkout_terms_version,
      v_existing_checkout_terms_acceptance_source,
      v_existing_checkout_terms_presented_at,
      v_existing_billing_email_confirmation_digest,
      v_existing_billing_email_confirmed_at,
      v_existing_billing_email_confirmation_acceptance_source
  from private.commerce_orders as commerce_order
  join private.readings as reading on reading.id = commerce_order.reading_id
  where commerce_order.provider = 'woocommerce'
    and commerce_order.provider_order_id = p_provider_order_id
  for update;

  if v_reading_id is null then
    insert into private.readings (
      status,
      checkout_terms_version_presented,
      checkout_terms_acceptance_source,
      checkout_terms_presented_at,
      billing_email_confirmation_digest,
      billing_email_confirmed_at,
      billing_email_confirmation_acceptance_source
    )
    values (
      'awaiting_intake',
      p_checkout_terms_version_presented,
      p_checkout_terms_acceptance_source,
      date_trunc('second', p_checkout_terms_presented_at),
      p_billing_email_confirmation_digest,
      date_trunc('second', p_billing_email_confirmed_at),
      p_billing_email_confirmation_acceptance_source
    )
    returning id into v_reading_id;

    insert into private.reading_intakes (reading_id)
    values (v_reading_id);

    insert into private.commerce_orders (
      provider,
      provider_order_id,
      order_number,
      reading_id,
      product_id,
      amount_minor,
      currency,
      billing_email,
      normalized_status,
      gateway_transaction_id,
      paid_at
    )
    values (
      'woocommerce',
      p_provider_order_id,
      p_order_number,
      v_reading_id,
      p_product_id,
      p_amount_minor,
      p_currency,
      p_billing_email,
      p_normalized_status,
      nullif(p_gateway_transaction_id, ''),
      p_paid_at
    )
    returning id into v_commerce_order_id;

    v_is_new_entitlement := true;
    v_billing_email := p_billing_email;
    v_order_number := p_order_number;
  else
    if v_existing_product_id is distinct from p_product_id
      or v_existing_amount_minor is distinct from p_amount_minor
      or v_existing_currency is distinct from p_currency then
      raise exception 'ORDER_COMMERCE_EVIDENCE_CONFLICT'
        using errcode = 'P0001';
    end if;
    if v_existing_checkout_terms_version is distinct from
        p_checkout_terms_version_presented
      or v_existing_checkout_terms_acceptance_source is distinct from
        p_checkout_terms_acceptance_source
      or v_existing_checkout_terms_presented_at is distinct from
        date_trunc('second', p_checkout_terms_presented_at) then
      raise exception 'ORDER_TERMS_EVIDENCE_CONFLICT'
        using errcode = 'P0001';
    end if;
    if v_existing_billing_email_confirmation_digest is distinct from
        p_billing_email_confirmation_digest
      or v_existing_billing_email_confirmed_at is distinct from
        date_trunc('second', p_billing_email_confirmed_at)
      or v_existing_billing_email_confirmation_acceptance_source is distinct
        from p_billing_email_confirmation_acceptance_source then
      raise exception 'ORDER_BILLING_EMAIL_CONFIRMATION_CONFLICT'
        using errcode = 'P0001';
    end if;
    if v_existing_order_status in ('refunded', 'cancelled', 'failed') then
      raise exception 'ORDER_ACCESS_REVOKED' using errcode = 'P0001';
    end if;

    update private.commerce_orders
    set
      order_number = p_order_number,
      normalized_status = p_normalized_status,
      gateway_transaction_id = coalesce(nullif(p_gateway_transaction_id, ''), gateway_transaction_id),
      paid_at = least(p_paid_at, paid_at)
    where id = v_commerce_order_id;
  end if;

  select status into v_reading_status
  from private.readings
  where id = v_reading_id
  for update;

  if v_reading_status in ('refunded', 'revoked', 'erased') then
    raise exception 'ORDER_ACCESS_REVOKED' using errcode = 'P0001';
  end if;

  select grant_row.id, grant_row.expires_at
    into v_grant_id, v_grant_expires_at
  from private.reading_access_grants as grant_row
  where grant_row.reading_id = v_reading_id
    and grant_row.revoked_at is null
  order by grant_row.created_at desc
  limit 1
  for update;

  if v_grant_id is not null and v_grant_expires_at <= now() then
    update private.reading_access_grants
    set revoked_at = coalesce(revoked_at, now())
    where id = v_grant_id;

    update private.email_deliveries
    set
      status = 'suppressed',
      provider_generation = provider_generation + 1,
      provider_message_id = null,
      sending_started_at = null,
      next_attempt_at = null,
      last_error_code = 'ACCESS_GRANT_ROTATED'
    where access_grant_id = v_grant_id
      and status in ('pending', 'sending', 'sent', 'failed');

    v_grant_id := null;
    v_grant_expires_at := null;
    v_grant_rotated := true;
  end if;

  if v_grant_id is not null
    and not v_is_new_entitlement
    and exists (
      select 1
      from private.reading_access_grants as prior_grant
      where prior_grant.reading_id = v_reading_id
        and prior_grant.id <> v_grant_id
        and prior_grant.revoked_at is not null
    ) then
    v_grant_rotated := true;
  end if;

  if v_grant_id is null then
    if not v_is_new_entitlement then
      v_grant_rotated := true;
    end if;
    insert into private.reading_access_grants (
      id,
      reading_id,
      expires_at
    )
    values (
      p_candidate_grant_id,
      v_reading_id,
      date_trunc('second', p_grant_expires_at)
    )
    returning id, expires_at into v_grant_id, v_grant_expires_at;
  end if;

  update private.integration_events
  set
    processing_status = 'processed',
    error_code = null,
    processed_at = now()
  where id = v_event_id;

  return jsonb_build_object(
    'duplicate_event', v_duplicate_event,
    'grant_rotated', v_grant_rotated,
    'is_new_entitlement', v_is_new_entitlement,
    'reading_id', v_reading_id,
    'commerce_order_id', v_commerce_order_id,
    'grant_id', v_grant_id,
    'grant_expires_at', v_grant_expires_at,
    'billing_email', v_billing_email,
    'order_number', v_order_number,
    'provider_order_id', p_provider_order_id
  );
end;
$$;

create or replace function public.valley_revoke_paid_woocommerce_order(
  p_delivery_id text,
  p_topic text,
  p_payload_hash text,
  p_provider_order_id text,
  p_matches_expected_product boolean,
  p_normalized_status text,
  p_event_at timestamptz
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_event_id uuid;
  v_commerce_order_id uuid;
  v_reading_id uuid;
  v_effective_status text;
  v_duplicate_event boolean := false;
begin
  if p_normalized_status not in ('refunded', 'cancelled', 'failed') then
    raise exception 'INVALID_REVOCATION_STATUS' using errcode = '22023';
  end if;

  perform pg_advisory_xact_lock(
    hashtextextended('woocommerce:' || p_provider_order_id, 0)
  );

  insert into private.integration_events (
    source,
    delivery_id,
    topic,
    payload_hash,
    signature_verified,
    provider_order_id,
    processing_status
  )
  values (
    'woocommerce',
    p_delivery_id,
    p_topic,
    p_payload_hash,
    true,
    p_provider_order_id,
    'received'
  )
  on conflict (source, delivery_id) do nothing
  returning id into v_event_id;

  if v_event_id is null then
    v_duplicate_event := true;
    perform private.assert_integration_event_replay(
      'woocommerce',
      p_delivery_id,
      p_topic,
      p_payload_hash,
      p_provider_order_id
    );
    select id into v_event_id
    from private.integration_events
    where source = 'woocommerce'
      and delivery_id = p_delivery_id;
  end if;

  select commerce_order.id, commerce_order.reading_id
    into v_commerce_order_id, v_reading_id
  from private.commerce_orders as commerce_order
  where commerce_order.provider = 'woocommerce'
    and commerce_order.provider_order_id = p_provider_order_id
  for update;

  -- WooCommerce failed/cancelled are pre-payment states and may legitimately
  -- return to processing after a gateway retry. REST revalidation is the
  -- authority for each webhook, so these events are recorded but are not
  -- permanent tombstones and do not destroy an existing paid entitlement.
  if p_normalized_status in ('failed', 'cancelled') then
    if v_event_id is not null then
      update private.integration_events
      set
        processing_status = 'ignored',
        error_code = case p_normalized_status
          when 'failed' then 'ORDER_PAYMENT_FAILED'
          else 'ORDER_PAYMENT_CANCELLED'
        end,
        processed_at = now()
      where id = v_event_id;
    end if;

    return jsonb_build_object(
      'duplicate_event', v_duplicate_event,
      'entitlement_found', v_commerce_order_id is not null,
      'revoked', false
    );
  end if;

  -- Known-entitlement refund enforcement never depends on today's catalog.
  -- For a completely missed paid webhook, only a product-line match may
  -- create the terminal fence; price and currency are still irrelevant.
  if v_commerce_order_id is null
    and not coalesce(p_matches_expected_product, false) then
    if v_event_id is not null then
      update private.integration_events
      set
        processing_status = 'ignored',
        error_code = 'ORDER_REFUND_WITHOUT_ENTITLEMENT',
        processed_at = now()
      where id = v_event_id;
    end if;

    return jsonb_build_object(
      'duplicate_event', v_duplicate_event,
      'entitlement_found', false,
      'revoked', false
    );
  end if;

  insert into private.commerce_order_tombstones (
    provider,
    provider_order_id,
    normalized_status,
    delivery_id,
    payload_hash,
    event_at
  )
  values (
    'woocommerce',
    p_provider_order_id,
    'refunded',
    p_delivery_id,
    p_payload_hash,
    coalesce(p_event_at, now())
  )
  on conflict (provider, provider_order_id)
  do update set
    normalized_status = 'refunded',
    delivery_id = case
      when excluded.event_at >= private.commerce_order_tombstones.event_at
        then excluded.delivery_id
      else private.commerce_order_tombstones.delivery_id
    end,
    payload_hash = case
      when excluded.event_at >= private.commerce_order_tombstones.event_at
        then excluded.payload_hash
      else private.commerce_order_tombstones.payload_hash
    end,
    event_at = greatest(
      private.commerce_order_tombstones.event_at,
      excluded.event_at
    )
  returning normalized_status into v_effective_status;

  if v_commerce_order_id is null then
    update private.integration_events
    set
      processing_status = 'processed',
      error_code = null,
      processed_at = now()
    where id = v_event_id;

    return jsonb_build_object(
      'duplicate_event', v_duplicate_event,
      'entitlement_found', false,
      'revoked', false
    );
  end if;

  if v_commerce_order_id is not null then
    perform 1
    from private.fulfillments
    where reading_id = v_reading_id
    for update;

    perform 1
    from private.readings
    where id = v_reading_id
    for update;

    update private.commerce_orders
    set
      normalized_status = 'refunded',
      refunded_at = coalesce(refunded_at, p_event_at, now())
    where id = v_commerce_order_id;

    update private.reading_access_grants
    set revoked_at = coalesce(revoked_at, p_event_at, now())
    where reading_id = v_reading_id
      and revoked_at is null;

    update private.email_deliveries
    set
      status = case
        when status in ('pending', 'sending', 'sent', 'failed')
          then 'suppressed'
        else status
      end,
      provider_generation = provider_generation + case
        when status in ('pending', 'sending', 'sent', 'failed') then 1
        else 0
      end,
      provider_message_id = case
        when status in ('pending', 'sending', 'sent', 'failed') then null
        else provider_message_id
      end,
      sending_started_at = null,
      next_attempt_at = null,
      last_error_code = case
        when status in ('pending', 'sending', 'sent', 'failed')
          then 'ORDER_REFUNDED'
        else last_error_code
      end
    where reading_id = v_reading_id;

    update private.fulfillments
    set
      status = 'revoked',
      last_error_code = 'ORDER_REFUNDED',
      lease_owner = null,
      lease_expires_at = null,
      next_attempt_at = null
    where reading_id = v_reading_id
      and status <> 'revoked';

    update private.reading_results
    set revoked_at = coalesce(revoked_at, p_event_at, now())
    where reading_id = v_reading_id
      and revoked_at is null;

    update private.readings
    set status = case
      when status = 'erased' then 'erased'
      else 'refunded'
    end
    where id = v_reading_id;
  end if;

  update private.integration_events
  set
    processing_status = 'processed',
    error_code = null,
    processed_at = now()
  where id = v_event_id;

  return jsonb_build_object(
    'duplicate_event', v_duplicate_event,
    'entitlement_found', v_commerce_order_id is not null,
    'revoked', v_commerce_order_id is not null
  );
end;
$$;

create or replace function public.valley_set_access_grant_token_hash(
  p_grant_id uuid,
  p_token_hash text
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_existing_hash text;
begin
  if p_token_hash !~ '^[0-9a-f]{64}$' then
    raise exception 'INVALID_TOKEN_HASH' using errcode = '22023';
  end if;

  select token_hash
    into v_existing_hash
  from private.reading_access_grants
  where id = p_grant_id
    and revoked_at is null
    and expires_at > now()
  for update;

  if not found then
    raise exception 'READING_LINK_UNAVAILABLE' using errcode = 'P0001';
  end if;
  if v_existing_hash is not null and v_existing_hash <> p_token_hash then
    raise exception 'ACCESS_GRANT_HASH_MISMATCH' using errcode = 'P0001';
  end if;

  update private.reading_access_grants
  set token_hash = p_token_hash
  where id = p_grant_id;

  return true;
end;
$$;

create or replace function public.valley_get_paid_reading(
  p_grant_id uuid,
  p_token_hash text,
  p_expires_at timestamptz
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_reading_id uuid;
  v_payload jsonb;
begin
  v_reading_id := private.authorized_reading_id(
    p_grant_id,
    p_token_hash,
    p_expires_at
  );

  select jsonb_build_object(
    'reading_id', reading.id,
    'public_id', reading.public_id,
    'reading_status', reading.status,
    'draft_payload', intake.draft_payload,
    'intake_submitted_at', intake.submitted_at,
    'fulfillment_status', fulfillment.status,
    'result_payload', case
      when reading.status in ('ready', 'delivered') then result.result_payload
      else null
    end
  )
  into v_payload
  from private.readings as reading
  join private.reading_intakes as intake on intake.reading_id = reading.id
  left join private.fulfillments as fulfillment on fulfillment.reading_id = reading.id
  left join lateral (
    select stored_result.result_payload
    from private.reading_results as stored_result
    where stored_result.reading_id = reading.id
      and stored_result.revoked_at is null
    order by stored_result.result_version desc
    limit 1
  ) as result on true
  where reading.id = v_reading_id;

  update private.reading_access_grants
  set last_used_at = now()
  where id = p_grant_id
    and reading_id = v_reading_id
    and token_hash = p_token_hash
    and expires_at = p_expires_at
    and expires_at > now()
    and revoked_at is null;

  if not found then
    raise exception 'READING_LINK_UNAVAILABLE' using errcode = 'P0001';
  end if;

  return v_payload;
end;
$$;

create or replace function public.valley_save_reading_intake_draft(
  p_grant_id uuid,
  p_token_hash text,
  p_expires_at timestamptz,
  p_draft_payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_reading_id uuid;
  v_status text;
begin
  v_reading_id := private.authorized_reading_id(
    p_grant_id,
    p_token_hash,
    p_expires_at
  );

  select status into v_status
  from private.readings
  where id = v_reading_id
  for update;

  if v_status not in ('awaiting_intake', 'intake_in_progress') then
    raise exception 'INTAKE_LOCKED' using errcode = 'P0001';
  end if;

  perform 1
  from private.reading_access_grants
  where id = p_grant_id
    and reading_id = v_reading_id
    and token_hash = p_token_hash
    and expires_at = p_expires_at
    and expires_at > now()
    and revoked_at is null
  for update;

  if not found then
    raise exception 'READING_LINK_UNAVAILABLE' using errcode = 'P0001';
  end if;

  update private.reading_intakes
  set draft_payload = p_draft_payload
  where reading_id = v_reading_id;

  update private.readings
  set
    status = 'intake_in_progress',
    intake_started_at = coalesce(intake_started_at, now())
  where id = v_reading_id;

  return jsonb_build_object(
    'reading_status', 'intake_in_progress',
    'saved', true
  );
end;
$$;

create or replace function public.valley_submit_reading_intake(
  p_grant_id uuid,
  p_token_hash text,
  p_expires_at timestamptz,
  p_intake_version text,
  p_final_payload jsonb,
  p_precision_snapshot jsonb,
  p_generation_consent_version text,
  p_generation_consent_accepted_at timestamptz
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_reading_id uuid;
  v_commerce_order_id uuid;
  v_fulfillment_id uuid;
begin
  v_reading_id := private.authorized_reading_id(
    p_grant_id,
    p_token_hash,
    p_expires_at
  );

  perform pg_advisory_xact_lock(hashtextextended(v_reading_id::text, 0));

  select id into v_commerce_order_id
  from private.commerce_orders
  where reading_id = v_reading_id
    and normalized_status in ('processing', 'completed')
  for update;

  if v_commerce_order_id is null then
    raise exception 'ORDER_NOT_PAID' using errcode = 'P0001';
  end if;

  perform 1
  from private.readings
  where id = v_reading_id
    and status in ('awaiting_intake', 'intake_in_progress')
  for update;

  if not found then
    raise exception 'INTAKE_LOCKED' using errcode = 'P0001';
  end if;

  perform 1
  from private.reading_access_grants
  where id = p_grant_id
    and reading_id = v_reading_id
    and token_hash = p_token_hash
    and expires_at = p_expires_at
    and expires_at > now()
    and revoked_at is null
  for update;

  if not found then
    raise exception 'READING_LINK_UNAVAILABLE' using errcode = 'P0001';
  end if;

  update private.readings
  set
    status = 'intake_submitted',
    intake_started_at = coalesce(intake_started_at, now()),
    intake_submitted_at = now()
  where id = v_reading_id
    and status in ('awaiting_intake', 'intake_in_progress');

  if not found then
    raise exception 'INTAKE_LOCKED' using errcode = 'P0001';
  end if;

  update private.reading_intakes
  set
    intake_version = p_intake_version,
    draft_payload = p_final_payload,
    final_payload = p_final_payload,
    precision_snapshot = p_precision_snapshot,
    generation_consent_version = p_generation_consent_version,
    generation_consent_accepted_at = p_generation_consent_accepted_at,
    submitted_at = now()
  where reading_id = v_reading_id
    and submitted_at is null;

  if not found then
    raise exception 'INTAKE_LOCKED' using errcode = 'P0001';
  end if;

  insert into private.fulfillments (
    reading_id,
    commerce_order_id,
    status
  )
  values (
    v_reading_id,
    v_commerce_order_id,
    'queued'
  )
  returning id into v_fulfillment_id;

  update private.readings
  set status = 'queued'
  where id = v_reading_id;

  return jsonb_build_object(
    'reading_id', v_reading_id,
    'fulfillment_id', v_fulfillment_id,
    'reading_status', 'queued'
  );
end;
$$;

create or replace function public.valley_claim_reading_fulfillment(
  p_request_id uuid,
  p_worker_id text,
  p_lease_seconds integer
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_fulfillment_id uuid;
  v_reading_id uuid;
  v_attempt_count integer;
  v_lease_expires_at timestamptz;
  v_job jsonb;
  v_existing_request private.worker_claim_requests%rowtype;
begin
  if p_request_id is null
    or p_worker_id is null
    or p_worker_id !~ '^[A-Za-z0-9._:-]{1,120}$'
    or p_lease_seconds is null
    or p_lease_seconds < 60
    or p_lease_seconds > 1800 then
    raise exception 'INVALID_WORKER_CLAIM' using errcode = '22023';
  end if;

  perform pg_advisory_xact_lock(hashtextextended(p_request_id::text, 0));

  delete from private.worker_claim_requests
  where created_at < now() - interval '1 day';

  select * into v_existing_request
  from private.worker_claim_requests
  where request_id = p_request_id;

  if found then
    if v_existing_request.worker_id <> p_worker_id then
      raise exception 'WORKER_CLAIM_REQUEST_CONFLICT' using errcode = 'P0001';
    end if;
    if v_existing_request.fulfillment_id is null then
      return jsonb_build_object('claimed', false);
    end if;

    select jsonb_build_object(
      'claimed', true,
      'version', 'paid-reading-job-v1',
      'worker_id', p_worker_id,
      'fulfillment_id', fulfillment.id,
      'reading_id', reading.id,
      'public_reading_id', reading.public_id,
      'attempt_count', v_existing_request.attempt_count,
      'lease_expires_at', v_existing_request.lease_expires_at,
      'intake_version', intake.intake_version,
      'analysis_datetime', reading.intake_submitted_at,
      'analysis_timezone', 'Asia/Taipei',
      'final_payload', intake.final_payload,
      'precision_snapshot', intake.precision_snapshot,
      'generation_consent_version', intake.generation_consent_version
    )
    into v_job
    from private.fulfillments as fulfillment
    join private.readings as reading on reading.id = fulfillment.reading_id
    join private.reading_intakes as intake on intake.reading_id = reading.id
    where fulfillment.id = v_existing_request.fulfillment_id
      and fulfillment.status = 'generating'
      and fulfillment.lease_owner = p_worker_id
      and fulfillment.attempt_count = v_existing_request.attempt_count
      and fulfillment.lease_expires_at = v_existing_request.lease_expires_at
      and fulfillment.lease_expires_at > now()
      and reading.status = 'generating'
      and intake.submitted_at is not null
      and intake.final_payload is not null;

    return coalesce(v_job, jsonb_build_object('claimed', false));
  end if;

  update private.fulfillments
  set
    status = 'needs_review',
    last_error_code = 'WORKER_RETRY_LIMIT_REACHED',
    lease_owner = null,
    lease_expires_at = null,
    next_attempt_at = null
  where status = 'generating'
    and lease_expires_at <= now()
    and attempt_count >= 5;

  update private.readings as reading
  set status = 'needs_review'
  where exists (
    select 1
    from private.fulfillments as fulfillment
    where fulfillment.reading_id = reading.id
      and fulfillment.status = 'needs_review'
  )
    and reading.status not in ('ready', 'delivered', 'refunded', 'revoked', 'erased');

  select fulfillment.id, fulfillment.reading_id
    into v_fulfillment_id, v_reading_id
  from private.fulfillments as fulfillment
  join private.readings as reading on reading.id = fulfillment.reading_id
  where (
      fulfillment.status = 'queued'
      or (
        fulfillment.status = 'retrying'
        and fulfillment.next_attempt_at <= now()
      )
      or (
        fulfillment.status = 'generating'
        and fulfillment.lease_expires_at <= now()
      )
    )
    and fulfillment.attempt_count < 5
    and reading.status not in ('ready', 'delivered', 'refunded', 'revoked', 'erased')
  order by
    case when fulfillment.status = 'queued' then 0 else 1 end,
    fulfillment.created_at
  limit 1
  for update of fulfillment skip locked;

  if v_fulfillment_id is null then
    insert into private.worker_claim_requests (
      request_id,
      worker_id,
      fulfillment_id
    )
    values (p_request_id, p_worker_id, null);
    return jsonb_build_object('claimed', false);
  end if;

  update private.fulfillments
  set
    status = 'generating',
    attempt_count = attempt_count + 1,
    lease_owner = p_worker_id,
    lease_expires_at = now() + make_interval(secs => p_lease_seconds),
    next_attempt_at = null,
    started_at = coalesce(started_at, now()),
    last_error_code = null
  where id = v_fulfillment_id
  returning attempt_count, lease_expires_at
    into v_attempt_count, v_lease_expires_at;

  update private.readings
  set status = 'generating'
  where id = v_reading_id
    and status not in ('ready', 'delivered', 'refunded', 'revoked', 'erased');

  select jsonb_build_object(
    'claimed', true,
    'version', 'paid-reading-job-v1',
    'worker_id', p_worker_id,
    'fulfillment_id', fulfillment.id,
    'reading_id', reading.id,
    'public_reading_id', reading.public_id,
    'attempt_count', fulfillment.attempt_count,
    'lease_expires_at', fulfillment.lease_expires_at,
    'intake_version', intake.intake_version,
    'analysis_datetime', reading.intake_submitted_at,
    'analysis_timezone', 'Asia/Taipei',
    'final_payload', intake.final_payload,
    'precision_snapshot', intake.precision_snapshot,
    'generation_consent_version', intake.generation_consent_version
  )
  into v_job
  from private.fulfillments as fulfillment
  join private.readings as reading on reading.id = fulfillment.reading_id
  join private.reading_intakes as intake on intake.reading_id = reading.id
  where fulfillment.id = v_fulfillment_id
    and intake.submitted_at is not null
    and intake.final_payload is not null;

  if v_job is null then
    raise exception 'FULFILLMENT_INTAKE_NOT_FOUND' using errcode = 'P0001';
  end if;

  insert into private.worker_claim_requests (
    request_id,
    worker_id,
    fulfillment_id,
    attempt_count,
    lease_expires_at
  )
  values (
    p_request_id,
    p_worker_id,
    v_fulfillment_id,
    v_attempt_count,
    v_lease_expires_at
  );

  return v_job;
end;
$$;

create or replace function public.valley_fail_reading_fulfillment(
  p_fulfillment_id uuid,
  p_reading_id uuid,
  p_worker_id text,
  p_attempt_count integer,
  p_retryable boolean,
  p_error_code text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_fulfillment private.fulfillments%rowtype;
  v_next_status text;
begin
  if p_fulfillment_id is null
    or p_reading_id is null
    or p_worker_id is null
    or p_worker_id !~ '^[A-Za-z0-9._:-]{1,120}$'
    or p_attempt_count is null
    or p_attempt_count < 1
    or p_retryable is null
    or p_error_code is null
    or p_error_code !~ '^[A-Z0-9_]{2,80}$' then
    raise exception 'INVALID_WORKER_FAILURE' using errcode = '22023';
  end if;

  perform pg_advisory_xact_lock(hashtextextended(p_fulfillment_id::text, 0));

  select * into v_fulfillment
  from private.fulfillments
  where id = p_fulfillment_id
    and reading_id = p_reading_id
  for update;

  if not found then
    raise exception 'FULFILLMENT_NOT_FOUND' using errcode = 'P0001';
  end if;

  v_next_status := case
    when p_retryable and p_attempt_count < 5 then 'retrying'
    else 'needs_review'
  end;

  if v_fulfillment.status = v_next_status
    and v_fulfillment.lease_owner is null
    and v_fulfillment.lease_expires_at is null
    and v_fulfillment.attempt_count = p_attempt_count
    and v_fulfillment.last_error_code = p_error_code then
    return jsonb_build_object(
      'accepted', true,
      'duplicate', true,
      'fulfillment_id', p_fulfillment_id,
      'reading_id', p_reading_id,
      'status', v_next_status
    );
  end if;

  if v_fulfillment.status <> 'generating'
    or v_fulfillment.lease_owner is distinct from p_worker_id
    or v_fulfillment.attempt_count is distinct from p_attempt_count
    or v_fulfillment.lease_expires_at is null
    or v_fulfillment.lease_expires_at <= now() then
    raise exception 'FULFILLMENT_LEASE_MISMATCH' using errcode = 'P0001';
  end if;

  update private.fulfillments
  set
    status = v_next_status,
    last_error_code = p_error_code,
    lease_owner = null,
    lease_expires_at = null,
    next_attempt_at = case
      when v_next_status = 'retrying' then
        now() + make_interval(
          secs => least(
            21600,
            (300 * power(2, greatest(p_attempt_count - 1, 0)))::integer
          )
        )
      else null
    end
  where id = p_fulfillment_id;

  update private.readings
  set status = v_next_status
  where id = p_reading_id
    and status not in ('ready', 'delivered', 'refunded', 'revoked', 'erased');

  return jsonb_build_object(
    'accepted', true,
    'duplicate', false,
    'fulfillment_id', p_fulfillment_id,
    'reading_id', p_reading_id,
    'status', v_next_status
  );
end;
$$;

create or replace function public.valley_renew_reading_fulfillment_lease(
  p_fulfillment_id uuid,
  p_reading_id uuid,
  p_worker_id text,
  p_attempt_count integer,
  p_lease_seconds integer
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_lease_expires_at timestamptz;
begin
  if p_fulfillment_id is null
    or p_reading_id is null
    or p_worker_id is null
    or p_worker_id !~ '^[A-Za-z0-9._:-]{1,120}$'
    or p_attempt_count is null
    or p_lease_seconds is null
    or p_attempt_count < 1
    or p_lease_seconds < 60
    or p_lease_seconds > 1800 then
    raise exception 'INVALID_WORKER_HEARTBEAT' using errcode = '22023';
  end if;

  perform pg_advisory_xact_lock(hashtextextended(p_fulfillment_id::text, 0));

  update private.fulfillments
  set lease_expires_at = now() + make_interval(secs => p_lease_seconds)
  where id = p_fulfillment_id
    and reading_id = p_reading_id
    and status = 'generating'
    and lease_owner = p_worker_id
    and attempt_count = p_attempt_count
    and lease_expires_at > now()
  returning lease_expires_at into v_lease_expires_at;

  if v_lease_expires_at is null then
    raise exception 'FULFILLMENT_LEASE_MISMATCH' using errcode = 'P0001';
  end if;

  return jsonb_build_object(
    'renewed', true,
    'fulfillment_id', p_fulfillment_id,
    'reading_id', p_reading_id,
    'lease_expires_at', v_lease_expires_at
  );
end;
$$;

create or replace function public.valley_claim_email_delivery(
  p_reading_id uuid,
  p_access_grant_id uuid,
  p_message_kind text,
  p_template_version text,
  p_recipient_hash text,
  p_provider_request_hash text,
  p_provider text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_delivery private.email_deliveries%rowtype;
begin
  if p_recipient_hash is null
    or p_recipient_hash !~ '^[0-9a-f]{64}$'
    or p_provider_request_hash is null
    or p_provider_request_hash !~ '^[0-9a-f]{64}$'
    or p_provider is null
    or p_provider not in ('resend', 'woocommerce') then
    raise exception 'INVALID_EMAIL_DELIVERY_REQUEST' using errcode = '22023';
  end if;

  perform pg_advisory_xact_lock(
    hashtextextended(
      p_reading_id::text || ':' || p_message_kind || ':' || p_template_version,
      0
    )
  );

  perform pg_advisory_xact_lock(
    hashtextextended('email-recipient:' || p_recipient_hash, 0)
  );

  if exists (
    select 1
    from private.email_recipient_suppressions
    where recipient_hash = p_recipient_hash
      and cleared_at is null
  ) then
    return jsonb_build_object(
      'claimed', false,
      'reason', 'recipient_suppressed'
    );
  end if;

  perform 1
  from private.reading_access_grants
  where id = p_access_grant_id
    and reading_id = p_reading_id
    and revoked_at is null
    and expires_at > now()
  for update;

  if not found then
    raise exception 'READING_LINK_UNAVAILABLE' using errcode = 'P0001';
  end if;

  select * into v_delivery
  from private.email_deliveries
  where reading_id = p_reading_id
    and message_kind = p_message_kind
    and template_version = p_template_version
  for update;

  if found and v_delivery.status in ('sent', 'delivered') then
    return jsonb_build_object('claimed', false, 'reason', 'already_sent');
  end if;

  if found and (
    v_delivery.status in ('bounced', 'complained', 'suppressed')
    or (
      v_delivery.attempt_count >= 5
      and (
        v_delivery.status = 'failed'
        or (
          v_delivery.status = 'sending'
          and v_delivery.sending_started_at <= now() - interval '5 minutes'
        )
      )
    )
  ) then
    if v_delivery.status not in ('bounced', 'complained', 'suppressed') then
      update private.email_deliveries
      set
        status = 'suppressed',
        last_error_code = coalesce(last_error_code, 'EMAIL_RETRY_LIMIT_REACHED'),
        next_attempt_at = null
      where id = v_delivery.id;
    end if;
    return jsonb_build_object('claimed', false, 'reason', 'retry_exhausted');
  end if;

  if found
    and v_delivery.status = 'sending'
    and v_delivery.sending_started_at > now() - interval '5 minutes' then
    return jsonb_build_object('claimed', false, 'reason', 'in_progress');
  end if;

  if found
    and v_delivery.status = 'failed'
    and v_delivery.next_attempt_at > now() then
    return jsonb_build_object('claimed', false, 'reason', 'retry_backoff');
  end if;

  if not found then
    insert into private.email_deliveries (
      reading_id,
      access_grant_id,
      message_kind,
      template_version,
      provider,
      recipient_hash,
      status,
      attempt_count,
      provider_request_hash,
      sending_started_at,
      next_attempt_at
    )
    values (
      p_reading_id,
      p_access_grant_id,
      p_message_kind,
      p_template_version,
      p_provider,
      p_recipient_hash,
      'sending',
      1,
      p_provider_request_hash,
      now(),
      null
    )
    returning * into v_delivery;
  else
    update private.email_deliveries
    set
      provider_generation = provider_generation + case
        when provider is distinct from p_provider
          or access_grant_id is distinct from p_access_grant_id
          or recipient_hash is distinct from p_recipient_hash
          or (
            provider_request_hash is not null
            and provider_request_hash is distinct from p_provider_request_hash
          )
          then 1
        else 0
      end,
      provider_message_id = case
        when provider is distinct from p_provider
          or access_grant_id is distinct from p_access_grant_id
          or recipient_hash is distinct from p_recipient_hash
          or (
            provider_request_hash is not null
            and provider_request_hash is distinct from p_provider_request_hash
          )
          then null
        else provider_message_id
      end,
      access_grant_id = p_access_grant_id,
      provider = p_provider,
      recipient_hash = p_recipient_hash,
      provider_request_hash = p_provider_request_hash,
      status = 'sending',
      attempt_count = attempt_count + 1,
      sending_started_at = now(),
      next_attempt_at = null,
      sent_at = null,
      delivered_at = null,
      bounced_at = null,
      complained_at = null,
      last_error_code = null
    where id = v_delivery.id
    returning * into v_delivery;
  end if;

  return jsonb_build_object(
    'claimed', true,
    'delivery_id', v_delivery.id,
    'attempt_count', v_delivery.attempt_count,
    'provider_generation', v_delivery.provider_generation
  );
end;
$$;

create or replace function public.valley_finish_email_delivery(
  p_delivery_id uuid,
  p_access_grant_id uuid,
  p_attempt_count integer,
  p_status text,
  p_provider_message_id text default null,
  p_error_code text default null,
  p_provider text default 'woocommerce'
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_delivery private.email_deliveries%rowtype;
begin
  if p_delivery_id is null
    or p_access_grant_id is null
    or p_status is null
    or p_status not in ('sent', 'failed')
    or p_provider is null
    or p_provider not in ('resend', 'woocommerce') then
    raise exception 'INVALID_EMAIL_DELIVERY_STATUS' using errcode = '22023';
  end if;
  if p_attempt_count is null
    or p_attempt_count < 1
    or (
      p_status = 'sent'
      and (
        p_provider_message_id is null
        or p_provider_message_id !~ '^[A-Za-z0-9._:-]{8,160}$'
      )
    ) then
    raise exception 'INVALID_EMAIL_DELIVERY_ATTEMPT' using errcode = '22023';
  end if;

  perform 1
  from private.reading_access_grants
  where id = p_access_grant_id
    and revoked_at is null
    and expires_at > now()
  for update;

  if not found then
    return false;
  end if;

  update private.email_deliveries
  set
    status = case
      when p_status = 'failed' and p_attempt_count >= 5 then 'suppressed'
      else p_status
    end,
    provider_message_id = case when p_status = 'sent' then p_provider_message_id else provider_message_id end,
    sent_at = case when p_status = 'sent' then now() else sent_at end,
    last_error_code = case
      when p_status = 'failed' and p_attempt_count >= 5
        then coalesce(p_error_code, 'EMAIL_RETRY_LIMIT_REACHED')
      else p_error_code
    end,
    next_attempt_at = case
      when p_status = 'failed' and p_attempt_count < 5 then
        now() + make_interval(
          secs => least(
            21600,
            (300 * power(2, greatest(p_attempt_count - 1, 0)))::integer
          )
        )
      else null
    end
  where id = p_delivery_id
    and access_grant_id = p_access_grant_id
    and provider = p_provider
    and status = 'sending'
    and attempt_count = p_attempt_count
  returning * into v_delivery;

  if not found then
    return false;
  end if;

  if p_status = 'sent' then
    insert into private.email_provider_messages (
      email_delivery_id,
      provider,
      provider_message_id,
      provider_generation,
      recipient_hash
    )
    values (
      v_delivery.id,
      v_delivery.provider,
      p_provider_message_id,
      v_delivery.provider_generation,
      v_delivery.recipient_hash
    )
    on conflict do nothing;

    if not exists (
      select 1
      from private.email_provider_messages
      where email_delivery_id = v_delivery.id
        and provider = v_delivery.provider
        and provider_message_id = p_provider_message_id
        and provider_generation = v_delivery.provider_generation
        and recipient_hash = v_delivery.recipient_hash
    ) then
      raise exception 'EMAIL_PROVIDER_MESSAGE_CONFLICT' using errcode = 'P0001';
    end if;
  end if;

  return true;
end;
$$;

create or replace function public.valley_record_resend_email_event(
  p_event_id text,
  p_event_type text,
  p_provider_message_id text,
  p_payload_hash text,
  p_event_at timestamptz
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_event_id uuid;
  v_existing_event private.email_provider_events%rowtype;
  v_message private.email_provider_messages%rowtype;
  v_delivery private.email_deliveries%rowtype;
  v_reading_id uuid;
  v_effective_event_type text;
  v_effective_event_at timestamptz;
  v_next_status text;
  v_has_unprocessed boolean;
  v_duplicate boolean := false;
begin
  if p_event_id is null
    or p_event_id !~ '^[A-Za-z0-9._:-]{8,160}$'
    or p_provider_message_id is null
    or p_provider_message_id !~ '^[A-Za-z0-9._:-]{8,160}$'
    or p_payload_hash is null
    or p_payload_hash !~ '^[0-9a-f]{64}$'
    or p_event_type is null
    or p_event_type not in (
      'email.sent',
      'email.delivered',
      'email.delivery_delayed',
      'email.failed',
      'email.bounced',
      'email.complained',
      'email.suppressed'
    )
    or p_event_at is null then
    raise exception 'INVALID_RESEND_EVENT' using errcode = '22023';
  end if;

  perform pg_advisory_xact_lock(
    hashtextextended('resend:' || p_provider_message_id, 0)
  );

  insert into private.email_provider_events (
    provider,
    event_id,
    event_type,
    provider_message_id,
    payload_hash,
    signature_verified,
    processing_status,
    event_at
  )
  values (
    'resend',
    p_event_id,
    p_event_type,
    p_provider_message_id,
    p_payload_hash,
    true,
    'received',
    p_event_at
  )
  on conflict (provider, event_id) do nothing
  returning id into v_event_id;

  if v_event_id is null then
    v_duplicate := true;
    select * into v_existing_event
    from private.email_provider_events
    where provider = 'resend'
      and event_id = p_event_id;

    if not found
      or v_existing_event.event_type is distinct from p_event_type
      or v_existing_event.provider_message_id is distinct from p_provider_message_id
      or v_existing_event.payload_hash is distinct from p_payload_hash
      or v_existing_event.event_at is distinct from p_event_at then
      raise exception 'RESEND_EVENT_ID_CONFLICT' using errcode = 'P0001';
    end if;
    v_event_id := v_existing_event.id;
    if v_existing_event.processing_status = 'processed' then
      return jsonb_build_object(
        'recorded', true,
        'duplicate', true,
        'matched', true
      );
    end if;
  end if;

  select * into v_message
  from private.email_provider_messages
  where provider = 'resend'
    and provider_message_id = p_provider_message_id;

  if not found then
    return jsonb_build_object(
      'recorded', true,
      'duplicate', v_duplicate,
      'matched', false
    );
  end if;

  if p_event_type in (
    'email.bounced',
    'email.complained',
    'email.suppressed'
  ) then
    perform pg_advisory_xact_lock(
      hashtextextended(
        'email-recipient:' || v_message.recipient_hash,
        0
      )
    );

    insert into private.email_recipient_suppressions as active_suppression (
      recipient_hash,
      suppression_kind,
      source_email_delivery_id,
      source_email_event_id
    )
    values (
      v_message.recipient_hash,
      case p_event_type
        when 'email.bounced' then 'bounced'
        when 'email.complained' then 'complained'
        else 'suppressed'
      end,
      v_message.email_delivery_id,
      v_event_id
    )
    on conflict (recipient_hash) where cleared_at is null do update
    set
      suppression_kind = excluded.suppression_kind,
      source_email_delivery_id = excluded.source_email_delivery_id,
      source_email_event_id = excluded.source_email_event_id,
      created_at = now()
    where
      case excluded.suppression_kind
        when 'complained' then 3
        when 'bounced' then 2
        else 1
      end >
      case active_suppression.suppression_kind
        when 'complained' then 3
        when 'bounced' then 2
        else 1
      end;
  end if;

  select reading_id into v_reading_id
  from private.email_deliveries
  where id = v_message.email_delivery_id;

  perform 1
  from private.fulfillments
  where reading_id = v_reading_id
  for update;

  perform 1
  from private.readings
  where id = v_reading_id
  for update;

  select * into v_delivery
  from private.email_deliveries
  where id = v_message.email_delivery_id
    and provider = 'resend'
    and reading_id = v_reading_id
  for update;

  if not found then
    return jsonb_build_object(
      'recorded', true,
      'duplicate', v_duplicate,
      'matched', false
    );
  end if;

  if v_message.provider_generation < v_delivery.provider_generation then
    update private.email_provider_events
    set processing_status = 'processed', processed_at = now()
    where provider = 'resend'
      and event_id = p_event_id;
    return jsonb_build_object(
      'recorded', true,
      'duplicate', v_duplicate,
      'matched', true,
      'stale_generation', true
    );
  end if;
  if v_message.provider_generation <> v_delivery.provider_generation then
    raise exception 'RESEND_MESSAGE_GENERATION_CONFLICT' using errcode = 'P0001';
  end if;

  select exists (
    select 1
    from private.email_provider_events
    where provider = 'resend'
      and provider_message_id = p_provider_message_id
      and processing_status = 'received'
  ) into v_has_unprocessed;

  select event_type, event_at
    into v_effective_event_type, v_effective_event_at
  from private.email_provider_events
  where provider = 'resend'
    and provider_message_id = p_provider_message_id
  order by
    case event_type
      when 'email.complained' then 6
      when 'email.bounced' then 5
      when 'email.suppressed' then 4
      when 'email.failed' then 3
      when 'email.delivered' then 2
      else 1
    end desc,
    event_at desc
  limit 1;

  v_next_status := case v_effective_event_type
    when 'email.complained' then 'complained'
    when 'email.bounced' then 'bounced'
    when 'email.suppressed' then 'suppressed'
    when 'email.failed' then
      case when v_delivery.attempt_count >= 5 then 'suppressed' else 'failed' end
    when 'email.delivered' then 'delivered'
    else v_delivery.status
  end;

  update private.email_deliveries
  set
    status = v_next_status,
    provider_generation = case
      when v_next_status = 'failed' and v_has_unprocessed
        then provider_generation + 1
      else provider_generation
    end,
    provider_message_id = case
      when v_next_status = 'failed' and v_has_unprocessed then null
      else provider_message_id
    end,
    delivered_at = case
      when v_next_status = 'delivered'
        then coalesce(delivered_at, v_effective_event_at)
      else delivered_at
    end,
    bounced_at = case
      when v_next_status = 'bounced'
        then coalesce(bounced_at, v_effective_event_at)
      else bounced_at
    end,
    complained_at = case
      when v_next_status = 'complained'
        then coalesce(complained_at, v_effective_event_at)
      else complained_at
    end,
    last_error_code = case v_effective_event_type
      when 'email.bounced' then 'RESEND_EMAIL_BOUNCED'
      when 'email.complained' then 'RESEND_EMAIL_COMPLAINED'
      when 'email.suppressed' then 'RESEND_EMAIL_SUPPRESSED'
      when 'email.failed' then 'RESEND_EMAIL_FAILED'
      else last_error_code
    end,
    sending_started_at = case
      when v_next_status in ('failed', 'bounced', 'complained', 'suppressed')
        then null
      else sending_started_at
    end,
    next_attempt_at = case
      when v_next_status = 'failed' then
        now() + make_interval(
          secs => least(
            21600,
            (300 * power(2, greatest(v_delivery.attempt_count - 1, 0)))::integer
          )
        )
      else null
    end
  where id = v_delivery.id;

  update private.email_provider_events
  set processing_status = 'processed', processed_at = now()
  where provider = 'resend'
    and provider_message_id = p_provider_message_id
    and processing_status = 'received';

  if v_delivery.message_kind = 'result_ready'
    and v_next_status = 'delivered' then
    update private.fulfillments
    set
      status = 'delivered',
      delivered_at = coalesce(delivered_at, v_effective_event_at)
    where reading_id = v_reading_id
      and status = 'ready';

    update private.readings
    set status = 'delivered'
    where id = v_reading_id
      and status = 'ready';
  end if;

  return jsonb_build_object(
    'recorded', true,
    'duplicate', v_duplicate,
    'matched', true,
    'delivery_status', v_next_status
  );
end;
$$;

create or replace function public.valley_recover_paid_reading(
  p_billing_email text,
  p_order_number text,
  p_candidate_grant_id uuid,
  p_candidate_grant_expires_at timestamptz,
  p_recovery_template_version text,
  p_recipient_hash text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_commerce_order private.commerce_orders%rowtype;
  v_delivery private.email_deliveries%rowtype;
  v_grant private.reading_access_grants%rowtype;
  v_reading_status text;
  v_recovery_template_version text;
begin
  if p_billing_email is null
    or p_billing_email <> lower(p_billing_email)
    or p_billing_email !~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'
    or nullif(trim(p_order_number), '') is null
    or p_candidate_grant_id is null
    or p_candidate_grant_expires_at is null
    or p_candidate_grant_expires_at <= now() + interval '1 day'
    or p_candidate_grant_expires_at > now() + interval '91 days'
    or p_recovery_template_version !~ '^paid-access-recovery-v1:[0-9a-f-]{36}$'
    or p_recovery_template_version <>
      'paid-access-recovery-v1:' || p_candidate_grant_id::text
    or p_recipient_hash is null
    or p_recipient_hash !~ '^[0-9a-f]{64}$' then
    raise exception 'INVALID_READING_RECOVERY_REQUEST' using errcode = '22023';
  end if;

  perform pg_advisory_xact_lock(
    hashtextextended(
      'reading-recovery:' || p_billing_email || ':' || trim(p_order_number),
      0
    )
  );

  select commerce_order.*
    into v_commerce_order
  from private.commerce_orders as commerce_order
  join private.readings as reading on reading.id = commerce_order.reading_id
  where commerce_order.provider = 'woocommerce'
    and commerce_order.billing_email = p_billing_email
    and commerce_order.order_number = trim(p_order_number)
    and commerce_order.normalized_status in ('processing', 'completed')
    and reading.status not in ('refunded', 'revoked', 'erased')
  order by commerce_order.created_at desc
  limit 1
  for update of commerce_order;

  if not found then
    return jsonb_build_object('eligible', false);
  end if;

  perform 1
  from private.fulfillments
  where reading_id = v_commerce_order.reading_id
  for update;

  select status into v_reading_status
  from private.readings
  where id = v_commerce_order.reading_id
  for update;

  if v_reading_status in ('refunded', 'revoked', 'erased') then
    return jsonb_build_object('eligible', false);
  end if;

  if exists (
    select 1
    from private.email_recipient_suppressions
    where recipient_hash = p_recipient_hash
      and cleared_at is null
  ) then
    return jsonb_build_object('eligible', false);
  end if;

  select * into v_grant
  from private.reading_access_grants
  where reading_id = v_commerce_order.reading_id
    and revoked_at is null
  order by created_at desc
  limit 1
  for update;

  if found and v_grant.expires_at <= now() then
    update private.reading_access_grants
    set revoked_at = coalesce(revoked_at, now())
    where id = v_grant.id;

    update private.email_deliveries
    set
      status = 'suppressed',
      provider_generation = provider_generation + 1,
      provider_message_id = null,
      sending_started_at = null,
      next_attempt_at = null,
      last_error_code = 'ACCESS_GRANT_ROTATED'
    where access_grant_id = v_grant.id
      and status in ('pending', 'sending', 'sent', 'failed');

    v_grant := null;
  end if;

  if v_grant.id is null then
    insert into private.reading_access_grants (
      id,
      reading_id,
      expires_at
    )
    values (
      p_candidate_grant_id,
      v_commerce_order.reading_id,
      date_trunc('second', p_candidate_grant_expires_at)
    )
    returning * into v_grant;
  end if;

  v_recovery_template_version :=
    'paid-access-recovery-v1:' || v_grant.id::text;

  select * into v_delivery
  from private.email_deliveries
  where reading_id = v_commerce_order.reading_id
    and message_kind = 'access_recovery'
    and template_version = v_recovery_template_version
  for update;

  if found and (
    v_delivery.status in ('bounced', 'complained')
    or (
      v_delivery.status = 'suppressed'
      and v_delivery.last_error_code = 'RESEND_EMAIL_SUPPRESSED'
    )
  ) then
    if v_delivery.recipient_hash is distinct from p_recipient_hash
      or not exists (
        select 1
        from private.email_recipient_suppressions as suppression
        where suppression.recipient_hash = p_recipient_hash
          and suppression.cleared_at is not null
          and suppression.suppression_kind = case
            when v_delivery.status = 'bounced' then 'bounced'
            when v_delivery.status = 'complained' then 'complained'
            else 'suppressed'
          end
      ) then
      return jsonb_build_object('eligible', false);
    end if;

    -- A recipient-wide owner clearance is an audited re-consent or false-
    -- positive correction. Once no active suppression remains, a new,
    -- rate-limited recovery request may reopen this specific recovery email.
    update private.email_deliveries
    set
      status = 'pending',
      attempt_count = 0,
      provider_generation = provider_generation + 1,
      provider_request_hash = null,
      provider_message_id = null,
      sending_started_at = null,
      next_attempt_at = null,
      sent_at = null,
      delivered_at = null,
      bounced_at = null,
      complained_at = null,
      last_error_code = null
    where id = v_delivery.id;

    v_delivery.status := 'pending';
  end if;

  if found and v_delivery.status = 'suppressed' then
    if v_delivery.recipient_hash is distinct from p_recipient_hash
      or v_delivery.last_error_code is null
      or v_delivery.last_error_code not in (
        'EMAIL_RETRY_LIMIT_REACHED',
        'RESEND_SEND_FAILED',
        'RESEND_EMAIL_FAILED',
        'WOOCOMMERCE_EMAIL_SEND_FAILED'
      ) then
      return jsonb_build_object('eligible', false);
    end if;

    -- A fresh, rate-limited customer request may reopen only a transiently
    -- exhausted recovery delivery. Recipient bounce/complaint/provider
    -- suppressions require the audited owner-clearance path above, and
    -- lifecycle suppressions stay closed.
    update private.email_deliveries
    set
      status = 'pending',
      attempt_count = 0,
      provider_generation = provider_generation + 1,
      provider_request_hash = null,
      provider_message_id = null,
      sending_started_at = null,
      next_attempt_at = null,
      sent_at = null,
      delivered_at = null,
      bounced_at = null,
      complained_at = null,
      last_error_code = null
    where id = v_delivery.id;

    v_delivery.status := 'pending';
  end if;

  if not found then
    insert into private.email_deliveries (
      reading_id,
      access_grant_id,
      message_kind,
      template_version,
      recipient_hash,
      status
    )
    values (
      v_commerce_order.reading_id,
      v_grant.id,
      'access_recovery',
      v_recovery_template_version,
      p_recipient_hash,
      'pending'
    );
  elsif v_delivery.status in ('sent', 'delivered') then
    update private.email_deliveries
    set
      access_grant_id = v_grant.id,
      recipient_hash = p_recipient_hash,
      status = 'pending',
      attempt_count = 0,
      provider_generation = provider_generation + 1,
      provider_request_hash = null,
      provider_message_id = null,
      sending_started_at = null,
      next_attempt_at = null,
      sent_at = null,
      delivered_at = null,
      last_error_code = null
    where id = v_delivery.id;
  end if;

  return jsonb_build_object(
    'eligible', true,
    'reading_id', v_commerce_order.reading_id,
    'billing_email', v_commerce_order.billing_email,
    'order_number', v_commerce_order.order_number,
    'provider_order_id', v_commerce_order.provider_order_id,
    'grant_id', v_grant.id,
    'grant_expires_at', v_grant.expires_at,
    'reading_status', v_reading_status
  );
end;
$$;

create or replace function public.valley_email_reconciliation_candidates(
  p_intake_template_version text,
  p_result_template_version text,
  p_limit integer
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_candidates jsonb;
begin
  if p_intake_template_version is null
    or p_intake_template_version !~ '^[A-Za-z0-9._:-]{1,120}$'
    or p_result_template_version is null
    or p_result_template_version !~ '^[A-Za-z0-9._:-]{1,120}$'
    or p_limit is null
    or p_limit < 1
    or p_limit > 20 then
    raise exception 'INVALID_EMAIL_RECONCILIATION_REQUEST' using errcode = '22023';
  end if;

  update private.email_deliveries
  set
    status = 'suppressed',
    last_error_code = coalesce(last_error_code, 'EMAIL_RETRY_LIMIT_REACHED'),
    next_attempt_at = null
  where attempt_count >= 5
    and (
      status = 'failed'
      or (
        status = 'sending'
        and sending_started_at <= now() - interval '5 minutes'
      )
    );

  with candidates as (
    select
      0 as priority,
      reading.created_at,
      'result_ready'::text as message_kind,
      p_result_template_version as template_version,
      reading.id as reading_id,
      commerce_order.billing_email,
      commerce_order.order_number,
      commerce_order.provider_order_id,
      access_grant.id as grant_id,
      access_grant.expires_at as grant_expires_at
    from private.readings as reading
    join private.commerce_orders as commerce_order
      on commerce_order.reading_id = reading.id
    join private.reading_access_grants as access_grant
      on access_grant.reading_id = reading.id
      and access_grant.revoked_at is null
      and access_grant.expires_at > now()
    join private.reading_results as result
      on result.reading_id = reading.id
      and result.result_version = 1
      and result.revoked_at is null
    left join private.email_deliveries as delivery
      on delivery.reading_id = reading.id
      and delivery.message_kind = 'result_ready'
      and delivery.template_version = p_result_template_version
    where reading.status = 'ready'
      and commerce_order.normalized_status in ('processing', 'completed')
      and not exists (
        select 1
        from private.email_recipient_suppressions as suppression
        where suppression.recipient_hash = coalesce(
            delivery.recipient_hash,
            encode(
              extensions.digest(
                convert_to(commerce_order.billing_email, 'UTF8'),
                'sha256'
              ),
              'hex'
            )
          )
          and suppression.cleared_at is null
      )
      and (
        delivery.id is null
        or (
          delivery.status = 'failed'
          and delivery.attempt_count < 5
          and delivery.next_attempt_at <= now()
        )
        or (
          delivery.status = 'sending'
          and delivery.attempt_count < 5
          and delivery.sending_started_at <= now() - interval '5 minutes'
        )
      )

    union all

    select
      2 as priority,
      reading.created_at,
      'intake_invitation'::text as message_kind,
      p_intake_template_version as template_version,
      reading.id as reading_id,
      commerce_order.billing_email,
      commerce_order.order_number,
      commerce_order.provider_order_id,
      access_grant.id as grant_id,
      access_grant.expires_at as grant_expires_at
    from private.readings as reading
    join private.commerce_orders as commerce_order
      on commerce_order.reading_id = reading.id
    join private.reading_access_grants as access_grant
      on access_grant.reading_id = reading.id
      and access_grant.revoked_at is null
      and access_grant.expires_at > now()
    left join private.email_deliveries as delivery
      on delivery.reading_id = reading.id
      and delivery.message_kind = 'intake_invitation'
      and delivery.template_version = p_intake_template_version
    where reading.status in ('awaiting_intake', 'intake_in_progress')
      and commerce_order.normalized_status in ('processing', 'completed')
      and not exists (
        select 1
        from private.email_recipient_suppressions as suppression
        where suppression.recipient_hash = coalesce(
            delivery.recipient_hash,
            encode(
              extensions.digest(
                convert_to(commerce_order.billing_email, 'UTF8'),
                'sha256'
              ),
              'hex'
            )
          )
          and suppression.cleared_at is null
      )
      and (
        delivery.id is null
        or (
          delivery.status = 'failed'
          and delivery.attempt_count < 5
          and delivery.next_attempt_at <= now()
        )
        or (
          delivery.status = 'sending'
          and delivery.attempt_count < 5
          and delivery.sending_started_at <= now() - interval '5 minutes'
        )
      )

    union all

    select
      1 as priority,
      delivery.created_at,
      'access_recovery'::text as message_kind,
      delivery.template_version,
      reading.id as reading_id,
      commerce_order.billing_email,
      commerce_order.order_number,
      commerce_order.provider_order_id,
      access_grant.id as grant_id,
      access_grant.expires_at as grant_expires_at
    from private.email_deliveries as delivery
    join private.readings as reading on reading.id = delivery.reading_id
    join private.commerce_orders as commerce_order
      on commerce_order.reading_id = reading.id
    join private.reading_access_grants as access_grant
      on access_grant.id = delivery.access_grant_id
      and access_grant.reading_id = reading.id
      and access_grant.revoked_at is null
      and access_grant.expires_at > now()
    where delivery.message_kind = 'access_recovery'
      and reading.status not in ('refunded', 'revoked', 'erased')
      and commerce_order.normalized_status in ('processing', 'completed')
      and not exists (
        select 1
        from private.email_recipient_suppressions as suppression
        where suppression.recipient_hash = delivery.recipient_hash
          and suppression.cleared_at is null
      )
      and (
        delivery.status = 'pending'
        or (
          delivery.status = 'failed'
          and delivery.attempt_count < 5
          and delivery.next_attempt_at <= now()
        )
        or (
          delivery.status = 'sending'
          and delivery.attempt_count < 5
          and delivery.sending_started_at <= now() - interval '5 minutes'
        )
      )
  ),
  limited_candidates as (
    select *
    from candidates
    order by priority, created_at
    limit p_limit
  )
  select coalesce(
    jsonb_agg(
      jsonb_build_object(
        'message_kind', candidate.message_kind,
        'template_version', candidate.template_version,
        'reading_id', candidate.reading_id,
        'billing_email', candidate.billing_email,
        'order_number', candidate.order_number,
        'provider_order_id', candidate.provider_order_id,
        'grant_id', candidate.grant_id,
        'grant_expires_at', candidate.grant_expires_at
      )
      order by candidate.priority, candidate.created_at
    ),
    '[]'::jsonb
  )
  into v_candidates
  from limited_candidates as candidate;

  return v_candidates;
end;
$$;

create or replace function public.valley_store_reading_result(
  p_fulfillment_id uuid,
  p_reading_id uuid,
  p_worker_id text,
  p_attempt_count integer,
  p_candidate_grant_id uuid,
  p_candidate_grant_expires_at timestamptz,
  p_contract_version text,
  p_result_payload jsonb,
  p_result_hash text,
  p_source_fingerprints jsonb,
  p_runtime_version text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_fulfillment private.fulfillments%rowtype;
  v_commerce_order private.commerce_orders%rowtype;
  v_grant private.reading_access_grants%rowtype;
  v_existing_hash text;
  v_reading_status text;
begin
  if p_candidate_grant_id is null
    or p_candidate_grant_expires_at is null
    or p_candidate_grant_expires_at <= now() + interval '1 day'
    or p_candidate_grant_expires_at > now() + interval '91 days' then
    raise exception 'INVALID_REPLACEMENT_GRANT_EXPIRY' using errcode = '22023';
  end if;

  perform pg_advisory_xact_lock(hashtextextended(p_fulfillment_id::text, 0));

  select commerce_order.* into v_commerce_order
  from private.fulfillments as fulfillment
  join private.commerce_orders as commerce_order
    on commerce_order.id = fulfillment.commerce_order_id
  where fulfillment.id = p_fulfillment_id
    and fulfillment.reading_id = p_reading_id
  for update of commerce_order;

  if not found then
    raise exception 'FULFILLMENT_NOT_FOUND' using errcode = 'P0001';
  end if;

  select * into v_fulfillment
  from private.fulfillments
  where id = p_fulfillment_id
    and reading_id = p_reading_id
  for update;

  if not found then
    raise exception 'FULFILLMENT_NOT_FOUND' using errcode = 'P0001';
  end if;

  select status into v_reading_status
  from private.readings
  where id = p_reading_id
  for update;

  if v_reading_status in ('refunded', 'revoked', 'erased') then
    raise exception 'READING_ACCESS_REVOKED' using errcode = 'P0001';
  end if;

  perform 1
  from private.reading_access_grants
  where reading_id = p_reading_id
    and revoked_at is null
  for update;

  select result_hash into v_existing_hash
  from private.reading_results
  where reading_id = p_reading_id
    and result_version = 1
  for update;

  if v_existing_hash is not null and v_existing_hash <> p_result_hash then
    raise exception 'RESULT_ALREADY_STORED' using errcode = 'P0001';
  end if;

  if v_existing_hash is null then
    if v_fulfillment.status <> 'generating'
      or v_fulfillment.lease_owner is distinct from p_worker_id
      or v_fulfillment.attempt_count is distinct from p_attempt_count
      or v_fulfillment.lease_expires_at is null
      or v_fulfillment.lease_expires_at <= now() then
      raise exception 'FULFILLMENT_LEASE_MISMATCH' using errcode = 'P0001';
    end if;

    insert into private.reading_results (
      reading_id,
      result_version,
      contract_version,
      result_payload,
      result_hash,
      source_fingerprints
    )
    values (
      p_reading_id,
      1,
      p_contract_version,
      p_result_payload,
      p_result_hash,
      coalesce(p_source_fingerprints, '{}'::jsonb)
    );

    update private.fulfillments
    set
      status = 'ready',
      lease_owner = null,
      lease_expires_at = null,
      next_attempt_at = null,
      runtime_version = p_runtime_version,
      result_contract_version = p_contract_version,
      ready_at = coalesce(ready_at, now())
    where id = p_fulfillment_id;

    update private.readings
    set status = case when status = 'delivered' then 'delivered' else 'ready' end
    where id = p_reading_id
      and status not in ('refunded', 'revoked', 'erased');
  end if;

  select * into v_grant
  from private.reading_access_grants
  where reading_id = p_reading_id
    and revoked_at is null
    and expires_at > now() + interval '1 day'
  order by created_at desc
  limit 1;

  if not found then
    update private.reading_access_grants
    set revoked_at = coalesce(revoked_at, now())
    where reading_id = p_reading_id
      and revoked_at is null;

    update private.email_deliveries
    set
      status = 'suppressed',
      provider_generation = provider_generation + 1,
      provider_message_id = null,
      sending_started_at = null,
      next_attempt_at = null,
      last_error_code = 'ACCESS_GRANT_ROTATED'
    where reading_id = p_reading_id
      and status in ('pending', 'sending', 'sent', 'failed')
      and exists (
        select 1
        from private.reading_access_grants as retired_grant
        where retired_grant.id = email_deliveries.access_grant_id
          and retired_grant.reading_id = p_reading_id
          and retired_grant.revoked_at is not null
      );

    insert into private.reading_access_grants (
      id,
      reading_id,
      expires_at
    )
    values (
      p_candidate_grant_id,
      p_reading_id,
      date_trunc('second', p_candidate_grant_expires_at)
    )
    returning * into v_grant;
  end if;

  return jsonb_build_object(
    'duplicate_result', v_existing_hash is not null,
    'reading_id', p_reading_id,
    'billing_email', v_commerce_order.billing_email,
    'order_number', v_commerce_order.order_number,
    'provider_order_id', v_commerce_order.provider_order_id,
    'grant_id', v_grant.id,
    'grant_expires_at', v_grant.expires_at
  );
end;
$$;

create or replace function private.valley_execute_reading_privacy_action(
  p_action_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_action private.reading_privacy_actions%rowtype;
  v_commerce_order private.commerce_orders%rowtype;
  v_reading_status text;
  v_already_erased boolean;
  v_erased_at timestamptz := now();
  v_action_completed_at timestamptz;
  v_intake_rows integer := 0;
  v_result_rows integer := 0;
begin
  select * into v_action
  from private.reading_privacy_actions
  where id = p_action_id
  for update;

  if not found then
    raise exception 'PRIVACY_ACTION_NOT_FOUND' using errcode = 'P0001';
  end if;

  if v_action.status in ('completed', 'skipped') then
    return jsonb_build_object(
      'completed', true,
      'duplicate', true,
      'skipped', v_action.status = 'skipped',
      'action_id', v_action.id,
      'reading_id', v_action.reading_id,
      'completed_at', v_action.completed_at
    );
  end if;

  if v_action.status not in ('pending', 'failed') then
    raise exception 'PRIVACY_ACTION_IN_PROGRESS' using errcode = 'P0001';
  end if;

  if v_action.action_kind = 'scheduled_retention'
    and not exists (
      select 1
      from private.reading_retention_policies
      where version = v_action.policy_version
        and enabled
    ) then
    raise exception 'RETENTION_POLICY_NOT_ENABLED' using errcode = 'P0001';
  end if;

  perform pg_advisory_xact_lock(
    hashtextextended('reading-content-erasure:' || v_action.reading_id::text, 0)
  );

  update private.reading_privacy_actions
  set
    status = 'running',
    started_at = now(),
    completed_at = null,
    error_code = null
  where id = v_action.id;

  begin
    select commerce_order.* into v_commerce_order
    from private.commerce_orders as commerce_order
    where commerce_order.id = v_action.commerce_order_id
      and commerce_order.reading_id = v_action.reading_id
    for update;

    if not found then
      raise exception 'PRIVACY_ACTION_COMMERCE_MISMATCH' using errcode = 'P0001';
    end if;

    perform 1
    from private.fulfillments
    where reading_id = v_action.reading_id
    for update;

    select status, personal_data_erased_at is not null
      into v_reading_status, v_already_erased
    from private.readings
    where id = v_action.reading_id
    for update;

    if not found then
      raise exception 'READING_NOT_FOUND' using errcode = 'P0001';
    end if;

    perform 1
    from private.reading_retention_holds
    where reading_id = v_action.reading_id
      and released_at is null
    for update;

    if found then
      raise exception 'READING_RETENTION_HOLD_ACTIVE' using errcode = 'P0001';
    end if;

    perform 1
    from private.reading_access_grants
    where reading_id = v_action.reading_id
    for update;

    perform 1
    from private.reading_intakes
    where reading_id = v_action.reading_id
    for update;

    perform 1
    from private.reading_results
    where reading_id = v_action.reading_id
    for update;

    perform 1
    from private.email_deliveries
    where reading_id = v_action.reading_id
    for update;

    if v_action.action_kind = 'scheduled_retention'
      and not exists (
        select 1
        from private.reading_retention_due(v_action.policy_version)
        where reading_id = v_action.reading_id
          and commerce_order_id = v_action.commerce_order_id
      ) then
      update private.reading_privacy_actions
      set
        status = 'skipped',
        previous_reading_status =
          coalesce(previous_reading_status, v_reading_status),
        error_code = 'RETENTION_NO_LONGER_DUE',
        completed_at = now()
      where id = v_action.id
      returning completed_at into v_action_completed_at;

      return jsonb_build_object(
        'completed', true,
        'duplicate', false,
        'skipped', true,
        'action_id', v_action.id,
        'reading_id', v_action.reading_id,
        'completed_at', v_action_completed_at
      );
    end if;

    perform set_config('valley.privacy_action_id', v_action.id::text, true);

    if not v_already_erased then
      update private.reading_access_grants
      set
        revoked_at = coalesce(revoked_at, v_erased_at),
        token_hash = null,
        last_used_at = null
      where reading_id = v_action.reading_id;

      update private.email_deliveries
      set
        status = case
          when status in ('pending', 'sending', 'sent', 'failed')
            then 'suppressed'
          else status
        end,
        provider_generation = provider_generation + case
          when status in ('pending', 'sending', 'sent', 'failed') then 1
          else 0
        end,
        provider_message_id = case
          when status in ('pending', 'sending', 'sent', 'failed') then null
          else provider_message_id
        end,
        sending_started_at = null,
        next_attempt_at = null,
        last_error_code = case
          when status in ('pending', 'sending', 'sent', 'failed')
            then 'READING_CONTENT_ERASED'
          else last_error_code
        end
      where reading_id = v_action.reading_id;

      update private.fulfillments
      set
        status = 'revoked',
        last_error_code = 'READING_CONTENT_ERASED',
        lease_owner = null,
        lease_expires_at = null,
        next_attempt_at = null
      where reading_id = v_action.reading_id;

      update private.reading_intakes
      set
        draft_payload = '{}'::jsonb,
        final_payload = null,
        precision_snapshot = null,
        erased_at = v_erased_at
      where reading_id = v_action.reading_id
        and erased_at is null;
      get diagnostics v_intake_rows = row_count;

      update private.reading_results
      set
        result_payload = '{}'::jsonb,
        result_hash = null,
        source_fingerprints = '{}'::jsonb,
        revoked_at = coalesce(revoked_at, v_erased_at),
        erased_at = v_erased_at
      where reading_id = v_action.reading_id
        and erased_at is null;
      get diagnostics v_result_rows = row_count;

      update private.readings
      set
        status = 'erased',
        personal_data_erased_at = v_erased_at
      where id = v_action.reading_id;
    end if;

    update private.reading_privacy_actions
    set
      status = 'completed',
      previous_reading_status = coalesce(previous_reading_status, v_reading_status),
      erased_components = array[
        'access_grants',
        'intake_payloads',
        'result_payloads',
        'active_delivery_attempts'
      ],
      intake_rows_scrubbed = v_intake_rows,
      result_rows_scrubbed = v_result_rows,
      error_code = null,
      completed_at = now()
    where id = v_action.id
    returning completed_at into v_action_completed_at;
  exception
    when others then
      update private.reading_privacy_actions
      set
        status = 'failed',
        error_code = 'SQLSTATE_' || sqlstate,
        completed_at = now()
      where id = v_action.id;

      return jsonb_build_object(
        'completed', false,
        'duplicate', false,
        'action_id', v_action.id,
        'reading_id', v_action.reading_id,
        'error_code', 'PRIVACY_ACTION_FAILED'
      );
  end;

  return jsonb_build_object(
    'completed', true,
    'duplicate', v_already_erased,
    'skipped', false,
    'action_id', v_action.id,
    'reading_id', v_action.reading_id,
    'completed_at', v_action_completed_at,
    'intake_rows_scrubbed', v_intake_rows,
    'result_rows_scrubbed', v_result_rows
  );
end;
$$;

create or replace function private.valley_clear_email_recipient_suppression(
  p_recipient_hash text,
  p_expected_suppression_kind text,
  p_cleared_by_hash text,
  p_clear_reason_code text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_suppression private.email_recipient_suppressions%rowtype;
begin
  if p_recipient_hash is null
    or p_recipient_hash !~ '^[0-9a-f]{64}$'
    or p_expected_suppression_kind is null
    or p_expected_suppression_kind not in (
      'bounced',
      'complained',
      'suppressed'
    )
    or p_cleared_by_hash is null
    or p_cleared_by_hash !~ '^[0-9a-f]{64}$'
    or p_clear_reason_code is null
    or p_clear_reason_code !~ '^[A-Z0-9_]{3,80}$' then
    raise exception 'INVALID_EMAIL_SUPPRESSION_CLEAR'
      using errcode = '22023';
  end if;

  perform pg_advisory_xact_lock(
    hashtextextended('email-recipient:' || p_recipient_hash, 0)
  );

  select * into v_suppression
  from private.email_recipient_suppressions
  where recipient_hash = p_recipient_hash
    and cleared_at is null
  for update;

  if not found then
    return jsonb_build_object('cleared', false);
  end if;

  if v_suppression.suppression_kind is distinct from
      p_expected_suppression_kind then
    raise exception 'EMAIL_SUPPRESSION_KIND_CHANGED'
      using errcode = 'P0001';
  end if;

  update private.email_recipient_suppressions
  set
    cleared_at = now(),
    cleared_by_hash = p_cleared_by_hash,
    clear_reason_code = p_clear_reason_code
  where id = v_suppression.id;

  return jsonb_build_object(
    'cleared', true,
    'suppression_id', v_suppression.id,
    'suppression_kind', v_suppression.suppression_kind
  );
end;
$$;

create or replace function private.valley_correct_reading_billing_email(
  p_commerce_order_id uuid,
  p_expected_email_hash text,
  p_corrected_email text,
  p_actor_hash text,
  p_verification_reference_hash text,
  p_reason_code text,
  p_idempotency_key text,
  p_replacement_grant_id uuid,
  p_replacement_grant_expires_at timestamptz,
  p_recovery_template_version text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_existing private.reading_contact_corrections%rowtype;
  v_commerce_order private.commerce_orders%rowtype;
  v_reading_status text;
  v_corrected_email text;
  v_previous_hash text;
  v_corrected_hash text;
  v_correction_id uuid;
  v_provider_order_id text;
begin
  -- Deliberately disabled. The app sends through the Woo order, so changing
  -- only this database would claim one recipient while Woo emails another.
  -- Re-enable only with an audited Woo-first update that also renews the
  -- WordPress email-confirmation proof and is revalidated before this RPC.
  raise exception 'CONTACT_CORRECTION_UNSUPPORTED'
    using errcode = 'P0001';

  v_corrected_email := lower(trim(p_corrected_email));
  if p_expected_email_hash is null
    or p_expected_email_hash !~ '^[0-9a-f]{64}$'
    or p_actor_hash is null
    or p_actor_hash !~ '^[0-9a-f]{64}$'
    or p_verification_reference_hash is null
    or p_verification_reference_hash !~ '^[0-9a-f]{64}$'
    or p_reason_code is null
    or p_reason_code !~ '^[A-Z0-9_]{3,80}$'
    or p_idempotency_key is null
    or p_idempotency_key !~ '^[A-Za-z0-9._:-]{8,160}$'
    or p_replacement_grant_id is null
    or p_replacement_grant_expires_at is null
    or p_replacement_grant_expires_at <= now() + interval '1 day'
    or p_replacement_grant_expires_at > now() + interval '91 days'
    or p_recovery_template_version is null
    or p_recovery_template_version <>
      'paid-access-recovery-v1:' || p_replacement_grant_id::text
    or p_corrected_email is null
    or v_corrected_email !~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$' then
    raise exception 'INVALID_CONTACT_CORRECTION' using errcode = '22023';
  end if;

  v_corrected_hash := encode(
    extensions.digest(convert_to(v_corrected_email, 'UTF8'), 'sha256'),
    'hex'
  );
  if v_corrected_hash = p_expected_email_hash then
    raise exception 'CONTACT_CORRECTION_UNCHANGED' using errcode = '22023';
  end if;

  perform pg_advisory_xact_lock(
    hashtextextended('contact-correction:' || p_idempotency_key, 0)
  );

  select * into v_existing
  from private.reading_contact_corrections
  where idempotency_key = p_idempotency_key;

  if found then
    if v_existing.commerce_order_id is distinct from p_commerce_order_id
      or v_existing.previous_email_hash is distinct from p_expected_email_hash
      or v_existing.corrected_email_hash is distinct from v_corrected_hash
      or v_existing.actor_hash is distinct from p_actor_hash
      or v_existing.verification_reference_hash is distinct from
        p_verification_reference_hash
      or v_existing.reason_code is distinct from p_reason_code
      or v_existing.replacement_grant_id is distinct from
        p_replacement_grant_id
      or v_existing.replacement_grant_expires_at is distinct from
        date_trunc('second', p_replacement_grant_expires_at)
      or v_existing.recovery_template_version is distinct from
        p_recovery_template_version then
      raise exception 'CONTACT_CORRECTION_IDEMPOTENCY_CONFLICT'
        using errcode = 'P0001';
    end if;

    return jsonb_build_object(
      'corrected', true,
      'duplicate', true,
      'correction_id', v_existing.id,
      'reading_id', v_existing.reading_id,
      'grant_id', v_existing.replacement_grant_id,
      'grant_expires_at', v_existing.replacement_grant_expires_at
    );
  end if;

  perform pg_advisory_xact_lock(
    hashtextextended('email-recipient:' || v_corrected_hash, 0)
  );

  if exists (
    select 1
    from private.email_recipient_suppressions
    where recipient_hash = v_corrected_hash
      and cleared_at is null
  ) then
    raise exception 'CONTACT_CORRECTION_EMAIL_SUPPRESSED'
      using errcode = 'P0001';
  end if;

  select provider_order_id into v_provider_order_id
  from private.commerce_orders
  where id = p_commerce_order_id;

  if v_provider_order_id is null then
    raise exception 'CONTACT_CORRECTION_ORDER_UNAVAILABLE'
      using errcode = 'P0001';
  end if;

  perform pg_advisory_xact_lock(
    hashtextextended('woocommerce:' || v_provider_order_id, 0)
  );

  select * into v_commerce_order
  from private.commerce_orders
  where id = p_commerce_order_id
  for update;

  if not found
    or v_commerce_order.normalized_status not in ('processing', 'completed') then
    raise exception 'CONTACT_CORRECTION_ORDER_UNAVAILABLE'
      using errcode = 'P0001';
  end if;

  perform 1
  from private.fulfillments
  where reading_id = v_commerce_order.reading_id
  for update;

  select status into v_reading_status
  from private.readings
  where id = v_commerce_order.reading_id
  for update;

  if v_reading_status in ('refunded', 'revoked', 'erased') then
    raise exception 'CONTACT_CORRECTION_READING_UNAVAILABLE'
      using errcode = 'P0001';
  end if;

  perform 1
  from private.reading_access_grants
  where reading_id = v_commerce_order.reading_id
  for update;

  perform 1
  from private.email_deliveries
  where reading_id = v_commerce_order.reading_id
  for update;

  v_previous_hash := encode(
    extensions.digest(
      convert_to(v_commerce_order.billing_email, 'UTF8'),
      'sha256'
    ),
    'hex'
  );
  if v_previous_hash <> p_expected_email_hash then
    raise exception 'CONTACT_CORRECTION_EMAIL_CHANGED'
      using errcode = 'P0001';
  end if;

  update private.commerce_orders
  set billing_email = v_corrected_email
  where id = v_commerce_order.id;

  update private.reading_access_grants
  set
    revoked_at = coalesce(revoked_at, now()),
    token_hash = null,
    last_used_at = null
  where reading_id = v_commerce_order.reading_id
    and revoked_at is null;

  update private.email_deliveries
  set
    status = case
      when status in ('pending', 'sending', 'sent', 'failed')
        then 'suppressed'
      else status
    end,
    provider_generation = provider_generation + case
      when status in ('pending', 'sending', 'sent', 'failed') then 1
      else 0
    end,
    provider_message_id = case
      when status in ('pending', 'sending', 'sent', 'failed') then null
      else provider_message_id
    end,
    sending_started_at = null,
    next_attempt_at = null,
    last_error_code = case
      when status in ('pending', 'sending', 'sent', 'failed')
        then 'BILLING_EMAIL_CORRECTED'
      else last_error_code
    end
  where reading_id = v_commerce_order.reading_id;

  insert into private.reading_access_grants (
    id,
    reading_id,
    expires_at
  )
  values (
    p_replacement_grant_id,
    v_commerce_order.reading_id,
    date_trunc('second', p_replacement_grant_expires_at)
  );

  insert into private.email_deliveries (
    reading_id,
    access_grant_id,
    message_kind,
    template_version,
    recipient_hash,
    status
  )
  values (
    v_commerce_order.reading_id,
    p_replacement_grant_id,
    'access_recovery',
    p_recovery_template_version,
    v_corrected_hash,
    'pending'
  );

  insert into private.reading_contact_corrections (
    commerce_order_id,
    reading_id,
    idempotency_key,
    previous_email_hash,
    corrected_email_hash,
    actor_hash,
    verification_reference_hash,
    reason_code,
    replacement_grant_id,
    replacement_grant_expires_at,
    recovery_template_version
  )
  values (
    v_commerce_order.id,
    v_commerce_order.reading_id,
    p_idempotency_key,
    v_previous_hash,
    v_corrected_hash,
    p_actor_hash,
    p_verification_reference_hash,
    p_reason_code,
    p_replacement_grant_id,
    date_trunc('second', p_replacement_grant_expires_at),
    p_recovery_template_version
  )
  returning id into v_correction_id;

  return jsonb_build_object(
    'corrected', true,
    'duplicate', false,
    'correction_id', v_correction_id,
    'reading_id', v_commerce_order.reading_id,
    'grant_id', p_replacement_grant_id,
    'grant_expires_at',
      date_trunc('second', p_replacement_grant_expires_at)
  );
end;
$$;

create or replace function private.valley_run_reading_retention_batch(
  p_policy_version text,
  p_actor_hash text,
  p_limit integer
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_run_id uuid;
  v_policy private.reading_retention_policies%rowtype;
  v_due record;
  v_action_id uuid;
  v_action_key text;
  v_action_result jsonb;
  v_scanned integer := 0;
  v_staged integer := 0;
  v_completed integer := 0;
  v_skipped integer := 0;
  v_failed integer := 0;
  v_remaining integer := 0;
begin
  if p_policy_version is null
    or p_policy_version !~ '^[A-Za-z0-9._:-]{3,80}$'
    or p_actor_hash is null
    or p_actor_hash !~ '^[0-9a-f]{64}$'
    or p_limit is null
    or p_limit < 1
    or p_limit > 100 then
    raise exception 'INVALID_RETENTION_RUN_REQUEST' using errcode = '22023';
  end if;

  if not pg_try_advisory_xact_lock(
    hashtextextended('reading-retention:' || p_policy_version, 0)
  ) then
    return jsonb_build_object('acquired', false);
  end if;

  select * into v_policy
  from private.reading_retention_policies
  where version = p_policy_version
    and enabled
    and anchor_version = 'reading-retention-anchor-v1';

  if not found then
    raise exception 'RETENTION_POLICY_NOT_ENABLED' using errcode = 'P0001';
  end if;

  insert into private.reading_retention_runs (
    policy_version,
    actor_hash,
    policy_snapshot,
    status
  )
  values (
    p_policy_version,
    p_actor_hash,
    jsonb_build_object(
      'anchor_version', v_policy.anchor_version,
      'approved_at', v_policy.approved_at,
      'approved_by_hash', v_policy.approved_by_hash,
      'delivered_after', v_policy.delivered_after::text,
      'incomplete_after', v_policy.incomplete_after::text,
      'revoked_after', v_policy.revoked_after::text,
      'run_cadence', v_policy.run_cadence::text
    ),
    'running'
  )
  returning id into v_run_id;

  begin
    for v_due in
      select *
      from private.reading_retention_due(p_policy_version)
      limit p_limit
    loop
      v_scanned := v_scanned + 1;
      v_action_id := null;
      v_action_key :=
        'retention:' || p_policy_version || ':' ||
        v_due.reading_id::text || ':' ||
        floor(extract(epoch from v_due.due_at) * 1000000)::bigint::text;

      insert into private.reading_privacy_actions (
        reading_id,
        commerce_order_id,
        idempotency_key,
        action_kind,
        actor_hash,
        reason_code,
        policy_version,
        status
      )
      values (
        v_due.reading_id,
        v_due.commerce_order_id,
        v_action_key,
        'scheduled_retention',
        p_actor_hash,
        'RETENTION_POLICY_DUE',
        p_policy_version,
        'pending'
      )
      on conflict (idempotency_key) do nothing
      returning id into v_action_id;

      if v_action_id is not null then
        v_staged := v_staged + 1;
      else
        select id into v_action_id
        from private.reading_privacy_actions
        where idempotency_key = v_action_key;
      end if;

      if v_action_id is null then
        v_failed := v_failed + 1;
        continue;
      end if;

      v_action_result :=
        private.valley_execute_reading_privacy_action(v_action_id);
      if coalesce((v_action_result ->> 'skipped')::boolean, false) then
        v_skipped := v_skipped + 1;
      elsif coalesce((v_action_result ->> 'completed')::boolean, false) then
        v_completed := v_completed + 1;
      else
        v_failed := v_failed + 1;
      end if;
    end loop;

    select count(*)::integer into v_remaining
    from private.reading_retention_due(p_policy_version);

    update private.reading_retention_runs
    set
      status = case when v_failed = 0 then 'completed' else 'failed' end,
      scanned_readings = v_scanned,
      staged_actions = v_staged,
      completed_actions = v_completed,
      skipped_actions = v_skipped,
      failed_actions = v_failed,
      overdue_remaining = v_remaining,
      error_code = case
        when v_failed > 0 then 'RETENTION_ACTION_FAILED'
        else null
      end,
      finished_at = now()
    where id = v_run_id;
  exception
    when others then
      update private.reading_retention_runs
      set
        status = 'failed',
        scanned_readings = v_scanned,
        staged_actions = v_staged,
        completed_actions = v_completed,
        skipped_actions = v_skipped,
        failed_actions = greatest(v_failed, 1),
        overdue_remaining = v_remaining,
        error_code = 'SQLSTATE_' || sqlstate,
        finished_at = now()
      where id = v_run_id;

      return jsonb_build_object(
        'acquired', true,
        'completed', false,
        'run_id', v_run_id,
        'error_code', 'RETENTION_RUN_FAILED'
      );
  end;

  return jsonb_build_object(
    'acquired', true,
    'completed', v_failed = 0,
    'run_id', v_run_id,
    'scanned_readings', v_scanned,
    'staged_actions', v_staged,
    'completed_actions', v_completed,
    'skipped_actions', v_skipped,
    'failed_actions', v_failed,
    'overdue_remaining', v_remaining
  );
end;
$$;

revoke all on schema private from service_role;
revoke all on all tables in schema private from public, anon, authenticated, service_role;
revoke all on all sequences in schema private from public, anon, authenticated, service_role;
revoke all on all functions in schema private from public, anon, authenticated, service_role;

revoke all on function public.valley_paid_access_health(text, integer, integer) from public, anon, authenticated;
revoke all on function public.valley_get_email_commerce_snapshot(uuid) from public, anon, authenticated;
revoke all on function public.valley_begin_woocommerce_reconciliation(uuid, integer, integer, integer) from public, anon, authenticated;
revoke all on function public.valley_finish_woocommerce_reconciliation(uuid, uuid, integer, boolean, integer, integer, integer, integer, integer) from public, anon, authenticated;
revoke all on function public.valley_fail_woocommerce_reconciliation(uuid, uuid, text) from public, anon, authenticated;
revoke all on function public.valley_take_rate_limit(text, text, integer, integer) from public, anon, authenticated;
revoke all on function public.valley_record_woocommerce_event(text, text, text, text, text, text) from public, anon, authenticated;
revoke all on function public.valley_process_paid_woocommerce_order(text, text, text, text, text, bigint, bigint, text, text, text, timestamptz, text, text, text, timestamptz, text, text, timestamptz, uuid, timestamptz) from public, anon, authenticated;
revoke all on function public.valley_revoke_paid_woocommerce_order(text, text, text, text, boolean, text, timestamptz) from public, anon, authenticated;
revoke all on function public.valley_set_access_grant_token_hash(uuid, text) from public, anon, authenticated;
revoke all on function public.valley_get_paid_reading(uuid, text, timestamptz) from public, anon, authenticated;
revoke all on function public.valley_save_reading_intake_draft(uuid, text, timestamptz, jsonb) from public, anon, authenticated;
revoke all on function public.valley_submit_reading_intake(uuid, text, timestamptz, text, jsonb, jsonb, text, timestamptz) from public, anon, authenticated;
revoke all on function public.valley_claim_reading_fulfillment(uuid, text, integer) from public, anon, authenticated;
revoke all on function public.valley_fail_reading_fulfillment(uuid, uuid, text, integer, boolean, text) from public, anon, authenticated;
revoke all on function public.valley_renew_reading_fulfillment_lease(uuid, uuid, text, integer, integer) from public, anon, authenticated;
revoke all on function public.valley_claim_email_delivery(uuid, uuid, text, text, text, text, text) from public, anon, authenticated;
revoke all on function public.valley_finish_email_delivery(uuid, uuid, integer, text, text, text, text) from public, anon, authenticated;
revoke all on function public.valley_record_resend_email_event(text, text, text, text, timestamptz) from public, anon, authenticated;
revoke all on function public.valley_recover_paid_reading(text, text, uuid, timestamptz, text, text) from public, anon, authenticated;
revoke all on function public.valley_email_reconciliation_candidates(text, text, integer) from public, anon, authenticated;
revoke all on function public.valley_store_reading_result(uuid, uuid, text, integer, uuid, timestamptz, text, jsonb, text, jsonb, text) from public, anon, authenticated;
revoke all on function private.valley_execute_reading_privacy_action(uuid) from public, anon, authenticated, service_role;

grant execute on function public.valley_paid_access_health(text, integer, integer) to service_role;
grant execute on function public.valley_get_email_commerce_snapshot(uuid) to service_role;
grant execute on function public.valley_begin_woocommerce_reconciliation(uuid, integer, integer, integer) to service_role;
grant execute on function public.valley_finish_woocommerce_reconciliation(uuid, uuid, integer, boolean, integer, integer, integer, integer, integer) to service_role;
grant execute on function public.valley_fail_woocommerce_reconciliation(uuid, uuid, text) to service_role;
grant execute on function public.valley_take_rate_limit(text, text, integer, integer) to service_role;
grant execute on function public.valley_record_woocommerce_event(text, text, text, text, text, text) to service_role;
grant execute on function public.valley_process_paid_woocommerce_order(text, text, text, text, text, bigint, bigint, text, text, text, timestamptz, text, text, text, timestamptz, text, text, timestamptz, uuid, timestamptz) to service_role;
grant execute on function public.valley_revoke_paid_woocommerce_order(text, text, text, text, boolean, text, timestamptz) to service_role;
grant execute on function public.valley_set_access_grant_token_hash(uuid, text) to service_role;
grant execute on function public.valley_get_paid_reading(uuid, text, timestamptz) to service_role;
grant execute on function public.valley_save_reading_intake_draft(uuid, text, timestamptz, jsonb) to service_role;
grant execute on function public.valley_submit_reading_intake(uuid, text, timestamptz, text, jsonb, jsonb, text, timestamptz) to service_role;
grant execute on function public.valley_claim_reading_fulfillment(uuid, text, integer) to service_role;
grant execute on function public.valley_fail_reading_fulfillment(uuid, uuid, text, integer, boolean, text) to service_role;
grant execute on function public.valley_renew_reading_fulfillment_lease(uuid, uuid, text, integer, integer) to service_role;
grant execute on function public.valley_claim_email_delivery(uuid, uuid, text, text, text, text, text) to service_role;
grant execute on function public.valley_finish_email_delivery(uuid, uuid, integer, text, text, text, text) to service_role;
grant execute on function public.valley_record_resend_email_event(text, text, text, text, timestamptz) to service_role;
grant execute on function public.valley_recover_paid_reading(text, text, uuid, timestamptz, text, text) to service_role;
grant execute on function public.valley_email_reconciliation_candidates(text, text, integer) to service_role;
grant execute on function public.valley_store_reading_result(uuid, uuid, text, integer, uuid, timestamptz, text, jsonb, text, jsonb, text) to service_role;
