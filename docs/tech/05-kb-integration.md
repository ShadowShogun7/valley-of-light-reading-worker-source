# 05 - KB Integration
## 知識庫如何整合到生產系統

> Active KB architecture with some historical V0 wording.
> If this document mentions free-result selectors or paid expansion, treat that
> as legacy language. Current astrology V1 emits a complete paid relationship
> result from `westernRelationshipCaseFile`, `readingBlueprint.chapters`, and
> `includedReadingRows`.

> 將靜態 `wiki/*.md` 文章轉化為生產系統可用的結構化資料。

---

## 兩階段架構

### Phase 1：Build Time（建立 KB）

```
原始書籍 (raw/)
    ↓
人類 + LLM 協作
    ↓
Markdown 維基 (wiki/*.md)
    ↓
這個階段是研究性的，可反覆修改
```

詳見：`AGENTS.md`（KB 維護規範）

### Phase 2：Compile Time（編譯）

```
wiki/*.md 檔案
    ↓
scripts/validate.py
    ↓
scripts/compile_kb.py
    ↓
scripts/lint_kb.py
    ↓
dist/kb/*.json
    ↓
後續再同步到 Supabase KB runtime tables
（keyword / embedding retrieval 屬於 Supabase runtime 階段）
```

### Phase 2.5：Retriever Test（檢索合約）

```
calculation result + user context
    ↓
candidate article ids
    ↓
scripts/select_signals.py
    ↓
selected primary articles
    ↓
Supabase kb_articles / kb_links / kb_claims
    ↓
scripts/retrieve_kb.py
    ↓
selected primary articles + one-hop typed expansion + claims
    ↓
prompt_context
    ↓
LLM output test
```

這一步先驗證 deterministic retrieval 是否足夠，避免還沒跑過真實 bundle 就大量擴張 KB。

### Phase 3：Run Time（生產使用）

```
合盤計算結果 + 用戶 context
    ↓
Candidate signal builder
    ↓
Slot-based signal selector
    ↓
KB Retriever（rules first, pgvector later）
    ↓
相關 KB 文章組
    ↓
LLM Prompt Builder
    ↓
Claude API
    ↓
個人化解讀
```

---

## 為什麼用 Hybrid 3-Layer 架構

我們之前討論過三種方案：

1. **純 LLM 即時解讀** — 成本高、不一致
2. **純 Template** — 組合爆炸、缺乏溫度
3. **Hybrid 3-Layer** ⭐ 採用

### Hybrid 三層

```
┌────────────────────────────────────────┐
│ Layer A: 原子層 (Atoms)                 │
│ ~200 個獨立知識單元                     │
│ 每個原子有 frontmatter + core + variants│
│ Storage: wiki/*.md → kb_articles 表    │
└────────────────────────────────────────┘
                ↓ 規則決定組合
┌────────────────────────────────────────┐
│ Layer B: 規則層 (Rules)                 │
│ candidate builder + slot selector       │
│ 決定哪些原子進入 free / paid bundle      │
│ Storage: select_signals.py + retriever  │
└────────────────────────────────────────┘
                ↓ LLM 敘事化
┌────────────────────────────────────────┐
│ Layer C: 產品層 (Products)              │
│ N 個產品配置                            │
│ 定義要用哪些規則 + 敘事框架              │
│ Storage: code in reading/*.py          │
└────────────────────────────────────────┘
```

**核心理念：LLM 不做命理判斷，只做敘事化。**

命理判斷在原子層（穩定、可信、有出處）。
LLM 拿到一組原子，將它們組合成有溫度的解讀。

---

## Compile KB Script

### 用途

`scripts/compile_kb.py` 先把 `wiki/*.md` 編譯成 local JSON artifacts。
這一步不碰 Supabase、不需要 secrets，也不做 embedding；目的是先固定 markdown → runtime data 的合約。
預設會先跑 `scripts/validate.py`，避免把不合格文章編進 runtime JSON。

輸出位置：

```
dist/kb/kb_articles.json
dist/kb/kb_claims.json
dist/kb/kb_links.json
dist/kb/manifest.json
```

