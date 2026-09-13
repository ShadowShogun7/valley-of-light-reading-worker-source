create extension if not exists pg_cron;

do $$
declare
  v_policy_version constant text :=
    'reading-retention-v1-2026-07-31';
  v_approved_by_hash constant text :=
    'a612ba48dfb8039de8a1417823ea4f1ae1d67b31954c5f74c5e71ea20d055016';
  v_existing private.reading_retention_policies%rowtype;
begin
  if exists (
    select 1
    from private.reading_retention_policies
    where enabled
      and version <> v_policy_version
  ) then
    raise exception 'ANOTHER_RETENTION_POLICY_IS_ENABLED'
      using errcode = 'P0001';
  end if;

  select *
    into v_existing
  from private.reading_retention_policies
  where version = v_policy_version;

  if found then
    if v_existing.anchor_version is distinct from
        'reading-retention-anchor-v1'
      or v_existing.run_cadence is distinct from interval '1 hour'
      or v_existing.incomplete_after is distinct from interval '30 days'
      or v_existing.delivered_after is distinct from interval '365 days'
      or v_existing.revoked_after is distinct from interval '1 second'
      or v_existing.approved_by_hash is distinct from v_approved_by_hash
      or v_existing.approved_at is null then
      raise exception 'RETENTION_POLICY_VERSION_CONFLICT'
        using errcode = 'P0001';
    end if;

    update private.reading_retention_policies
    set enabled = true
    where version = v_policy_version
      and not enabled;
  else
    insert into private.reading_retention_policies (
      version,
      enabled,
      anchor_version,
      run_cadence,
      incomplete_after,
      delivered_after,
      revoked_after,
      approved_by_hash,
      approved_at
    )
    values (
      v_policy_version,
      true,
      'reading-retention-anchor-v1',
      interval '1 hour',
      interval '30 days',
      interval '365 days',
      interval '1 second',
      v_approved_by_hash,
      now()
    );
  end if;
end;
$$;

select cron.schedule(
  'valley-reading-retention-hourly',
  '7 * * * *',
  $retention$
    select private.valley_run_reading_retention_batch(
      'reading-retention-v1-2026-07-31',
      '177e5ada85b6bc68a1353de3e197f1120a785b4da58539d8b3d0b9697049cdb4',
      50
    );
  $retention$
);

do $$
declare
  v_result jsonb;
begin
  v_result := private.valley_run_reading_retention_batch(
    'reading-retention-v1-2026-07-31',
    '177e5ada85b6bc68a1353de3e197f1120a785b4da58539d8b3d0b9697049cdb4',
    5
  );

  if not coalesce((v_result ->> 'acquired')::boolean, false)
    or not coalesce((v_result ->> 'completed')::boolean, false)
    or coalesce((v_result ->> 'overdue_remaining')::integer, 1) <> 0 then
    raise exception 'INITIAL_RETENTION_RUN_NOT_CLEAN'
      using errcode = 'P0001',
        detail = v_result::text;
  end if;
end;
$$;
