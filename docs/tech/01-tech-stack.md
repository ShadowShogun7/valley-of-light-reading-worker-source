# 01 - Tech Stack
## 完整技術選型與依賴

> Active technical stack with some old funnel-planning examples.
> If this document references free analysis, `NT$499`, `NT$2,480`, or the old
> tiered funnel, treat those as legacy planning notes. Current astrology V1 is
> one `NT$1,280` paid complete Western relationship reading.
> Product contract: `docs/product/00-current-v1-contract.md`.
>
> Production commerce update (2026-07-25): WordPress + WooCommerce now own
> guest checkout and order management. ECPay may remain the payment gateway
> through its supported WooCommerce module. The direct ECPay SDK, payment,
> account, email-delivery, and deployment examples below are legacy planning
> notes where they conflict with
> `docs/tech/13-production-commerce-and-reading-delivery-architecture.md`.

> 此文件鎖定所有技術決策。任何套件、服務、版本變動都應更新此文件。

---

## 技術棧總覽

```
┌─────────────────────────────────────────────┐
│  FRONTEND（前端）                            │
│  Next.js 16 + React 19 + TypeScript        │
│  部署：Vercel                                │
└─────────────────────────────────────────────┘
                    ↓ HTTPS/JSON
┌─────────────────────────────────────────────┐
│  BACKEND API（後端）                         │
│  Python 3.11 + FastAPI + Pydantic v2       │
│  部署：Railway 或 Zeabur                     │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  DATA LAYER（資料層）                        │
│  Supabase                                   │
│  (Postgres + Auth + Storage + pgvector)    │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  EXTERNAL SERVICES                          │
│  Claude API · 綠界 ECPay · Resend · R2     │
└─────────────────────────────────────────────┘
```

---

## 為什麼這套架構

### 為什麼前後端分離

- **SEO 需要 SSR** — 思雅型 ICP 主要從 Google 進入
- **後端可獨立 scale** — LLM 呼叫和計算密集任務需要彈性
- **計算邏輯不暴露在前端** — 保護 IP

### 為什麼後端用 Python

- `immanuel-python`（西洋占星計算）只有 Python 版
- `sxtwl`（八字計算）原生 Python
- Claude API SDK Python 較成熟
- 處理命盤資料用 numpy/pandas 自然

### 為什麼用 Supabase 取代分散服務

之前考慮過 Postgres + Auth0 + S3 + Pinecone 分開架。
但 Supabase 一站全包：
- PostgreSQL（資料庫）
- Auth（用戶認證）
- Storage（檔案儲存）
- pgvector（KB 向量搜尋）
- Realtime（AI 問答串流）
- Edge Functions（簡單後端邏輯）

**V1 階段可以暫時不需要獨立後端 server，用 Supabase Edge Functions 處理大部分邏輯。**
省下開發初期至少 30% 的時間。

### 為什麼用綠界 ECPay 而非 TapPay 或 Stripe

- 信用卡 + ATM + 超商代碼 + Apple Pay + Google Pay + LINE Pay **全包**
- 思雅型 ICP 習慣這些付款方式
- 中小企業手續費合理（約 2.6%）
- 沙箱環境免費測試
- Stripe 對台灣商家有限制
- TapPay SDK 較現代但覆蓋面不如綠界

---

## 完整開源依賴清單

### 命盤計算

**immanuel-python**
- GitHub: https://github.com/theriftlab/immanuel-python
- License: AGPL-3.0
- 用途：本命盤、合盤、行運計算
- 底層：Swiss Ephemeris
- ⚠️ AGPL 需要正式 compliance strategy；不要假設 server-side SaaS 自動安全

**pyswisseph**
- GitHub: https://github.com/astrorigin/pyswisseph
- License: AGPL-3.0 / Swiss Ephemeris Professional License
- 用途：immanuel-python 的底層星曆計算
- 精度：NASA JPL DE441 級

**sxtwl**
- GitHub: https://github.com/yuangu/sxtwl_cpp
- Python wrapper: https://pypi.org/project/sxtwl/
- License: BSD-3-Clause
- 用途：農曆轉換、八字四柱、節氣計算

**lunar_python**（BaZi verifier / fallback）
- GitHub: https://github.com/6tail/lunar-python
- PyPI: https://pypi.org/project/lunar_python/
- License: MIT
- 用途：八字四柱、藏干、十神等高階欄位交叉驗證；不直接採用黃曆/神煞解讀

**kerykeion**（Western dashboard candidate）
- GitHub: https://github.com/g-battaglia/kerykeion
- License: AGPL-3.0
- 用途：chart-ready data、SVG chart、synastry/transit/composite dashboard probe
- 注意：built-in relationship score 只可做 debug，不可當產品判斷真相

**iztro**（V2 才用）
- GitHub: https://github.com/SylarLong/iztro
- License: MIT
- 用途：紫微斗數（如未來 V4 加入紫微作為第三系統）
- 注意：是 JavaScript/TypeScript

---

### 後端框架

**FastAPI**
- GitHub: https://github.com/tiangolo/fastapi
- License: MIT
- 版本：0.110+
- 為什麼選：原生 async、自動 OpenAPI 文件、Pydantic 整合