資料拆分：

- `kb_articles.json`：文章 metadata、variants、variant → claim 對應。
- `kb_claims.json`：claim text、source quote、source location、confidence、product use、supported variants。
- `kb_links.json`：typed frontmatter `links`、legacy `related`、body `[[wiki links]]` 的 resolved/unresolved link graph。
- `manifest.json`：本次編譯時間與 counts。

下一階段使用 `scripts/sync_supabase.py` 將這些 JSON upsert 到文章、claim、link、atom、rule、question blueprint 與 guardrail runtime tables。
embedding table 尚未建立，等 embedding model / vector dimension 鎖定後再加 migration。

### 執行方式

```bash
# 驗證
python3 scripts/validate.py

# 編譯所有 draft/review/published 文章到 dist/kb
# 預設會先跑 validate.py
python3 scripts/compile_kb.py

# 快速重編，不重跑 validate.py
python3 scripts/compile_kb.py --skip-validate

# 只編譯 published 文章
python3 scripts/compile_kb.py --published-only

# KB 健康度檢查
python3 scripts/lint_kb.py

# pre-release gate；warnings 也會失敗
python3 scripts/lint_kb.py --strict

# Supabase sync dry run；production-safe，產生 table-by-table plan
python3 scripts/sync_supabase.py --dry-run --plan-out default

# 私有測試 draft content 才使用
python3 scripts/sync_supabase.py --dry-run --include-drafts

# 在 CI/CD 中自動編譯（每次 wiki/ 有 commit）
# .github/workflows/compile-kb.yml
```

## Supabase Runtime Schema

Supabase schema 由 migration 管理：

```
supabase/migrations/20260519152111_init_kb_runtime.sql
supabase/migrations/20260525095713_add_structured_kb_runtime.sql
supabase/migrations/20260525112318_add_question_blueprint_version.sql
```

V0 runtime tables：
- `kb_articles`：compiled article metadata、variants、claim ids、controlled links。
- `kb_claims`：claim-level evidence、source location、confidence、product use。
- `kb_links`：retriever 可用的 typed / related / body wiki graph。
- `kb_atoms`：deterministic interpretation atoms，含 selectors、claim ids、safe meaning。
- `kb_rulesets` / `kb_rules`：question-specific reducer rules。
- `kb_question_blueprints`：free reading chapter contracts、forbidden claims、paid boundaries。
- `kb_guardrail_sets` / `kb_guardrails`：birth-data precision、method、safety boundaries。
- `kb_sync_runs`：每次 sync 的 counts、git sha、status。

安全邊界：
- raw books 不進 Supabase。
- frontend 不直接讀 KB tables。
- tables 啟用 RLS，並撤銷 `anon` / `authenticated` 存取。
- backend/sync script 使用 service role key。
- `scripts/sync_supabase.py` 預設只同步 `status: published`。

Build-phase 私有測試可使用：

```bash
python3 scripts/sync_supabase.py --include-drafts
```

但這不應進 CI/CD 或 production job。

## Signal Selector

`scripts/select_signals.py` 是 V0 free-result primary selection layer。
它不連 Supabase，只讀 `dist/kb/kb_articles.json` metadata。

Input:
- relationship stage
- main question
- `bazi_signals`
- `western_signals`
- optional `cross_signals` / manual `article_ids`

Free-result slots:
- `stage`
- `question`
- `bazi_core`
- `western_core`
- `timing` optional
- `safety` optional / conditional

Ranking policy:
- Use deterministic tie-breaks, not weighted scores.
- Priority order: slot fit → answers question → matches stage → calculation strength → confidence → product fit → claim-backed → non-redundant cluster → safety compatibility → calculation order.
- Output includes `rank_reason` so the backend and product team can inspect why a signal was selected.

Why this exists:
- The complete relationship result needs to stay focused enough to build trust instead of dumping every detected signal.
- The selector prevents primary-rich scenarios from stuffing every detected signal into the LLM prompt.
- Future deeper reports should expand the selected complete-result signals, not introduce unrelated material.

