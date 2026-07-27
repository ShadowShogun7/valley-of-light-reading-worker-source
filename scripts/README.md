# Scripts 工具腳本

放置 KB 編譯、驗證、維護的 Python 腳本。

## 已建立的腳本

### validate.py

驗證 wiki 結構與 claim-level source traceability：
- frontmatter 是否完整
- confidence / status / type 是否有效
- `source_primary` / `source_secondary` 是否能對到 `docs/research/sources.yml`
- 內部連結 `[[...]]`、`related`、typed `links` 是否可解析
- typed `links` 是否與 `related` 對齊，且是否有合法 type / reason
- `## Claims` 是否存在
- claim ids 是否符合 article id
- variants 是否引用 claim ids
- cited claim 是否支援該 variant
- source location 是否指向真實 raw path 與 line/range
- source quote 是否能在 cited raw line/range 找到
- Western source quote 是否保持短引文

### compile_kb.py

把 `wiki/*.md` 編譯成 local JSON artifacts。
預設會先執行 `validate.py`；只有在已經剛跑過驗證、需要快速重編時才使用 `--skip-validate`。

輸出：
- `dist/kb/kb_articles.json`
- `dist/kb/kb_claims.json`
- `dist/kb/kb_links.json`
- `dist/kb/kb_atoms.json`
- `dist/kb/kb_rules.json`
- `dist/kb/kb_question_blueprints.json`
- `dist/kb/kb_guardrails.json`
- `dist/kb/manifest.json`

這一步不連 Supabase、不生成 embedding。它先固定 KB runtime data contract，後續再加 Supabase sync。
`kb_links.json` 會保留 typed graph、legacy related links、body wiki links，方便 retriever 做受控擴展。

### structured_kb.py / compile_structured_kb.py

把 `kb/atoms/**/*.yml` 與 `kb/rules/**/*.yml` 編譯成 deterministic reducer artifacts。

用途：
- Markdown article 繼續負責 source-backed 長文與 claims。
- YAML atom 負責產品可執行的 interpretation unit。
- YAML rule 負責 question-specific reducer decision。
- Pydantic schema 會驗證 id、條件、source article、claim id 與 cluster cross-reference。

範例：

```bash
python3 scripts/compile_structured_kb.py
python3 scripts/compile_kb.py
```

### report_structured_kb_coverage.py

產生 structured KB coverage report，檢查 atoms/rules 是否都有 source article、claim ids、question fallback，以及哪些 Western articles 尚未進入 runtime atom/rule layer。

輸出：
- `docs/research/06-structured-kb-coverage.md`

範例：

```bash
python3 scripts/compile_kb.py
python3 scripts/report_structured_kb_coverage.py
```

### book_digests.py / validate_book_digests.py / report_book_digest_coverage.py

把 `kb/book_digests/**/*.yml` 作為「讀書方法層」來驗證與產生報告。

用途：
- book digest 先整理每本書的 reading method、可用範圍、禁用推論與 runtime target。
- Astrology method sources 決定星盤證據怎麼讀。
- Situation-handling sources 只決定行動邊界與語氣，不能製造占星結論。
- `report_book_digest_coverage.py` 會產生 `docs/research/11-western-relationship-method-bible.md`，作為後續 atom/rule audit 的方法總表。

範例：

```bash
python3 scripts/validate_book_digests.py
python3 scripts/report_book_digest_coverage.py
```

### structured_runtime.py

Single loading boundary for structured runtime records: atoms, rules, question blueprints, and guardrails.

用途：
- local mode reads compiled JSON from `dist/kb`
- Supabase mode reads the same contract from runtime tables
- API/build scripts use the indexed form through `load_structured_kb`
- retrieval scripts use raw records through `load_structured_records`

This keeps calculation and reducer logic deterministic while allowing production to switch the storage backend with env config.

### structured_runtime_contract.py

Offline adapter contract test for the structured runtime layer.

用途：
- simulate Supabase-shaped rows using the same transform functions as `sync_supabase.py`
- normalize DB-only columns and `when_clause` / `rule_output` through `structured_runtime.py`
- fail if local JSON and normalized Supabase rows produce different reducer records or indexes

範例：

```bash
python3 scripts/structured_runtime_contract.py
```

### verify_paid_v1_reading_stack.py

One-command backend gate for the paid Western V1 reading stack.

