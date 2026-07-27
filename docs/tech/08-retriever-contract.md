# 08 - Retriever Contract
## Supabase KB 檢索與 Prompt Bundle 合約

> Legacy V0 retriever reference.
> This document still uses free-result selector language. Current astrology V1
> uses structured atoms/rules/question blueprints to build a complete paid
> relationship result. Use `docs/product/00-current-v1-contract.md`,
> `docs/product/09-frontend-flow-view-model.md`, and
> `docs/tech/09-structured-kb-atoms-rules.md` for active implementation.

> 目的：先驗證 deterministic retrieval 是否足夠，再決定是否加入 embeddings。

---

## 當前策略

V0 retriever 不做語意搜尋。

流程：

```
calculation result + user context
    ↓
candidate article ids
    ↓
slot-based primary selector
    ↓
selected primary article ids
    ↓
kb_articles
    ↓
one-hop typed kb_links expansion
    ↓
kb_claims
    ↓
prompt_context bundle
```

這樣可以先檢查四件事：
- 規則偵測出的 candidate signals 是否合理。
- selector 選出的 primary articles 是否回答當前問題，而不是把所有訊號都塞進 prompt。
- typed internal links 是否補足必要背景，而不是加噪音。
- claims 是否足夠支撐 LLM 生成繁中關係解讀。

---

## Test Harness

腳本：

```bash
python3 scripts/retrieve_kb.py
```

範例：

```bash
python3 scripts/retrieve_kb.py \
  --scenario examples/retrieval/cold-war-still-love-me.json \
  --include-drafts
```

輸出 JSON：

```bash
python3 scripts/retrieve_kb.py \
  --scenario examples/retrieval/cold-war-still-love-me.json \
  --include-drafts \
  --json
```

`--include-drafts` 只用於 build-phase 私有測試。
Production retriever 不應讀 `draft` rows。

Structured runtime harness:

```bash
python3 scripts/retrieve_structured_kb.py \
  --scenario examples/retrieval/cold-war-still-love-me.json \
  --strict

python3 scripts/structured_retrieval_smoke.py
```

This verifies the deterministic side of the reading runtime: atoms, reducer rules,
fallback rules, question blueprint, and guardrails. Default mode reads local
compiled JSON. After Supabase migrations and sync are applied, run the same
contract against DB tables:

```bash
python3 scripts/check_supabase_migration_contract.py
python3 scripts/supabase_target_guard.py --env-file .env --target staging
python3 scripts/structured_runtime_contract.py
python3 scripts/structured_retrieval_smoke.py --source supabase
python3 scripts/run_supabase_structured_runtime_cutover.py --env-file .env
python3 scripts/check_supabase_runtime_readiness.py --env-file .env
python3 scripts/validate_supabase_structured_runtime.py --env-file .env
```

`structured_runtime_contract.py` is offline: it transforms compiled JSON into
Supabase-shaped rows, normalizes them through the runtime adapter, and fails if
DB-only fields or table column names would change reducer behavior.
`check_supabase_migration_contract.py` is static and no-database: it reads the
migration SQL and checks the structured runtime tables, columns, key
relationships, RLS boundary, revokes, and service-role grants before SQL is
applied to a hosted target.
`supabase_target_guard.py` checks the configured hosted project ref/name and
requires the staging/production label to be explicit before any write command
can proceed.
`check_supabase_runtime_readiness.py` is read-only: it checks whether the
configured Supabase target has the required runtime tables and structured row
counts before running DB-backed validation.
`run_supabase_structured_runtime_cutover.py` is the safe cutover wrapper: by
default it runs the static migration contract, offline runtime contract, sync
dry run, and read-only readiness check. Real writes require
`--sync --allow-writes --target staging|production`; production also requires
`--confirm-production`. Add `--prune` during cutover to delete stale runtime
rows outside the compiled published set. The script refuses sync when
structured tables are missing.
`validate_supabase_structured_runtime.py` is live: it reads Supabase through the
runtime adapter, compares it with compiled JSON, runs every structured retrieval
scenario, and builds one free-result view model from Supabase-backed structured
KB.

---