## Retriever Test Harness

目前使用：

```bash
python3 scripts/retrieve_kb.py --scenario examples/retrieval/cold-war-still-love-me.json --include-drafts
```

它會：
- 預設先用 `select_signals.py` 從 candidates 選出 primary articles。
- 只展開預設允許的 frontmatter typed links：`requires`、`timing`、`cross_checks`、`cautions`、`supports`。
- 只做 one-hop expansion。
- attach `kb_claims` 作為 prompt evidence。
- 產生 `prompt_context` 供 LLM output 測試。

Runtime result generation also attaches compact `claimSupport` records directly
to `westernRelationshipCaseFile.evidenceClusters.*` and forwards them into
`readingBlueprint.chapters[].evidence`. This keeps the complete-result narrative
grounded in source-backed claims even when the UI is using real calculation
payloads instead of retrieval-only fixtures.

The Western runtime evidence layer should not collapse the reading into one
strongest synastry aspect. Current complete-result case files expose separate
Western evidence objects for:
- each person's natal relationship needs through Moon / Venus / Mars / Saturn / Desc
- synastry attraction, emotional-safety, pressure, repair, and communication clusters
- aspect type, orb, and applying/separating state for selected inter-aspects
- current transit pressure and timing windows for each person

Current multi-layer expansion batch:
- `bazi-geju-month-command-strength` — 月令、日主強弱、用神方法邊界。
- `bazi-shishen-ten-gods-relationship-roles` — 十神作為關係角色語言。
- `bazi-timing-luck-flow` — 大運、行年與喜忌統觀，支撐 timing background。
- `bazi-timing-year-month-trigger` — 流年 / 流月觸發與產品文案邊界。
- `western-planets-natal-relationship-needs` — 合盤前先看本命關係需求。
- `western-composite-composite-chart` — paid depth 的 relationship-itself layer。
- `western-transits-timing-window` — 已開放 `free` claim support，支撐免費結果的 action timing。

Raw scenario primary ids 仍可用於 diagnostics：

```bash
python3 scripts/retrieve_kb.py \
  --scenario examples/retrieval/cold-war-still-love-me.json \
  --include-drafts \
  --no-select-signals
```

批次檢查：

```bash
python3 scripts/retrieval_smoke.py --include-drafts
```

詳見：`docs/tech/08-retriever-contract.md`

## KB Health Lint

`scripts/lint_kb.py` 補 `validate.py` 沒做的健康度檢查。

分工：
- `validate.py`：結構、引用、source traceability 必須正確；有 error 就不能編譯。
- `compile_kb.py`：把 wiki 轉成 runtime JSON；預設先跑 validation。
- `lint_kb.py`：檢查 KB 是否適合繼續擴張或進入 production sync。

目前 lint 會回報：
- article / claim / link 數量
- status / confidence / category 分布
- duplicate article id / claim id
- typed link graph 過稀、過密、unresolved target
- 是否仍是 0 published articles
- `dist/kb/manifest.json` 是否與目前 wiki count 對齊

V0 建置期允許 `0 published articles`，但 production sync 必須保持 gated。

---

## Internal Link Graph

內部連結對 Valley 是正向的，但必須受控。
它的用途不是讓 LLM 自己逛 wiki，而是讓 retriever 在 deterministic first 的前提下擴展少量相關 articles / claims。

每篇 article 使用兩層：

```yaml
related:
  - western-aspects-saturn-pressure
links:
  - target: western-aspects-saturn-pressure
    type: timing
    reason: 土星壓力常需要行運時間窗協助判斷壓力何時被啟動。
```

規則：

- `related` 是簡單 target list，方便人讀與舊腳本相容。
- `links` 是機器用 typed graph；每個 target 必須也出現在 `related`。
- body `[[...]]` links 只作為人類導航與弱訊號，不作主要 retrieval rule。
- 每篇文章先控制在 2-5 個強連結，不要把每個提到的概念都連起來。

目前允許的 link type：