用途：
- validate and compile the local KB runtime artifacts
- validate book coverage, book digests, method-claim usage, structured runtime, runtime method trace, and paid V1 section contract
- run Western answer-rule, answer-layer, timing-branch, context, chart-variation, and complete-result smoke tests
- fail when key generated research reports are stale
- optionally run `apps/web` typecheck/build with `--include-web`

範例：

```bash
python3 scripts/verify_paid_v1_reading_stack.py
python3 scripts/verify_paid_v1_reading_stack.py --include-web
```

### validate_supabase_structured_runtime.py

Live DB-backed validation for the structured runtime adapter.

用途：
- read `kb_atoms`, `kb_rules`, `kb_question_blueprints`, and `kb_guardrails` through the same adapter used by the API
- compare Supabase records against compiled local JSON
- run every structured retrieval scenario against Supabase rows
- build one complete relationship result view model with `structured-kb-source=supabase`

安全預設：
- does not run migrations
- does not sync by default
- `--sync` writes to the configured Supabase project and now requires `--allow-writes --target staging|production`
- production sync also requires explicit approval plus `--confirm-production`
- `--prune` deletes stale runtime rows outside the current compiled sync set when used with `--sync`

範例：

```bash
python3 scripts/validate_supabase_structured_runtime.py --env-file .env
python3 scripts/validate_supabase_structured_runtime.py --env-file .env --sync --allow-writes --target staging --prune
```

### check_supabase_runtime_readiness.py

Read-only preflight for Supabase KB runtime tables.

用途：
- check whether article/claim/link tables and structured runtime tables exist
- compare structured table row counts against local compiled JSON
- report missing tables before running DB-backed runtime validation

安全預設：
- read-only GET requests only
- does not run migrations
- does not sync data
- does not print service-role keys

範例：

```bash
python3 scripts/check_supabase_runtime_readiness.py --env-file .env
python3 scripts/check_supabase_runtime_readiness.py --json
```

### check_supabase_migration_contract.py

Static SQL contract check for structured KB Supabase migrations.

用途：
- verify the structured migration files exist
- check that each structured runtime table has the columns required by `sync_supabase.py`
- check primary keys, key foreign keys, RLS enablement, public/anon/authenticated revokes, and service-role grants
- check required structured indexes and table comments as warnings
- provide a no-database gate before applying SQL to a hosted Supabase target

範例：

```bash
python3 scripts/check_supabase_migration_contract.py
python3 scripts/check_supabase_migration_contract.py --json
```

### supabase_target_guard.py

Hosted Supabase target classifier and write guard.

用途：
- identify the configured Supabase host/project ref without printing secrets
- use Supabase CLI project metadata when available to show the project name
- infer `staging` / `production` only from explicit env (`VALLEY_SUPABASE_TARGET`) or project naming
- block write commands when `--target staging` points at an unknown/main project

範例：

```bash
python3 scripts/supabase_target_guard.py
python3 scripts/supabase_target_guard.py --target staging
VALLEY_SUPABASE_TARGET=staging python3 scripts/supabase_target_guard.py --target staging
```

### run_supabase_structured_runtime_cutover.py

Guarded cutover runner for moving structured KB runtime reads onto Supabase.

用途：
- run the static structured migration contract
- run the offline structured runtime contract
- produce the Supabase sync dry-run plan
- run the read-only Supabase runtime readiness check
- optionally run a real sync only when `--sync`, `--allow-writes`, and `--target staging|production` are all present
- optionally prune stale runtime rows with `--prune`
- block production sync unless `--confirm-production` is also present
- block staging sync unless the hosted project is explicitly labelled as staging
- optionally fail the command when the target is not ready with `--require-ready`

安全預設：
- default mode does not write to Supabase
- does not apply migrations
- blocks real sync if structured runtime tables are missing
- target must be explicitly labelled as hosted `staging` or `production` before writes
- production writes require explicit launch/write approval plus `--confirm-production`
- if project metadata is ambiguous, set `VALLEY_SUPABASE_TARGET=staging` in the staging env or pass `--allow-unknown-staging-target` only after manual verification

範例：

```bash
python3 scripts/run_supabase_structured_runtime_cutover.py --env-file .env
python3 scripts/run_supabase_structured_runtime_cutover.py --env-file .env --json
python3 scripts/run_supabase_structured_runtime_cutover.py --env-file .env --require-ready
python3 scripts/run_supabase_structured_runtime_cutover.py --env-file .env --sync --allow-writes --target staging --prune --validate-live
python3 scripts/run_supabase_structured_runtime_cutover.py --env-file .env --sync --allow-writes --target production --confirm-production --prune --validate-live
```

