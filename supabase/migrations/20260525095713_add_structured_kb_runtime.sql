-- Store structured KB runtime records for deterministic readings.
--
-- These tables mirror the compiled JSON artifacts under dist/kb:
-- - kb_atoms.json
-- - kb_rules.json
-- - kb_question_blueprints.json
-- - kb_guardrails.json
--
-- They are intentionally service-role write/read only for now. The public app
-- should receive selected evidence through the application API, not direct KB
-- table access.

create table public.kb_atoms (
  id text primary key,
  system text not null,
  layer text not null,
  category text not null,
  label text not null,
  source_article_id text not null references public.kb_articles(id) on delete restrict,
  claim_ids text[] not null default '{}',
  applies_to jsonb not null default '{}'::jsonb,
  selectors jsonb not null default '{}'::jsonb,
  interpretation jsonb not null default '{}'::jsonb,
  path text not null,
  content_hash text not null,
  synced_at timestamptz not null default now(),
  constraint kb_atoms_system_check
    check (system in ('western', 'bazi', 'context', 'cross')),
  constraint kb_atoms_layer_check
    check (layer in ('identity', 'synastry', 'timing', 'precision', 'context')),
  constraint kb_atoms_applies_to_object_check
    check (jsonb_typeof(applies_to) = 'object'),
  constraint kb_atoms_selectors_object_check
    check (jsonb_typeof(selectors) = 'object'),
  constraint kb_atoms_interpretation_object_check
    check (jsonb_typeof(interpretation) = 'object')
);

create table public.kb_rulesets (
  ruleset_id text primary key,
  version text not null,
  applies_to jsonb not null default '{}'::jsonb,
  rule_ids text[] not null default '{}',
  path text not null,
  content_hash text not null,
  synced_at timestamptz not null default now(),
  constraint kb_rulesets_version_check
    check (version = 'kb-rules-v1'),
  constraint kb_rulesets_applies_to_object_check
    check (jsonb_typeof(applies_to) = 'object')
);

create table public.kb_rules (
  id text primary key,
  ruleset_id text not null references public.kb_rulesets(ruleset_id) on delete cascade,
  question text not null,
  priority integer not null default 0,
  when_clause jsonb not null default '{}'::jsonb,
  rule_output jsonb not null default '{}'::jsonb,
  path text not null,
  content_hash text not null,
  synced_at timestamptz not null default now(),
  constraint kb_rules_when_clause_object_check
    check (jsonb_typeof(when_clause) = 'object'),
  constraint kb_rules_output_object_check
    check (jsonb_typeof(rule_output) = 'object')
);

create table public.kb_question_blueprints (
  blueprint_id text primary key,
  applies_to jsonb not null default '{}'::jsonb,
  title_direction text not null,
  story_arc_template text not null,
  chapter_order text[] not null default '{}',
  global_forbidden_claims text[] not null default '{}',
  style_rules text[] not null default '{}',
  paid_unlock text[] not null default '{}',
  questions jsonb not null default '[]'::jsonb,
  chapters jsonb not null default '[]'::jsonb,
  path text not null,
  content_hash text not null,
  synced_at timestamptz not null default now(),
  constraint kb_question_blueprints_applies_to_object_check
    check (jsonb_typeof(applies_to) = 'object'),
  constraint kb_question_blueprints_questions_array_check
    check (jsonb_typeof(questions) = 'array'),
  constraint kb_question_blueprints_chapters_array_check
    check (jsonb_typeof(chapters) = 'array')
);

create table public.kb_guardrail_sets (
  guardrail_id text primary key,
  version text not null,
  applies_to jsonb not null default '{}'::jsonb,
  guardrail_ids text[] not null default '{}',
  path text not null,
  content_hash text not null,
  synced_at timestamptz not null default now(),
  constraint kb_guardrail_sets_version_check
    check (version = 'kb-guardrails-v1'),
  constraint kb_guardrail_sets_applies_to_object_check
    check (jsonb_typeof(applies_to) = 'object')
);

create table public.kb_guardrails (
  id text primary key,
  guardrail_id text not null references public.kb_guardrail_sets(guardrail_id) on delete cascade,
  system text not null,
  category text not null,
  source_article_id text not null references public.kb_articles(id) on delete restrict,
  claim_ids text[] not null default '{}',
  applies_to text[] not null default '{}',
  points_any text[] not null default '{}',
  precision_any text[] not null default '{}',
  blocks text[] not null default '{}',
  lowers_confidence text[] not null default '{}',
  display text not null,
  reason text not null,
  path text not null,
  content_hash text not null,
  synced_at timestamptz not null default now(),
  constraint kb_guardrails_system_check
    check (system in ('western', 'bazi', 'context', 'cross')),
  constraint kb_guardrails_category_check
    check (category in ('precision', 'safety', 'method')),
  constraint kb_guardrails_display_check
    check (display in ('allowed', 'allowed_with_uncertainty', 'blocked', 'not_available'))
);