- `requires`：本文判斷需要 target 作前置脈絡。
- `supports`：target 支持或延伸同一組命理判斷。
- `contrasts`：target 用來比較、區分或避免混淆。
- `cross_checks`：target 可跨來源或跨系統交叉檢查，但不是直接等同。
- `contextualizes`：target 提供產品敘事或心理脈絡。
- `timing`：target 提供行運、時間窗或觸發時點。
- `cautions`：target 是限制條件或過度推論警示。

Runtime 建議：

1. 計算引擎輸出 candidate article ids。
2. Selector 選出 free/paid primary articles。
3. Retriever 只展開 `requires`、`timing`、必要的 `cross_checks` / `cautions` / `supports`。
4. 每個展開 target 只取 claim-backed excerpts。
5. LLM prompt 只接收最終 bundle，不直接訪問整個 wiki graph。

---

## KB Retriever（生產時的檢索）

### 用途

給定一個合盤計算結果與用戶 context，找出最相關的 KB 文章。

### 兩種檢索策略

#### 策略 1：規則式檢索（主要）

```python
# app/knowledge/retriever.py

def build_retrieval_bundle(
    calculation: CalculationResult,
    context: UserContext,
    product_surface: str = "free",
) -> KBBundle:
    """
    V0 production shape:
    1. calculation/context produce candidates
    2. selector chooses primary slots
    3. retriever expands through controlled links
    4. claims become prompt evidence
    """
    scenario = {
        "stage": context.relationship_stage,
        "main_question": context.main_question,
        "bazi_signals": build_bazi_candidate_ids(calculation),
        "western_signals": build_western_candidate_ids(calculation),
        "cross_signals": build_cross_candidate_ids(calculation),
    }

    selection = select_signals_for_scenario(
        scenario=scenario,
        product_surface=product_surface,
        include_drafts=False,
    )

    primary_articles = fetch_articles(selection.selected_primary_ids)
    expansion_links = fetch_one_hop_links(
        from_ids=selection.selected_primary_ids,
        link_types=["requires", "timing", "cross_checks", "cautions", "supports"],
    )
    expanded_articles = fetch_articles(expansion_links.target_ids, max_count=4)
    claims = fetch_claims(primary_articles + expanded_articles, product_use=product_surface)

    return KBBundle(selection, primary_articles, expanded_articles, claims)
```

#### 策略 2：語意搜尋（補充）

當規則式檢索找不到對應文章時，用 embedding 找最相似的。

```python
def semantic_search(
    query: str,
    category: str = None,
    top_k: int = 3
) -> List[KBArticle]:
    """
    用 embedding 找相似 KB 文章
    """
    # 生成 query embedding
    query_embedding = model.encode(query).tolist()
    
    # pgvector 相似度搜尋
    sql = """
        SELECT *, 1 - (embedding <=> %s::vector) AS similarity
        FROM kb_articles
        WHERE status = 'published'
    """
    params = [query_embedding]
    
    if category:
        sql += " AND category = %s"
        params.append(category)
    
    sql += " ORDER BY embedding <=> %s::vector LIMIT %s"
    params.extend([query_embedding, top_k])
    
    results = supabase.rpc('execute_sql', {'sql': sql, 'params': params}).execute()
    
    return [KBArticle(**r) for r in results.data]
```

主要用於 AI 問答（每個問題不同，無法規則化）。

---

## Variant 選擇邏輯

每個 KB 文章可能有多個 variants。產品根據情境選擇正確的 variant。

```python
def select_variant(
    article: KBArticle,
    context: UserContext,
    product: str
) -> str:
    """
    根據情境選擇正確的 variant
    """
    # 復合產品的階段對應
    if product == "relationship_compatibility":
        if context.stage in ["broke_up_recent", "cold_war", "broke_up_long"]:
            return article.variants.get("in_breakup", article.variants["core"])
        elif context.stage == "crisis":
            return article.variants.get("in_relationship", article.variants["core"])
    
    # 純八字產品
    if product == "personal_bazi":
        return article.variants.get("in_general", article.variants["core"])
    
    # 預設用 core
    return article.variants["core"]
```

---

## Confidence 處理

KB 文章標有 confidence 等級，生產時要不同處理。