### lint_kb.py

回報 KB 健康度，不取代 `validate.py`。

檢查重點：
- article / claim / link 統計
- status / confidence / category 分布
- 重複 article id 或 claim id
- typed link graph 是否過稀、過密、或有 unresolved target
- 是否全部仍為 draft（production sync gate）
- `dist/kb/manifest.json` 是否與目前 wiki count 對齊

預設只有 `ERROR` 會讓指令失敗；`--strict` 會讓 `WARN` 也失敗，適合 pre-release gate。

### sync_supabase.py

把 compiled KB JSON 同步到 Supabase runtime tables。

安全預設：
- 先跑 `validate.py`
- 預設只編譯並同步 `status: published` 的文章
- published set 為 0 時會拒絕同步，除非加 `--allow-empty`
- 私有測試才使用 `--include-drafts`
- 這是 low-level sync script；hosted staging / production writes should normally go through `run_supabase_structured_runtime_cutover.py`
- `--prune` 會刪除 Supabase runtime tables 中不在本次 compiled sync set 的舊 rows，正式 cutover 建議使用

目前同步表：
- `kb_articles`
- `kb_claims`
- `kb_links`
- `kb_atoms`
- `kb_rulesets`
- `kb_rules`
- `kb_question_blueprints`
- `kb_guardrail_sets`
- `kb_guardrails`
- `kb_sync_runs`

Supabase schema 由 `supabase/migrations/20260519152111_init_kb_runtime.sql`
與 `supabase/migrations/20260525095713_add_structured_kb_runtime.sql` 管理。
embedding table 尚未建立；等 embedding model / vector dimension 鎖定後再加 migration。

### select_signals.py

從 scenario candidate ids 中選出 legacy primary articles.

用途：
- 把 `stage` / `main_question` / calculation signals 放進固定 slots
- 在每個 slot 內根據問題、階段、計算強度、confidence、claim-backed 狀態做 tie-break
- 對 attraction / safety / commitment / conflict / timing / method guardrail 做 redundancy 控制
- 輸出 `selected_primary_ids`、`slot_assignments`、`rank_reason`、`dropped_candidates`、`missing_slots`

安全預設：
- 預設只讀 compiled `status: published` metadata
- build-phase 私有測試才使用 `--include-drafts`
- 預設 legacy selector `--max-primary 6`
- 不連 Supabase；只讀 `dist/kb/kb_articles.json`

### retrieve_kb.py

從 Supabase runtime tables 建立 deterministic retrieval bundle。

用途：
- 測試 slot-based primary article selection
- 測試 typed link one-hop expansion
- attach `kb_claims` evidence
- 產生 LLM prompt candidate：`prompt_context`

安全預設：
- 預設只讀 `status: published`
- build-phase 私有測試才使用 `--include-drafts`
- 不使用 embeddings，不做 second-hop expansion
- 預設先跑 slot-based selector；raw scenario 測試才使用 `--no-select-signals`
- `contextualizes` links 不作預設 expansion；需要時用 `--expansion-type contextualizes` 顯式加入
- 預設 `--max-expanded 4`，適合 compact relationship-result bundle；future deep report 可顯式提高
- 未指定 `--variant` 時，依 scenario stage 自動選 variants：`crisis` 用 `core + in_relationship`，其他 breakup stages 用 `core + in_breakup`

### retrieve_structured_kb.py / structured_retrieval_smoke.py

從 structured runtime contract 建立 atoms / rules / question blueprints / guardrails bundle。

用途：
- 驗證每個使用者問題都有 reducer rules、fallback rule、question blueprint、required atom categories 與 guardrails
- local mode 直接讀 `dist/kb/*.json`，不需要 Supabase
- Supabase mode 在 migration + sync 後讀 runtime tables，檢查 DB contract 是否與 local JSON 等價

範例：

```bash
python3 scripts/retrieve_structured_kb.py \
  --scenario examples/retrieval/cold-war-still-love-me.json \
  --strict

python3 scripts/structured_retrieval_smoke.py

python3 scripts/structured_runtime_contract.py

python3 scripts/structured_retrieval_smoke.py --source supabase

python3 scripts/validate_supabase_structured_runtime.py --env-file .env
```

