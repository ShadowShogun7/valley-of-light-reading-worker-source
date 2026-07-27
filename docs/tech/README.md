# Tech Documents

技術架構層 — 回答「怎麼蓋這個產品」。

## 文件

- **01-tech-stack.md** — 完整技術棧與開源依賴
- **02-backend-architecture.md** — 後端模組設計、API endpoints
- **03-database-schema.md** — Supabase / PostgreSQL schema
- **04-calculation-engines.md** — 八字 + 西洋計算引擎
- **05-kb-integration.md** — KB 系統的三層架構與整合
- **06-llm-prompt-strategy.md** — LLM 在三層系統中的角色與 prompt 設計
- **07-claim-schema.md** — claim-level 來源追蹤與驗證格式
- **08-retriever-contract.md** — Supabase KB 檢索與 prompt bundle 合約
- **09-structured-kb-atoms-rules.md** — YAML atoms/rules 與 deterministic reducer layer
- **10-hosted-supabase-cutover.md** — hosted Supabase structured KB migration/sync runbook
- **11-final-narrative-fact-contract.md** — 最終解讀層的 typed facts、頁面 ownership 與 fact-only isolation
- **12-final-narrative-fact-renderer.md** — 五頁 locked renderer、自然繁中規則與 production release gates
- **13-production-commerce-and-reading-delivery-architecture.md** — WordPress / WooCommerce payment-first guest checkout、post-payment intake、email access 與 production launch gates
- **14-production-launch-readiness.md** — 已實作、本機驗證、live WordPress 狀態、上線 gate 與仍需使用者核准的 blockers
- **15-staging-commerce-e2e-runbook.md** — 隔離 staging 建置、Woo 離線付款測試、綠界 sandbox 與 production approval 邊界
- **16-agpl-production-compliance.md** — AGPL 部署決策、公開 source release 與 fail-closed production controls

## 閱讀順序

依層次讀：
1. 01（技術棧總覽）
2. 02（架構）→ 03（資料）
3. 04（計算引擎）→ 05（KB）→ 07（Claim Schema）→ 09（Atoms/Rules）→ 08（Retriever）→ 06（LLM）

如果只是要建 KB（不寫程式），讀 05 + 07，然後跑 `python3 scripts/validate.py`。
如果要確認 KB 可進入 runtime data，接著跑 `python3 scripts/compile_kb.py`。
如果要確認 structured atoms/rules，接著跑 `python3 scripts/compile_structured_kb.py`。
如果要確認 legacy selector primary selection，接著跑 `python3 scripts/select_signals.py --scenario examples/retrieval/cold-war-still-love-me.json --include-drafts`。
如果要確認 Supabase runtime bundle，接著跑 `python3 scripts/retrieve_kb.py --scenario examples/retrieval/cold-war-still-love-me.json --include-drafts`。
如果要把 structured KB 切到 hosted Supabase，讀 `docs/tech/10-hosted-supabase-cutover.md`。
如果要確認目前 astrology 產品輸出契約，讀 `docs/product/03-onboarding-questions.md`、`docs/product/07-reading-contract.md`、`docs/product/09-frontend-flow-view-model.md`、`docs/tech/02-backend-architecture.md`、`docs/tech/06-llm-prompt-strategy.md`。
如果要準備正式上線的付款、訂單、結果寄送與免帳號找回流程，讀 `docs/tech/13-production-commerce-and-reading-delivery-architecture.md`。
如果要判斷目前能否上線、確認 launch gate 與待核准項目，讀 `docs/tech/14-production-launch-readiness.md`。
如果要建立隔離 staging 並跑不扣款的 WordPress/WooCommerce 全流程，讀 `docs/tech/15-staging-commerce-e2e-runbook.md`。
如果要發布 calculation worker，先讀 `docs/tech/16-agpl-production-compliance.md` 並完成公開 source release。
如果要跑完整 reading harness，使用 `python3 scripts/build_reading_context.py --reading examples/readings/cold-war-still-love-me.json --include-drafts --json`。

## 重要

核心 reading 技術選型仍維持 Supabase 與既有 calculation/runtime stack。
正式商務邊界已改為 WordPress + WooCommerce；付款 gateway 可沿用綠界，
但應透過通過 sandbox 驗證的 WooCommerce 模組，而不是照舊文件直接串接
ECPay SDK。正式上線以 `13-production-commerce-and-reading-delivery-architecture.md`
為準；`01-tech-stack.md` 與 `03-database-schema.md` 內舊 funnel、直接付款與
帳號 schema 範例只作歷史參考。
