-- Valley of Light KB runtime schema.
--
-- This migration stores only compiled, production-safe KB data. Raw book files
-- stay in the private Git repo and are not synced into Supabase.

create extension if not exists pgcrypto with schema extensions;
create extension if not exists vector with schema extensions;

create table public.kb_articles (
  id text primary key,
  path text not null unique,
  title text not null,
  title_en text,
  category text not null,
  article_type text not null,
  status text not null default 'draft',
  confidence text not null,
  source_primary text,
  source_primary_id text,
  source_chapter text,
  source_secondary text[] not null default '{}',
  source_secondary_ids text[] not null default '{}',
  applicable_products text[] not null default '{}',
  relationship_stage text[] not null default '{}',
  question_relevance text[] not null default '{}',
  related_ids text[] not null default '{}',
  links jsonb not null default '[]'::jsonb,
  variants jsonb not null default '{}'::jsonb,
  variant_claims jsonb not null default '{}'::jsonb,
  claim_ids text[] not null default '{}',
  search_text text not null default '',
  content_hash text not null,
  created_on date,
  updated_on date,
  last_reviewed_on date,
  synced_at timestamptz not null default now(),
  constraint kb_articles_article_type_check
    check (article_type in ('entity', 'concept', 'bridge', 'context')),
  constraint kb_articles_status_check
    check (status in ('draft', 'review', 'published', 'deprecated')),
  constraint kb_articles_confidence_check
    check (confidence in ('DOCTRINE', 'INTERPRETATION', 'SPECULATIVE')),
  constraint kb_articles_links_array_check
    check (jsonb_typeof(links) = 'array'),
  constraint kb_articles_variants_object_check
    check (jsonb_typeof(variants) = 'object'),
  constraint kb_articles_variant_claims_object_check
    check (jsonb_typeof(variant_claims) = 'object')
);

create table public.kb_claims (
  claim_id text primary key,
  article_id text not null references public.kb_articles(id) on delete cascade,
  article_path text not null,
  claim text not null,
  source_quote text,
  source_location text not null,
  source_raw_path text,
  source_id text,
  source_start_line integer,
  source_end_line integer,
  confidence text not null,
  reasoning text not null,
  product_use text[] not null default '{}',
  variants_supported text[] not null default '{}',
  content_hash text not null,
  synced_at timestamptz not null default now(),
  constraint kb_claims_confidence_check
    check (confidence in ('DOCTRINE', 'INTERPRETATION', 'SPECULATIVE')),
  constraint kb_claims_source_line_range_check
    check (
      source_start_line is null
      or source_end_line is null
      or source_end_line >= source_start_line
    )
);

create table public.kb_links (
  link_id text primary key,
  from_id text not null references public.kb_articles(id) on delete cascade,
  to_id text references public.kb_articles(id) on delete set null,
  target text not null,
  link_type text not null,
  reason text,
  source text not null,
  resolved boolean not null default false,
  synced_at timestamptz not null default now(),
  constraint kb_links_source_check
    check (source in ('frontmatter_links', 'frontmatter_related', 'body_wiki')),
  constraint kb_links_type_check
    check (
      link_type in (
        'requires',
        'supports',
        'contrasts',
        'cross_checks',
        'contextualizes',
        'timing',
        'cautions',
        'related',
        'wiki'
      )
    )
);

create table public.kb_sync_runs (
  id uuid primary key default extensions.gen_random_uuid(),
  git_sha text,
  published_only boolean not null default true,
  article_count integer not null default 0,
  claim_count integer not null default 0,
  link_count integer not null default 0,
  status text not null default 'started',
  notes text,
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  constraint kb_sync_runs_status_check
    check (status in ('started', 'completed', 'failed'))
);

create index kb_articles_category_idx on public.kb_articles(category);
create index kb_articles_status_idx on public.kb_articles(status);
create index kb_articles_confidence_idx on public.kb_articles(confidence);
create index kb_articles_applicable_products_idx on public.kb_articles using gin(applicable_products);
create index kb_articles_relationship_stage_idx on public.kb_articles using gin(relationship_stage);
create index kb_articles_question_relevance_idx on public.kb_articles using gin(question_relevance);
create index kb_articles_related_ids_idx on public.kb_articles using gin(related_ids);

create index kb_claims_article_id_idx on public.kb_claims(article_id);
create index kb_claims_confidence_idx on public.kb_claims(confidence);
create index kb_claims_product_use_idx on public.kb_claims using gin(product_use);
create index kb_claims_variants_supported_idx on public.kb_claims using gin(variants_supported);

create index kb_links_from_id_idx on public.kb_links(from_id);
create index kb_links_to_id_idx on public.kb_links(to_id);
create index kb_links_type_idx on public.kb_links(link_type);
create index kb_links_source_idx on public.kb_links(source);
create index kb_links_resolved_idx on public.kb_links(resolved);

alter table public.kb_articles enable row level security;
alter table public.kb_claims enable row level security;
alter table public.kb_links enable row level security;
alter table public.kb_sync_runs enable row level security;

revoke all on table public.kb_articles from anon, authenticated;
revoke all on table public.kb_claims from anon, authenticated;
revoke all on table public.kb_links from anon, authenticated;
revoke all on table public.kb_sync_runs from anon, authenticated;

grant select, insert, update, delete on table public.kb_articles to service_role;
grant select, insert, update, delete on table public.kb_claims to service_role;
grant select, insert, update, delete on table public.kb_links to service_role;
grant select, insert, update, delete on table public.kb_sync_runs to service_role;

comment on table public.kb_articles is
  'Compiled Valley of Light wiki articles. Raw source books stay outside Supabase.';
comment on table public.kb_claims is
  'Claim-level evidence extracted from KB articles for prompt construction and audit.';
comment on table public.kb_links is
  'Controlled internal link graph used by deterministic retrieval expansion.';
comment on table public.kb_sync_runs is
  'Audit trail for local JSON to Supabase KB sync jobs.';