## Input Contract

Scenario JSON：

```json
{
  "stage": "cold-war",
  "main_question": "still-love-me",
  "bazi_signals": [
    "bazi-wuxing-mu-sheng-huo",
    "bazi-tiangan-ding-huo"
  ],
  "western_signals": [
    "western-aspects-venus-saturn"
  ],
  "cross_signals": []
}
```

映射規則：
- `stage: cold-war` → `context-stage-cold-war`
- `main_question: still-love-me` → `context-question-still-love-me`
- `bazi_signals` / `western_signals` / `cross_signals` 必須直接提供 article ids。
- 在 selector 模式下，這些 ids 是 candidate pool，不保證全部進入 free-result primary bundle。

Default variant rules:
- `crisis` → `core + in_relationship`
- `broke-up-recent` / `cold-war` / `broke-up-long` → `core + in_breakup`
- Explicit `--variant` flags override this for manual tests.

---

## Signal Selector

`retrieve_kb.py` 和 `retrieval_smoke.py` 預設使用 `scripts/select_signals.py`。
需要檢查 raw scenario bundle 時，可加 `--no-select-signals`。

Free result slots:

```python
FREE_RESULT_SLOTS = {
    "stage": 1,
    "question": 1,
    "bazi_core": 1,
    "western_core": 1,
    "timing": 1,
    "safety": 1,
}
```

V0 ranking policy:

```python
rank_key = (
    slot_fit,                 # must fit the current slot
    answers_question,         # direct question match beats generic relevance
    matches_stage,            # breakup / in-relationship context match
    calculation_strength,     # chart engine priority or scenario order
    confidence_rank,          # DOCTRINE > INTERPRETATION > SPECULATIVE
    product_surface_fit,      # must serve relationship_compatibility
    has_claim_backed_article, # must be usable as evidence
    non_redundant_cluster,    # avoid repeating the same free-result idea
    not_safety_conflict,      # safety slot should not use attraction/timing
    -first_index,             # stable tie-break from calculation order
)
```

This is intentionally not a weighted formula. V0 should be easy to inspect and
editorially controlled; real user/conversion data can tune priorities later if needed.

Redundancy clusters are capped for optional free-result slots:
- `attraction`
- `safety_validation`
- `commitment_pressure`
- `conflict_pattern`
- `timing_action`
- `method_guardrail`

Required slots can still select a redundant cluster when needed, but `rank_reason`
records `cluster_already_selected`.
If a selected primary already satisfies a required safety slot, the selector records the safety slot as
`covered_by_existing_primary` instead of duplicating the article.

Safety slot activation:
- `broke-up-recent` requires safety
- `what-did-i-do-wrong` requires safety
- emotional risk `self-blaming`, `desperate`, or `unsafe-or-overwhelmed` requires safety
- emotional risk `anxious` activates safety when a suitable candidate exists

Selector output is inspectable:

```bash
python3 scripts/select_signals.py \
  --scenario examples/retrieval/broke-up-long-any-chance.json \
  --include-drafts \
  --json
```

---

## Expansion Rules

預設只展開 frontmatter typed links：

```text
requires
timing
cross_checks
cautions
supports
```

不展開：
- `contextualizes` links（可手動加，但不作預設）
- `frontmatter_related` legacy links
- body `[[wiki]]` links
- second-hop links

理由：LLM 不應自由逛 wiki graph；retriever 只做小範圍、可解釋的 deterministic expansion。
`contextualizes` 在目前 21 篇測試中容易把背景文章帶得太廣，所以先保持 optional。

---

## Output Contract

Bundle shape：

```json
{
  "input": {
    "scenario": {},
    "primary_ids": [],
    "selection": {},
    "include_drafts": true,
    "expansion_types": [],
    "variants": ["core", "in_breakup"],
    "product_use": "free",
    "max_expanded": 4
  },
  "retrieval": {
    "primary_count": 0,
    "expanded_count": 0,
    "claim_count": 0,
    "missing_primary_ids": [],
    "candidate_expansion_ids": [],
    "missing_expansion_ids": []
  },
  "primary_articles": [],
  "expanded_articles": [],
  "expansion_links": [],
  "claims": [],
  "prompt_context": ""
}
```

