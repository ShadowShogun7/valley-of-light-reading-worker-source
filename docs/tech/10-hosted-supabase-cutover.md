# 10 - Hosted Supabase Structured KB Cutover

Purpose: move structured KB runtime reads from compiled JSON to hosted Supabase without requiring local Supabase or Docker.

## Boundary

- Hosted staging is the first write target.
- Production writes require explicit approval and `--confirm-production`.
- The app still reads selected evidence through backend/runtime APIs. The frontend should not query KB runtime tables directly.
- The static migration check does not replace applying SQL to Supabase; it only checks the migration contract before the hosted write.

## Hosted Staging Flow

1. Run no-write local gates:

```bash
python3 scripts/check_supabase_migration_contract.py
python3 scripts/supabase_target_guard.py --env-file .env --target staging
python3 scripts/run_supabase_structured_runtime_cutover.py --env-file .env
```

The staging target must be explicit. Prefer setting this in the staging env:

```bash
VALLEY_SUPABASE_TARGET=staging
```

If the configured project is not explicitly labelled as staging, write commands
will stop before syncing.

2. Apply these migration files to the hosted staging Supabase project through the normal hosted SQL/migration path:

```text
supabase/migrations/20260525095713_add_structured_kb_runtime.sql
supabase/migrations/20260525112318_add_question_blueprint_version.sql
```

3. Confirm the hosted target has the required runtime tables:

```bash
python3 scripts/check_supabase_runtime_readiness.py --env-file .env
```

4. Sync published structured KB rows and validate live runtime reads:

```bash
python3 scripts/run_supabase_structured_runtime_cutover.py \
  --env-file .env \
  --sync \
  --allow-writes \
  --target staging \
  --prune \
  --validate-live
```

5. Run the Western complete-result flow API/UI gates:

```bash
python3 scripts/smoke_western_complete_result_flow.py
npm --prefix apps/web run typecheck
npm --prefix apps/web run build
```

6. Set the staging app runtime to Supabase-backed structured KB:

```bash
VALLEY_RUNTIME_ENV=staging
VALLEY_STRUCTURED_KB_SOURCE=supabase
VALLEY_SUPABASE_URL=...
VALLEY_SUPABASE_SERVICE_ROLE_KEY=...
```

Vercel Preview also defaults to Supabase if `VALLEY_STRUCTURED_KB_SOURCE` is
unset, but explicit `VALLEY_STRUCTURED_KB_SOURCE=supabase` is preferred for
staging.

## Production Flow

Production uses the same hosted process, but only after explicit launch/write approval.

```bash
python3 scripts/run_supabase_structured_runtime_cutover.py \
  --env-file .env.production \
  --sync \
  --allow-writes \
  --target production \
  --confirm-production \
  --prune \
  --validate-live
```

Before production sync, verify the staging run produced:

- no missing structured tables
- no structured count mismatches
- no stale runtime rows outside the compiled published set
- Western-only complete-result payload
- no BaZi runtime payload or visible copy in the astrology flow

## Why No Local Supabase

The project uses hosted Supabase as the database environment. Local tests stay on compiled JSON and static migration checks. Hosted Supabase readiness and live validation prove the DB-backed runtime once the migrations are applied.
