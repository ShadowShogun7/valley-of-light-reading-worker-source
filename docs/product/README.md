# Product Documents

產品設計層 — 回答「產品具體長什麼樣、用戶怎麼用」。

## 文件

- **00-current-v1-contract.md** — active paid-only Western V1 source of truth
- **01-product-tiers.md** — legacy 三層產品架構（免費 / NT$499 / NT$2,480）
- **02-landing-page-flow.md** — legacy old funnel landing page copy
- **03-onboarding-questions.md** — partial legacy 五步問卷設計；context fields still useful
- **04-free-result-page.md** — legacy 免費結果頁設計（舊 funnel 參考）
- **05-paid-report-structure.md** — legacy NT$499 完整報告七大 section（舊 funnel 參考）
- **06-ritual-system.md** — legacy / future NT$2,480 復合儀式系統
- **07-reading-contract.md** — 一次完整關係解讀的 intake / selector / result 資料合約
- **08-result-dashboard-design.md** — legacy 免費結果儀表板視覺與互動規格（舊 funnel 參考）
- **09-frontend-flow-view-model.md** — 前端 flow 與 CompleteRelationshipResultViewModel 合約
- **10-bazi-reading-interpreter.md** — 八字計算事實轉成人話 reading 的解釋層
- **11-western-relationship-reading-framework.md** — 西洋合盤優先階段的 reading 架構與產品參考
- **12-astrology-session-handoff.md** — 新西洋星盤 session / branch / workspace handoff
- **13-western-suskin-method-system.md** — Rod Suskin P0 方法源導入後的 Western runtime 順序、clusters、atoms、guardrails 與驗證方式
- **14-paid-v1-result-section-contract.md** — paid V1 五段結果頁 runtime / evidence contract
- **16-paid-v1-native-copy-contract.md** — paid V1 繁體中文可讀 copy contract
- **17-paid-v1-precision-layer-boundary-contract.md** — precision-gated visible interpretation boundary
- **18-paid-v1-relationship-thesis-contract.md** — hidden relationship-thesis synthesis layer contract
- **19-final-narrative-native-zh-tw-realization-contract.md** — locked final Traditional Chinese realization and future-upgrade integration contract
- **20-production-commerce-legal-copy-zh-tw.md** — active paid V1 checkout, generation-consent, cancellation/refund, and privacy launch-copy draft

## 閱讀順序

按用戶旅程順序讀：
1. Astrology current V1: 00（Current V1 Contract） → 14（Paid V1 Sections） → 18（Relationship Thesis） → 19（Final Chinese Realization） → 16（Native Copy） → 09（Frontend ViewModel） → 13（Suskin Method System） → 11（Western Framework） → 20（Production Commerce Legal Copy）
2. BaZi continuation: 03（問卷 context fields） → 07（Reading Contract） → 10（BaZi Interpreter） → 09（Frontend ViewModel）
3. Legacy funnel reference only: 01（Tiers） → 04（免費結果策略） → 08（結果儀表板） → 05（付費報告） → 06（儀式）

## Current Contract

Current astrology product flow is Western-only while BaZi is on hold:

```text
five-step onboarding
    ↓
five runtime context fields
    ↓
Western chart calculation + candidate signals
    ↓
Western relationship case file
    ↓
complete relationship result dashboard
    ↓
future deep reading can expand relationship chart layers, timing, and action strategy
```

V1 is one `NT$1,280` paid complete reading. Do not design a free result page,
locked teaser rows, `NT$499` upsell, or in-result deep-report CTA unless the
product direction changes again.

Keep `03-onboarding-questions.md`, `07-reading-contract.md`, and
`09-frontend-flow-view-model.md` aligned with `docs/tech/02-backend-architecture.md`
and `docs/tech/06-llm-prompt-strategy.md`.

`10-bazi-reading-interpreter.md` remains the reference for the paused BaZi path.
`04-free-result-page.md`, `05-paid-report-structure.md`, and
`08-result-dashboard-design.md` are legacy funnel references until they are
rewritten for the paid-only cosmic result design.

## 變動原則

產品文件**會隨用戶反饋演化**。
重大改動時要在 `docs/CHANGELOG.md` 記錄（未來建立）。