### DOCTRINE 文章

- 直接使用，可斷言
- 例：「丁火日主性格內斂深情」

### INTERPRETATION 文章

- 用軟性語言
- LLM Prompt 提示：「以下內容為 INTERPRETATION 等級，請用『通常』『傾向』『可能』等詞」
- 例：「乙木日主在分手後**傾向**默默處理」

### SPECULATIVE 文章

- **預設不在 NT$499 內容中使用**
- 只在 NT$2,480 深度報告中作為「光之谷研究觀點」呈現
- 必須加 disclaimer：「以下為光之谷研究團隊的觀察，目前命理學界尚無共識」

```python
def filter_by_confidence(
    articles: List[KBArticle],
    tier: str
) -> List[KBArticle]:
    """
    根據產品 tier 過濾 confidence 等級
    """
    if tier == "free":
        # 免費內容只用 DOCTRINE
        return [a for a in articles if a.confidence == "DOCTRINE"]
    elif tier == "full":
        # NT$499 用 DOCTRINE + INTERPRETATION
        return [a for a in articles if a.confidence in ["DOCTRINE", "INTERPRETATION"]]
    elif tier == "deep":
        # NT$2,480 全部 confidence 都可用
        return articles
```

---

## 多產品共用 KB

同一個 KB 可以支撐多個產品。

### 產品對應

```python
PRODUCTS = {
    "valley_of_light": {
        # 復合挽回（V1）
        "name": "光之谷",
        "uses_atoms": ["bazi", "western", "cross", "context"],
        "variant_preference": ["in_breakup", "in_relationship", "core"],
        "voice": "valley_of_light_voice",
        "max_articles_per_reading": 15,
    },
    
    "pure_bazi": {
        # 純八字個人分析（V2/V3）
        "name": "純八字命格分析",
        "uses_atoms": ["bazi"],
        "variant_preference": ["core", "in_general"],
        "voice": "bazi_researcher_voice",
        "max_articles_per_reading": 20,
    },
    
    "pure_western": {
        # 純星盤個人分析（V2/V3）
        "name": "純星盤個人分析",
        "uses_atoms": ["western"],
        "variant_preference": ["core", "in_general"],
        "voice": "modern_astrology_voice",
        "max_articles_per_reading": 20,
    },
}
```

**同一個原子（如 `bazi-tiangan-yi-mu`）可以被三個產品使用，只是 variant 選擇不同。**

---

## KB 更新時的處理

### 場景 1：新增文章

1. Agent 在 `wiki/` 新增 markdown 檔案
2. 更新 `index.md` 和 `log.md`
3. 跑 `python scripts/compile_kb.py`
4. 新文章進入生產（5 秒內）

### 場景 2：修改現有文章

1. Agent 修改 markdown
2. 更新 `last_reviewed` frontmatter
3. 跑 compile script
4. 修改自動 sync 到資料庫

### 場景 3：刪除文章

1. 在 markdown frontmatter 設 `status: deprecated`
2. 跑 compile script
3. 文章標為 deprecated，不再進入生產（但保留紀錄）

**不要直接刪除檔案。** Deprecation 比刪除安全。

---

## 監控

每週檢查 Supabase 上的 KB 狀態：

```sql
-- KB 文章統計
SELECT 
  category,
  confidence,
  COUNT(*) as count
FROM kb_articles
WHERE status = 'published'
GROUP BY category, confidence
ORDER BY category, confidence;

-- 檢查孤立文章（沒被任何 reading 使用）
SELECT slug, title, created_at
FROM kb_articles
WHERE slug NOT IN (
  SELECT jsonb_array_elements_text(retrieved_kb_articles) 
  FROM readings 
  WHERE created_at > NOW() - INTERVAL '30 days'
)
AND status = 'published';
```

---

## 與其他文件的關聯

- KB 維護規範：`AGENTS.md`
- 計算引擎：`tech/04-calculation-engines.md`
- LLM Prompt：`tech/06-llm-prompt-strategy.md`
- 資料庫：`tech/03-database-schema.md`