`prompt_context` is the immediate LLM input candidate.
It includes article variants plus claim-backed evidence and source locations.

---

## Current Smoke Test

Scenario:

```bash
python3 scripts/retrieve_kb.py \
  --scenario examples/retrieval/cold-war-still-love-me.json \
  --include-drafts \
  --json
```

Expected high-level result:

```text
primary articles: 4
expanded articles: 4
claims: 13
missing primary ids: []
```

Current primary ids:
- `context-stage-cold-war`
- `context-question-still-love-me`
- `bazi-wuxing-mu-sheng-huo`
- `western-aspects-venus-saturn`

Current expanded ids:
- `context-question-when-to-contact`
- `western-transits-timing-window`
- `western-synastry-relationship-framework`
- `bazi-hehun-spouse-star`

This is a reasonable first bundle: it contains stage, question, BaZi support pattern,
Western timing, and method guardrails.

---

## Smoke Suite

Run all current examples:

```bash
python3 scripts/retrieval_smoke.py --include-drafts
python3 scripts/structured_retrieval_smoke.py
```

Current scenarios:
- `cold-war-still-love-me.json`
- `cold-war-any-chance.json`
- `cold-war-when-to-contact.json`
- `cold-war-stay-or-let-go.json`
- `cold-war-what-did-i-do-wrong.json`
- `broke-up-recent-still-love-me.json`
- `broke-up-long-any-chance.json`
- `crisis-stay-or-let-go.json`

Current findings:
- All 8 scenarios resolve primary ids successfully.
- Selector mode keeps all scenarios under the 20-claim warning threshold.
- Current smoke suite total is 117 claims across 8 scenarios, down from 143 before selection.
- `broke-up-long-any-chance` dropped from 24 claims raw to 18 claims selected.
- `crisis-stay-or-let-go` dropped from 21 claims raw to 15 claims selected.
- `context-question-when-to-contact` and `western-transits-timing-window` still repeat often because timing/action guidance is central to several relationship questions.
- `contextualizes` was removed from default expansion because it created extra broad background pulls; it remains available through `--expansion-type contextualizes` when needed.
- Production-mode retrieval without `--include-drafts` returns 0 rows right now, which confirms the draft gate is working.
- Mixed-stage scenarios now cover all four relationship stages, so repeated expansions are a better graph-quality signal than the earlier cold-war-only suite.
- Stage-aware default variants prevent crisis bundles from including breakup-only wording unless explicitly requested.

Additional controls:

```bash
# published-only production gate
python3 scripts/retrieve_kb.py --scenario examples/retrieval/cold-war-still-love-me.json --json

# deeper/full claim filter
python3 scripts/retrieve_kb.py --scenario examples/retrieval/cold-war-still-love-me.json --include-drafts --product-use full --json
```

Current control results:
- Production gate: `0 primary / 0 expanded / 0 claims`, because all current rows are `draft`.
- Full filter on `cold-war-still-love-me`: `6 primary / 4 expanded / 20 claims`.

Former gap checks:

```bash
python3 scripts/retrieve_kb.py --stage broke-up-recent --question still-love-me --article western-aspects-venus-saturn --include-drafts --json
python3 scripts/retrieve_kb.py --stage crisis --question stay-or-let-go --article western-aspects-moon-saturn --include-drafts --json
python3 scripts/retrieve_kb.py --stage broke-up-long --question any-chance --article western-transits-timing-window --include-drafts --json
```

Previous gap results:
- `context-stage-broke-up-recent` missing
- `context-stage-crisis` missing
- `context-stage-broke-up-long` missing

These gaps have been closed by adding all remaining stage articles. Current validation should use the full smoke suite, not ad hoc missing-stage probes.

---

## Next Decision

Before scaling to 50+ articles, production work should define the consumer-facing report shape:
- free result slots and section order
- paid report sections that expand the selected free-result signals
- event logging fields needed to tune selector priorities after launch
- whether `max_expanded=4` remains the free-result default once real calculations produce stronger signal priorities