**Uvicorn**
- GitHub: https://github.com/encode/uvicorn
- License: BSD-3-Clause
- 用途：ASGI server

**Pydantic v2**
- GitHub: https://github.com/pydantic/pydantic
- License: MIT
- 用途：資料驗證、API schema
- 為什麼選：v2 用 Rust 重寫後速度極快

---

### 資料庫客戶端

**supabase-py**
- GitHub: https://github.com/supabase-community/supabase-py
- License: MIT
- 用途：Supabase Python SDK

**asyncpg**（如需直接連 Postgres）
- GitHub: https://github.com/MagicStack/asyncpg
- License: Apache-2.0
- 用途：高效能 async PostgreSQL client

---

### LLM 整合

**anthropic-sdk-python**
- GitHub: https://github.com/anthropics/anthropic-sdk-python
- License: MIT
- 模型選擇：
  - **免費合盤：** claude-sonnet-4.6（速度快、成本低）
  - **完整報告（NT$499）：** claude-opus-4.6（品質最高）
  - **AI 問答：** claude-sonnet-4.6（速度優先）

---

### 知識庫與向量檢索

**sentence-transformers**
- GitHub: https://github.com/UKPLab/sentence-transformers
- License: Apache-2.0
- 用途：生成中文 embedding
- 推薦模型：`paraphrase-multilingual-mpnet-base-v2`

**pgvector**（Supabase 內建）
- GitHub: https://github.com/pgvector/pgvector
- License: PostgreSQL License
- 用途：在 Supabase 內存 KB embedding，做語意搜尋

**python-frontmatter**
- 用途：解析 markdown 文件的 YAML frontmatter
- 用於：編譯 `wiki/*.md` 到資料庫

---

### 付款（綠界 ECPay）

**ECPayAIO_Python**
- GitHub: https://github.com/ECPay/ECPayAIO_Python
- License: MIT
- 用途：綠界全方位金流串接
- 支援：信用卡、ATM、超商代碼、超商條碼、Apple Pay、Google Pay
- 文件：https://developers.ecpay.com.tw/?p=2855

⚠️ 綠界 SDK 較老派，建議自己寫 wrapper 簡化使用。

---

### 前端框架

**Next.js 16**
- GitHub: https://github.com/vercel/next.js
- License: MIT
- 模式：App Router
- 為什麼：SSR 利於 SEO、Vercel 親兒子
- The paid result app currently resolves `next@16.2.12`; keep the lockfile and
  production dependency audit green before each release.

**React 19** + **TypeScript**

Styling:
- V0 result dashboard prototype uses explicit CSS tokens in `apps/web/src/app/globals.css` to match the custom warm ivory dashboard theme.
- Tailwind CSS can still be introduced when the shared design system stabilizes, but it is not required for the first result-dashboard build.

**shadcn/ui**
- GitHub: https://github.com/shadcn-ui/ui
- License: MIT
- 為什麼：複製進專案，完全可客製化

**react-hook-form** + **zod** + **@hookform/resolvers**
- 用途：表單管理（五步問卷）

**framer-motion**
- License: MIT
- 用途：動畫（loading 動畫、頁面轉場）

**lucide-react**
- 用途：Icon library

---

### PDF 生成

**WeasyPrint**
- GitHub: https://github.com/Kozea/WeasyPrint
- License: BSD-3-Clause
- 用途：HTML/CSS → PDF
- 為什麼選：純 Python、支援中文、CSS 排版能力強

---

### 信件發送

**Resend**
- 網址：https://resend.com
- GitHub: https://github.com/resend/resend-python
- 為什麼：dev-friendly、React Email 整合好
- 用途：訂單確認、報告連結、儀式包出貨通知

---

### 儲存（PDF 報告）

**Cloudflare R2**
- 網址：https://www.cloudflare.com/products/r2/
- 為什麼選：比 AWS S3 便宜 70%、無 egress fee
- 用於：生成的 PDF 報告

**或 Supabase Storage**（V1 階段量小可以先用）

---

### 監控

**Sentry**
- 用途：錯誤追蹤、效能監控

**Posthog**
- 用途：用戶行為分析、funnel 追蹤、A/B test
- 為什麼選：開源、可自架、隱私友善

---

## requirements.txt（Python 後端）

```python
# Core framework
fastapi==0.110.0
uvicorn[standard]==0.27.0
pydantic==2.6.0
python-dotenv==1.0.0

# Database
supabase==2.4.0
asyncpg==0.29.0
sqlalchemy==2.0.27

# Astrology / BaZi calculation
immanuel==1.5.4
pyswisseph==2.10.3.2
sxtwl==2.0.7
lunar_python==1.4.8
# Optional dashboard probe, not committed as production dependency until license path is decided:
# kerykeion==5.12.8

# LLM
anthropic==0.21.0

# Vector search & embeddings
sentence-transformers==2.5.0
numpy==1.26.0
python-frontmatter==1.1.0

# Payment (ECPay)
ecpay-payment-sdk==1.0.0

# Email
resend==0.7.0

# PDF generation
weasyprint==60.2

# Monitoring
sentry-sdk[fastapi]==1.40.0
posthog==3.4.0

# Utilities
httpx==0.27.0
python-multipart==0.0.9
```

