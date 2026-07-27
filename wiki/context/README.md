# 情境化解讀 KB 文章

**這層不是命理知識，是產品行為指引。**

告訴生產系統的 LLM：針對不同的用戶階段、問題、情境，
該用什麼語氣、該強調什麼、該避免什麼。

## 子目錄

- `stages/` — 4 個用戶階段（剛分手 / 冷凍 / 分手已久 / 危機）
- `questions/` — 5 個主要用戶問題（從 funnel Step 5）
- `tone/` — 品牌語氣指南

## 為什麼這層獨立存在

純命理知識（bazi/, western/, cross/）告訴 LLM「丁火日主是什麼」。
情境層告訴 LLM「面對剛分手的用戶，丁火日主該怎麼說」。

兩者結合，才產生個人化、有溫度的解讀。

## 與品牌文件的關係

```
docs/brand/03-voice-and-tone.md  ←→  wiki/context/tone/
（語氣的原則）              （給 LLM 用的可檢索版本）

docs/strategy/02-ideal-customer.md  ←→  wiki/context/stages/
（ICP 的人物描述）              （給 LLM 用的階段框架）

docs/product/03-onboarding-questions.md  ←→  wiki/context/questions/
（問卷設計）                     （給 LLM 用的問題框架）
```

兩者**內容呼應，但用途不同**：
- `docs/` 是給人類設計師、開發者讀的
- `wiki/context/` 是給生產 LLM 在 prompt 中讀的

## 建立順序

V0 必建：
1. `stages/cold-war.md` — 冷凍斷聯（主要 ICP 階段）✅
2. `questions/still-love-me.md` — 「他還愛我嗎」（最常被選的問題）✅
3. `questions/when-to-contact.md` — 「我什麼時候聯絡」✅
4. `tone/valley-of-light-voice.md` — 整體語氣基準

Note: `wiki/context/*` 目前仍要使用 claim-level source schema。品牌語氣若只引用內部產品文件，應先決定 validator 是否允許 `docs/` source locations。

V0.3 已完成：
- 4 個 stage 文章：`broke-up-recent` / `cold-war` / `broke-up-long` / `crisis` ✅
- 5 個 question 文章：`still-love-me` / `when-to-contact` / `any-chance` / `what-did-i-do-wrong` / `stay-or-let-go` ✅

下一步：先用 mixed-stage retrieval scenarios 測試 graph 寬度，再決定是否補 `tone/valley-of-light-voice.md` 的內部文件引用規則。
