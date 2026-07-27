alter table public.kb_question_blueprints
  add column if not exists version text not null default 'kb-question-blueprints-v1';

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'kb_question_blueprints_version_check'
  ) then
    alter table public.kb_question_blueprints
      add constraint kb_question_blueprints_version_check
      check (version = 'kb-question-blueprints-v1');
  end if;
end
$$;