---

## package.json（Next.js 前端核心依賴）

```json
{
  "dependencies": {
    "next": "14.1.0",
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "typescript": "5.3.0",
    "tailwindcss": "3.4.0",
    "@supabase/supabase-js": "2.39.0",
    "react-hook-form": "7.50.0",
    "zod": "3.22.0",
    "@hookform/resolvers": "3.3.0",
    "framer-motion": "11.0.0",
    "lucide-react": "0.330.0",
    "@radix-ui/react-dialog": "1.0.5",
    "@radix-ui/react-select": "2.0.0",
    "@radix-ui/react-radio-group": "1.1.3",
    "date-fns": "3.3.0",
    "posthog-js": "1.105.0"
  }
}
```

---

## License 整體檢查

對 SaaS 模式（光之谷的營運方式）的影響：

| License | 套件 | 影響 |
|---------|------|------|
| MIT | FastAPI, lunar_python, etc. | ✅ 完全自由 |
| Apache-2.0 | sentence-transformers | ✅ 完全自由 |
| BSD-3-Clause | sxtwl, WeasyPrint | ✅ 完全自由 |
| AGPL-3.0 | immanuel-python, pyswisseph, kerykeion | ⚠️ 需要正式 compliance strategy |

**結論：** BaZi calculation dependency risk is low. The Western calculation
service selected the AGPL path on 2026-07-27; every deployed worker now requires
a matching public source URL and archive checksum before startup.
Options:
- open-source the calculation microservice wrapper
- use hosted third-party API
- use an appropriate commercial Swiss Ephemeris path
- accept AGPL obligations intentionally and document them

---

## 成本估算

### V1 初期（月流量 < 5,000）

| 服務 | 方案 | 月成本 |
|------|------|--------|
| Vercel | Hobby | $0 |
| Railway | Hobby | $5 |
| Supabase | Free Tier | $0 |
| Claude API | 預估 | $50-200 |
| Cloudflare R2 | 預估 | $1-5 |
| Resend | Free Tier | $0 |
| Sentry | Developer | $0 |
| Posthog | Free | $0 |
| 綠界 | 交易手續費（從營收扣）| ~2.6% |
| **合計** | | **$60-220 / 月** |

### 中期（月流量 50,000）

| 服務 | 方案 | 月成本 |
|------|------|--------|
| Vercel | Pro | $20 |
| Railway | Pro | $20 |
| Supabase | Pro | $25 |
| Claude API | 大量用量 | $500-2,000 |
| 其他 | | $50 |
| **合計** | | **$615-2,115 / 月** |

**Claude API 是最大成本** — 這也是為什麼 caching 策略很重要（同樣的生日 + 同樣的問題用 cache，可省 70%）。

---

## 部署環境

### V1 推薦部署

```
前端：Vercel
  - 自動 CI/CD
  - Edge Network 含台灣節點
  - SEO 優化內建

後端：Railway 或 Zeabur
  - Railway：穩定、文件完整、亞洲節點
  - Zeabur：台灣團隊、中文 docs、學習曲線低

資料庫：Supabase
  - 全包資料層

儲存：Supabase Storage（V1）→ Cloudflare R2（V2 當流量大）

監控：Sentry + Posthog（兩者都有免費 tier）
```

### 域名建議

- 主域名：`valleyoflight.tw` 或 `光之谷.tw`
- API：`api.valleyoflight.tw`

---

## 開發環境設定

### 本地開發需要

1. Node.js 20+
2. Python 3.11+
3. Hosted Supabase project credentials
4. Claude API key
5. 綠界沙箱帳號

### 環境變數

```bash
# .env.local

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=xxx
SUPABASE_SERVICE_ROLE_KEY=xxx

# Anthropic
ANTHROPIC_API_KEY=sk-ant-xxx

# 綠界（沙箱）
ECPAY_MERCHANT_ID=2000132
ECPAY_HASH_KEY=xxx
ECPAY_HASH_IV=xxx
ECPAY_ENV=sandbox

# Resend
RESEND_API_KEY=xxx

# Sentry
SENTRY_DSN=xxx

# Posthog
POSTHOG_API_KEY=xxx
```

---

## V1 開發路線圖

```
Week 1-2：環境準備 + 計算引擎包裝
Week 3-4：KB 建立（先做八字基礎）
Week 5-6：免費合盤 + 結果頁
Week 7-8：付款 + NT$499 報告
Week 9-10：AI 問答系統
Week 11-12：測試 + 正式上線
```

---

## 與其他文件的關聯

- 後端模組設計：`tech/02-backend-architecture.md`
- 資料庫結構：`tech/03-database-schema.md`
- 計算引擎細節：`tech/04-calculation-engines.md`
- KB 整合：`tech/05-kb-integration.md`
- LLM Prompt 策略：`tech/06-llm-prompt-strategy.md`