### smoke_western_context_matrix.py

產生 125 個 Western relationship-result context cases：

```text
stage x question x contact status
```

並輪替 emotional risk 與 precision state。這個 smoke 會確認每個 case 都有 Suskin/context clusters、active blueprint method evidence、精度 gate，且不落回 fallback rule。

```bash
python3 scripts/smoke_western_context_matrix.py
```

### smoke_western_answer_layer.py

Verifies that every compiled Western answer rule is covered by deterministic
fixtures across the timing and non-timing rule matrices.

```bash
python3 scripts/smoke_western_answer_layer.py
```

### build_reading_context.py

把一次 reading intake JSON 轉成 V0 runtime context。

用途：
- 使用 `person_a` / `person_b` role labels：`你` / `對方`
- 明確標記 V0 不收集名字；role labels 不參與 calculation
- 轉出 selector scenario：`stage` / `main_question` / candidate signals
- 執行 `select_signals.py`
- 可選擇連 Supabase 執行 `retrieve_kb.py` bundle
- 輸出 free answer contract 與 paid expansion contract

安全預設：
- 不生成 LLM 文字，只生成 prompt-ready context
- `--selection-only` 可離線檢查 selector，不需 Supabase
- build-phase 私有測試才使用 `--include-drafts`

### build_relationship_result_view_models.py

把 `examples/calculations/*.json` 轉成前端可直接吃的 `CompleteRelationshipResultViewModel` fixtures。

用途：
- 讓 result dashboard 使用真實 calculation + selector slot output，而不是手寫單一 mock
- 把 raw Western engine output 壓成 UI 需要的 summary / metrics / evidence / paid preview
- 用 deterministic template copy 測前端 flow；未來由 LLM narrative layer 替換 copy，不改 UI contract

輸出：
- `apps/web/src/data/generated/relationship-result-scenarios.json`

範例：

```bash
python3 scripts/build_relationship_result_view_models.py
```

### calc_western_spike.py

Astrology branch runtime uses this Western-only bridge.

用途：
- 使用 `immanuel` 產生西洋本命盤、合盤相位與分析日行運
- 將 raw calculation 映射成 Western KB article ids
- 產生 minimal stage / question / western_core slot selection
- 不 import、不計算、不輸出 BaZi payload

範例：

```bash
python3 scripts/calc_western_spike.py \
  --reading examples/readings/cold-war-still-love-me.json \
  --include-drafts \
  --select
```

輸出 fixture:

```bash
python3 scripts/calc_western_spike.py \
  --reading examples/readings/cold-war-still-love-me.json \
  --include-drafts \
  --select \
  --write examples/calculations/cold-war-still-love-me.json
```

### calc_spike.py

把一次 reading intake JSON 轉成真實計算輸出與 candidate signals。

用途：
- 使用 `sxtwl` 產生八字四柱
- 使用 `lunar_python` 交叉驗證四柱，補藏干與十神資料
- 使用 `immanuel` 產生西洋本命盤與合盤相位
- 將 raw calculation 映射成既有 KB article ids
- 可選擇直接跑 selector，檢查真實 signal 進入 legacy selector slots 後會選出什麼
- 保留給 BaZi branch / mixed legacy experiments；astrology branch runtime 不使用它

安裝 spike 依賴：

```bash
python3 -m pip install -r requirements-calculation.txt
```

範例：

```bash
python3 scripts/calc_spike.py \
  --reading examples/readings/cold-war-still-love-me.json \
  --include-drafts \
  --select
```

輸出 fixture:

```bash
python3 scripts/calc_spike.py \
  --reading examples/readings/cold-war-still-love-me.json \
  --include-drafts \
  --select \
  --write examples/calculations/cold-war-still-love-me.json
```

### retrieval_smoke.py

批次跑 `examples/retrieval/*.json`，用來檢查不同用戶情境下的 bundle 是否過寬或缺 primary articles。

目前用於回答兩個問題：
- 每個 scenario 是否能找到 primary articles。
- 哪些 expanded articles 反覆出現，可能代表 graph 太泛。
- stage 推導出的 variants 是否符合用戶當下狀態。
- 哪些 scenario 超過 claim-budget warning threshold，提示 primary signals 可能太多。
- selector 是否把 primary bundle 壓在 compact claim budget 內。

### kb_utils.py

共用 markdown/frontmatter/source parser。`validate.py` 與 `compile_kb.py` 都使用它，避免兩套解析邏輯 drift。