alter table public.kb_sync_runs
  add column if not exists atom_count integer not null default 0,
  add column if not exists rule_count integer not null default 0,
  add column if not exists question_blueprint_count integer not null default 0,
  add column if not exists guardrail_count integer not null default 0;

create index kb_atoms_system_idx on public.kb_atoms(system);
create index kb_atoms_layer_idx on public.kb_atoms(layer);
create index kb_atoms_category_idx on public.kb_atoms(category);
create index kb_atoms_source_article_id_idx on public.kb_atoms(source_article_id);
create index kb_atoms_claim_ids_idx on public.kb_atoms using gin(claim_ids);
create index kb_atoms_applies_to_idx on public.kb_atoms using gin(applies_to);
create index kb_atoms_selectors_idx on public.kb_atoms using gin(selectors);

create index kb_rulesets_applies_to_idx on public.kb_rulesets using gin(applies_to);

create index kb_rules_ruleset_id_idx on public.kb_rules(ruleset_id);
create index kb_rules_question_idx on public.kb_rules(question);
create index kb_rules_priority_idx on public.kb_rules(priority desc);
create index kb_rules_when_clause_idx on public.kb_rules using gin(when_clause);
create index kb_rules_output_idx on public.kb_rules using gin(rule_output);

create index kb_question_blueprints_applies_to_idx on public.kb_question_blueprints using gin(applies_to);
create index kb_question_blueprints_chapter_order_idx on public.kb_question_blueprints using gin(chapter_order);
create index kb_question_blueprints_questions_idx on public.kb_question_blueprints using gin(questions);
create index kb_question_blueprints_chapters_idx on public.kb_question_blueprints using gin(chapters);

create index kb_guardrail_sets_applies_to_idx on public.kb_guardrail_sets using gin(applies_to);

create index kb_guardrails_guardrail_id_idx on public.kb_guardrails(guardrail_id);
create index kb_guardrails_system_idx on public.kb_guardrails(system);
create index kb_guardrails_category_idx on public.kb_guardrails(category);
create index kb_guardrails_source_article_id_idx on public.kb_guardrails(source_article_id);
create index kb_guardrails_display_idx on public.kb_guardrails(display);
create index kb_guardrails_claim_ids_idx on public.kb_guardrails using gin(claim_ids);
create index kb_guardrails_applies_to_idx on public.kb_guardrails using gin(applies_to);
create index kb_guardrails_points_any_idx on public.kb_guardrails using gin(points_any);
create index kb_guardrails_precision_any_idx on public.kb_guardrails using gin(precision_any);
create index kb_guardrails_blocks_idx on public.kb_guardrails using gin(blocks);

alter table public.kb_atoms enable row level security;
alter table public.kb_rulesets enable row level security;
alter table public.kb_rules enable row level security;
alter table public.kb_question_blueprints enable row level security;
alter table public.kb_guardrail_sets enable row level security;
alter table public.kb_guardrails enable row level security;

revoke all on table public.kb_atoms from public;
revoke all on table public.kb_rulesets from public;
revoke all on table public.kb_rules from public;
revoke all on table public.kb_question_blueprints from public;
revoke all on table public.kb_guardrail_sets from public;
revoke all on table public.kb_guardrails from public;

revoke all on table public.kb_atoms from anon, authenticated;
revoke all on table public.kb_rulesets from anon, authenticated;
revoke all on table public.kb_rules from anon, authenticated;
revoke all on table public.kb_question_blueprints from anon, authenticated;
revoke all on table public.kb_guardrail_sets from anon, authenticated;
revoke all on table public.kb_guardrails from anon, authenticated;

grant select, insert, update, delete on table public.kb_atoms to service_role;
grant select, insert, update, delete on table public.kb_rulesets to service_role;
grant select, insert, update, delete on table public.kb_rules to service_role;
grant select, insert, update, delete on table public.kb_question_blueprints to service_role;
grant select, insert, update, delete on table public.kb_guardrail_sets to service_role;
grant select, insert, update, delete on table public.kb_guardrails to service_role;

comment on table public.kb_atoms is
  'Machine-readable interpretation atoms selected from source-backed KB claims.';
comment on table public.kb_rulesets is
  'Structured reducer ruleset manifests for deterministic reading answers.';
comment on table public.kb_rules is
  'Question-specific reducer rules that convert evidence clusters into answer posture.';
comment on table public.kb_question_blueprints is
  'Question and chapter contracts controlling free reading structure and forbidden claims.';
comment on table public.kb_guardrail_sets is
  'Structured guardrail set manifests for precision, safety, and method limits.';
comment on table public.kb_guardrails is
  'Claim boundaries that block or lower-confidence unsupported runtime interpretation.';
