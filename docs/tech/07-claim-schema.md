# 07 - Claim-Level KB Schema
## 將文章收斂成可驗證的命理判斷單元

> 本文件補強 `AGENTS.md` 的文章規範。
> 目的：讓每一句會進入產品解讀的命理判斷，都能回溯到原典段落。

---

## 為什麼需要 Claim Layer

原本的 `wiki/*.md` 是「文章層」：

```
丁火.md
  → core
  → in_relationship
  → in_breakup
  → in_general
```

這對人類閱讀很好，但生產系統真正需要的是更小的單位：

```
source passage
  → extracted claim
  → confidence
  → product-safe interpretation
  → variants
  → retrieval tags
```

也就是說，`wiki` 文章仍然存在，但每篇文章內部必須明確列出
「本文哪些判斷是從哪些原典段落抽出來的」。

---

## Claim 的定義

一個 claim 是可獨立驗證、可被產品使用的最小命理判斷。

### 好的 claim

```
丁火較丙火柔中，不能直接等同於燈燭物象。
```

### 不好的 claim

```
丁火的人很深情。
```

原因：第二句沒有指出「從哪個原典判斷推導而來」，也太容易變成泛泛人格描述。

---

## Claim ID 命名

格式：

```
{article_id}-{3-digit-number}
```

範例：

```
bazi-tiangan-ding-huo-001
bazi-tiangan-ding-huo-002
bazi-wuxing-mu-001
context-stage-cold-war-001
```

規則：
- 同一篇文章內遞增，不重用。
- claim 刪除時不要重排舊編號。
- 重大改寫時新增 claim，不覆蓋舊 claim 的來源意義。

---

## Article Body 新增結構

每篇正式 wiki article 除了既有 variants 外，必須包含：

```markdown
## Claims

### bazi-tiangan-ding-huo-001

**Claim:** 丁火較丙火柔中，不能直接等同於燈燭物象。

**Source quote:**
> 引自《滴天髓闡微》通神論 七、天干：
> 「丁非灯烛之谓，较丙火则柔中耳。」

**Source location:** raw/bazi/952331994-01-滴天髓阐微-完美排版.txt:339

**Confidence:** INTERPRETATION

**Reasoning:** 原文先否定「丁火就是燈燭」的物象化說法，再以「較丙火則柔中」界定丁火與丙火的差異。因此可安全使用「柔中」作為核心判斷，但不應過度推導成固定人格。

**Product use:**
- free
- full

**Variants supported:**
- core
- in_relationship
- in_breakup
```

---

## Confidence 判斷

### DOCTRINE

多個權威來源一致，且沒有明顯派別爭議。

生產語氣：
```
命盤顯示...
```

### INTERPRETATION

有明確原文依據，但屬於作者觀點、注家詮釋，或從原文合理推導到產品場景。

生產語氣：
```
通常傾向...
在這個脈絡下，可以理解為...
```

### SPECULATIVE

跨系統對應、當代心理詮釋、沒有直接原典支持的產品推論。

生產語氣：
```
以下是光之谷研究團隊的觀察...
目前命理學界尚無共識...
```

預設不得進入 NT$499 內容。

---

## 文章與 Claim 的關係

文章段落必須引用 claim，不要讓生成用段落漂浮在來源之外。

推薦寫法：

```markdown
## core

丁火的核心不應被簡化成「燈燭」這個物象。據任鐵樵評註，
丁火相對丙火更偏向柔中、內明，重點在於氣質差異，而不是具體物品比喻。
（claims: bazi-tiangan-ding-huo-001）
```

驗證腳本會檢查：
- 是否有 `## Claims`
- claim id 是否符合 article id
- 是否有 source quote
- 是否有 source location
- variant 段落是否至少引用一個 claim id
- variant 引用的 claim 是否存在
- claim 的 `Variants supported` 是否包含該 variant
- source location 是否能解析到 `docs/research/sources.yml` 中登記的 raw file
- source quote 是否能在 cited raw line/range 找到
- `related` 與 typed `links` 是否互相對齊
- typed `links` target 是否存在、type 是否有效、reason 是否存在

---

## Raw Source Location

`Source location` 優先使用：

```
raw/path/file.txt:line
```

如果行號暫時不穩定，可以使用：

```
raw/path/file.txt section="通神論 七、天干"
```

但 V1 上線前應補齊行號，方便審核。

---

## 生產系統如何使用

編譯時，`compile_kb.py` 會將文章拆成三層 local JSON：

```
dist/kb/kb_articles.json
  - slug
  - title
  - variants
  - confidence
  - variant_claims

dist/kb/kb_claims.json
  - claim_id
  - article_slug
  - claim
  - source_quote
  - source_location
  - confidence
  - product_use
  - variants_supported

dist/kb/kb_links.json
  - typed frontmatter links
  - related links
  - wiki links
  - reason
  - resolved flag
```

V0 可以先不建立 Supabase `kb_claims` table，但 markdown 必須先照這個格式寫。
目前 local compiler 已可產生 JSON；後續 Supabase sync 只需沿用這份 contract。

注意：article-level `confidence` 只作為文章預設標籤。產品 runtime 必須優先使用 claim-level `confidence`，避免把 `INTERPRETATION` 或 `SPECULATIVE` 推論升級成教義。

---

## 最小測試集建議

第一批測試文章不求多，重點是跑通整個流程：

1. `wiki/bazi/tiangan/ding-huo.md`
2. `wiki/bazi/tiangan/yi-mu.md`
3. `wiki/bazi/wuxing/mu-sheng-huo.md`
4. `wiki/context/stages/cold-war.md`
5. `wiki/context/questions/still-love-me.md`
6. `wiki/context/tone/valley-of-light-voice.md`

這 6 篇足以測試：
- 原典引用
- article variants
- claim IDs
- context retrieval
- 免費結果頁的三個洞察
- brand voice gating

---

## 與其他文件的關聯

- KB 操作規則：`AGENTS.md`
- 生產整合：`docs/tech/05-kb-integration.md`
- Prompt 策略：`docs/tech/06-llm-prompt-strategy.md`
- 驗證工具：`scripts/validate.py`