詳見：`docs/tech/05-kb-integration.md`

## 預計的腳本

### embed_kb.py（V1 必要）

生成 embeddings 並 upsert 到後續的 `kb_embeddings` table。

### missing_articles.py（後期）

根據 `index.md` 中的 TODO 標記找出缺漏文章。

### deeper_lint.py（後期）

更深的 KB lint：
- 過時文章（last_reviewed > 6 個月）
- 矛盾偵測
- 重複內容偵測

## 使用方式

```bash
# 驗證
python3 scripts/validate.py

# 編譯到 local JSON
python3 scripts/compile_kb.py

# 快速重編，不重跑 validate.py
python3 scripts/compile_kb.py --skip-validate

# KB 健康度檢查
python3 scripts/lint_kb.py

# pre-release gate
python3 scripts/lint_kb.py --strict

# Supabase sync dry run：production-safe，產生 table-by-table plan
python3 scripts/sync_supabase.py --dry-run --plan-out default

# Supabase structured runtime cutover preflight：contract + dry-run + read-only readiness
python3 scripts/run_supabase_structured_runtime_cutover.py --env-file .env

# Supabase structured migration static contract：no DB needed before hosted migration
python3 scripts/check_supabase_migration_contract.py

# Supabase sync dry run：私有建置期測試 draft content
python3 scripts/sync_supabase.py --dry-run --include-drafts

# Hosted Supabase 真正同步 published articles：建議走 guarded cutover runner
python3 scripts/run_supabase_structured_runtime_cutover.py --env-file .env --sync --allow-writes --target staging --prune --validate-live

# 檢查 legacy primary selector
python3 scripts/select_signals.py --scenario examples/retrieval/broke-up-long-any-chance.json --include-drafts

# 輸出 selector JSON
python3 scripts/select_signals.py --scenario examples/retrieval/broke-up-long-any-chance.json --include-drafts --json

# Supabase retriever smoke test：私有 draft content
python3 scripts/retrieve_kb.py --scenario examples/retrieval/cold-war-still-love-me.json --include-drafts

# Raw scenario primary ids，不經 selector
python3 scripts/retrieve_kb.py --scenario examples/retrieval/cold-war-still-love-me.json --include-drafts --no-select-signals

# 輸出完整 JSON bundle
python3 scripts/retrieve_kb.py --scenario examples/retrieval/cold-war-still-love-me.json --include-drafts --json

# Reading contract harness：selection only
python3 scripts/build_reading_context.py --reading examples/readings/cold-war-still-love-me.json --include-drafts --selection-only --json

# Reading contract harness：selection + Supabase KB bundle
python3 scripts/build_reading_context.py --reading examples/readings/cold-war-still-love-me.json --include-drafts --json

# 批次檢查所有 retrieval examples
python3 scripts/retrieval_smoke.py --include-drafts

# 找缺漏
python3 scripts/missing_articles.py
```

## 環境變數

目前的 `validate.py` / `compile_kb.py` 不需要環境變數。

Supabase sync 腳本需要的環境變數放在 repo 根目錄的 `.env`，或共用 env `/Users/novaos/.openclaw/workspace/.env`。
Valley 專案請優先使用 `VALLEY_` 前綴，避免誤連到其他 Supabase project：

```
VALLEY_SUPABASE_URL=...
VALLEY_SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_DB_PASSWORD=...         # only needed for Supabase CLI migration push/query
```

Fallback keys `SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` 只用於沒有 `VALLEY_` keys 的環境。

`.env` 已加入 `.gitignore`，不會被 commit。

## 重要

⚠️ `validate.py`、`compile_kb.py`、`kb_utils.py` 已建立。
V1 開發時的優先順序：
1. 先用 `validate.py` 驗證每篇 KB 文章
2. 每批文章跑 `compile_kb.py`，確認 markdown 可進入 runtime JSON
3. 每批文章跑 `lint_kb.py`，確認 link graph 與 production gate 沒有失控
4. Supabase schema 先走 migrations，不直接在 dashboard 手改
5. 先用 `build_reading_context.py` 跑 3-5 個真實 reading bundle，再擴張 KB
6. KB 有 30+ 篇後，鎖 embedding model / dimension，再建 embedding migration
7. KB 有 80+ 篇後，補 `missing_articles.py` / deeper lint
8. 上線後再做其他維護腳本
