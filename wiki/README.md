# Wiki — KB 文章主體

這是光之谷的**核心 IP**。
所有結構化的命理知識整理在這裡。

## 子目錄

- `bazi/` — 八字命理（天干、地支、十神、五行、合婚、格局）
- `western/` — 西洋占星（行星、星座、宮位、相位、合盤）
- `cross/` — 中西交叉（最高戰略價值）
- `context/` — 情境化解讀框架（用戶階段、問題、語氣）

## 兩種主要分類

### 命理知識層（bazi + western + cross）
這層是「命理事實」— 古典書籍提取的客觀內容。
LLM 萃取時必須完整保留原典出處。

### 情境框架層（context）
這層不是命理知識，是「告訴生產 LLM 怎麼針對不同用戶寫解讀」的指引。
與 docs/brand/03-voice-and-tone.md 配合使用。

## 撰寫規範

詳見：
- `../AGENTS.md` — KB 維護規範（必讀）
- `../docs/tech/07-claim-schema.md` — claim-level 來源追蹤格式
- `../docs/brand/03-voice-and-tone.md` — 語氣規範
- `../docs/brand/04-copywriting-guidelines.md` — 文案準則

每篇正式文章都要包含 `## Claims`，並在 variants 中用
`(claims: claim-id)` 標註來源判斷。這是生產系統避免 LLM 憑空推論的核心防線。

## 命名規範

- 檔名用 kebab-case 或繁中（保持一致）
- ID 在 frontmatter 用 kebab-case
- 例：`yi-mu.md` 或 `乙木.md`（V0.1 決定用繁中檔名 + kebab-case ID）

## 統計

當前文章數：0
目標 V1：~100 篇基礎文章
目標 V2：~300 篇文章（含中西交叉與多產品變體）
