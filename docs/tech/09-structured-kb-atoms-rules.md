# 09 - Structured KB Atoms And Rules
## YAML reducer layer for deterministic readings

**Status:** Build-stage V1
**Scope:** Local YAML authoring and JSON compilation before Supabase runtime storage.

---

## Target Architecture

Valley readings should not depend on broad article retrieval alone.

The production path is:

```text
calculation JSON
  -> structured atoms
  -> reducer rules
  -> question blueprints
  -> precision guardrails
  -> readingBlueprint
  -> controlled RAG evidence pack
  -> LLM wording only
```

Markdown articles remain the source-backed human-readable layer. YAML atoms, rules, question blueprints, and guardrails are the machine-readable execution layer.

---

## Authoring Paths

```text
wiki/**/*.md
  source-backed long-form articles and claim ids

kb/atoms/**/*.yml
  interpretation atoms: category, selectors, source article, claim ids, safe meanings

kb/rules/**/*.yml
  reducer rules: question, priority, conditions, answer copy, because-clusters

kb/question_blueprints/**/*.yml
  question answer contracts and relationship-result chapter structure

kb/guardrails/**/*.yml
  hard claim boundaries for missing or low-confidence birth data
```

Compiled local artifacts:

```text
dist/kb/kb_articles.json
dist/kb/kb_claims.json
dist/kb/kb_links.json
dist/kb/kb_atoms.json
dist/kb/kb_rules.json
dist/kb/kb_question_blueprints.json
dist/kb/kb_guardrails.json
dist/kb/manifest.json
```

`dist/` is still a generated local cache. The build-stage Supabase sync layer now maps these artifacts into runtime tables, but production writes should wait for explicit approval.

---

## Current V1 Shape

The first Western ruleset is:

```text
kb/atoms/western/relationship-free-v1.yml
kb/atoms/western/horoscope-symbols-v1.yml
kb/rules/western/relationship-result-v1.yml
kb/question_blueprints/western/relationship-result-v1.yml
kb/guardrails/western/precision-v1.yml
```

It covers method order, natal relationship potential, element comparison, luminary comparison, Hand symbol foundations, planet functions, generic planet-in-sign style, Moon/Mercury/Venus/Mars/Saturn point-specific sign functions, ascendant impression, house relationship factors, aspect priority, consultation safety, identity needs, attraction, emotional safety, pressure, communication, repair, current transits, birth-data quality, question-specific answer contracts, and missing time/place guardrails.

The Rod Suskin P0 method layer is authored here:

```text
kb/atoms/western/suskin-method-v1.yml
wiki/western/synastry/method-order.md
wiki/western/planets/natal-relationship-potential.md
wiki/western/synastry/initial-comparison-elements.md
wiki/western/synastry/interchart-aspect-priorities.md
wiki/western/composite/relationship-chart-layer.md
wiki/western/synastry/consultation-ethics.md
docs/product/13-western-suskin-method-system.md
```

The runtime order is:

```text
intake context + precision gate
  -> methodOrder
  -> relationshipPotential
  -> Moon/Mercury/Venus/Mars/Saturn sign-function needs
  -> elementComparison
  -> luminaryComparison
  -> synastry aspect clusters
  -> pressure / repair / timing reducers
  -> consultationSafety
  -> question-specific answer
  -> controlled LLM wording
```

Runtime integration:

- `westernRelationshipCaseFile.evidenceClusters[*].atomId`
- `westernRelationshipCaseFile.evidenceClusters[*].claimIds`
- `westernRelationshipCaseFile.answerLayer.ruleId`
- `westernRelationshipCaseFile.answerLayer.rulesetId`
- `westernRelationshipCaseFile.answerLayer.questionBlueprintId`
- `westernRelationshipCaseFile.answerLayer.questionClaimIds`
- `readingBlueprint.chapters[]` generated from the question blueprint YAML

The Python fallback logic remains in place so missing local artifacts do not make development impossible, but generated fixtures should use the YAML layer.

---

## Commands

```bash
python3 scripts/compile_structured_kb.py
python3 scripts/compile_kb.py
python3 scripts/build_relationship_result_view_models.py
python3 scripts/smoke_western_complete_result_flow.py
python3 scripts/smoke_western_context_matrix.py
python3 scripts/smoke_western_chart_variation_matrix.py
python3 scripts/smoke_western_answer_layer.py
python3 scripts/retrieve_structured_kb.py --scenario examples/retrieval/cold-war-still-love-me.json --strict
python3 scripts/structured_retrieval_smoke.py
```

---

## Production Direction

For production DB:

- Store compiled article/claim/link/atom/rule/question-blueprint/guardrail records in Supabase Postgres.
- Use Postgres full-text search as the primary lexical retrieval path.
- Use pgvector as secondary semantic expansion, never as the authority.
- Keep local dev/test on compiled JSON first; SQLite FTS5 can be added when local keyword search needs to mimic Postgres ranking more closely.
- Run `python3 scripts/sync_supabase.py --dry-run --plan-out default` before any real sync and inspect the table counts plus content hash.
- Use `scripts/retrieve_structured_kb.py --source supabase` only after the structured KB migration is applied and the sync job has populated the runtime tables.

The LLM should only receive selected facts, atoms, rules, and source-backed claims. It should not decide the astrology meaning.
