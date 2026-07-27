# 03 - Database Schema
## Supabase / PostgreSQL 資料庫結構

> Production commerce update (2026-07-25): the `users`, `readings`,
> `payments`, and email-link examples in this document predate the active
> paid-only WooCommerce guest-checkout decision. They are not production DDL.
> Use `docs/tech/13-production-commerce-and-reading-delivery-architecture.md`
> for the launch customer/order/fulfillment/access model. Existing KB runtime
> migrations remain the source of truth for KB tables.

> Schema planning contains old free/paid funnel fields.
> Current astrology V1 should persist one complete paid reading result. Any
> `free_reading`, locked-preview, or upsell-specific fields are legacy until the
> schema is migrated to the complete-result contract.
> Product contract: `docs/product/00-current-v1-contract.md`.

---

## Schema 總覽

```
┌─────────────────┐
│     users       │  匿名用戶或登入用戶
└─────────────────┘
        │
        ↓ 1:N
┌─────────────────┐
│    readings     │  每次合盤分析
└─────────────────┘
   │       │
   │       ↓ 1:N
   │   ┌─────────────┐
   │   │  questions  │  AI 問答記錄
   │   └─────────────┘
   ↓ 1:N
┌─────────────────┐
│    payments     │  付款記錄
└─────────────────┘

┌─────────────────┐
│   kb_articles   │  KB 文章 + embedding
└─────────────────┘

┌─────────────────┐
│  ritual_orders  │  實體儀式包訂單
└─────────────────┘
```

---

## 完整 DDL

### users 表

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE,
  phone TEXT,
  line_user_id TEXT,
  
  -- 用戶偏好（V2 才用）
  preferences JSONB DEFAULT '{}',
  
  -- 元資料
  created_at TIMESTAMPTZ DEFAULT NOW(),
  last_active_at TIMESTAMPTZ,
  
  -- Risk flags（情緒風險用戶標記）
  risk_flags JSONB DEFAULT '{}'
  -- 範例: {"crisis_keywords_detected": true, "flagged_at": "..."}
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_phone ON users(phone);
```

**注意：** V1 不強制註冊。用戶填問卷時建立匿名 user（email 選填）。

---

### readings 表

```sql
CREATE TABLE readings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  
  -- 輸入資料
  person_a JSONB NOT NULL,
  -- 範例: {
  --   "birth_date": "1995-11-04",
  --   "birth_time": "13:00",
  --   "birth_place": "Taichung, Taiwan",
  --   "birth_timezone": "Asia/Taipei",
  --   "gender": "female"
  -- }
  
  person_b JSONB NOT NULL,
  
  context JSONB NOT NULL,
  -- 範例: {
  --   "stage": "cold_war",
  --   "who_initiated": "them",
  --   "last_contact": "month_plus",
  --   "relationship_length": "1-3y",
  --   "main_question": "still_love_me"
  -- }
  
  -- 計算結果（cache 用）
  calculation_result JSONB,
  -- 包含完整的八字、星盤、合盤計算結果
  -- 結構化資料，給 LLM 與前端共用
  
  -- 解讀內容（分層儲存）
  free_reading JSONB,    -- 三個免費洞察 + 鎖定預覽
  full_report JSONB,     -- NT$499 報告（付費後填入）
  deep_report JSONB,     -- NT$2,480 報告（升級後填入）
  
  -- 狀態
  tier TEXT NOT NULL DEFAULT 'free',
  -- 'free' | 'full' | 'deep'
  
  paid_at TIMESTAMPTZ,
  upgraded_at TIMESTAMPTZ,
  
  -- 元資料
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- 分析追蹤
  llm_tokens_used INT,
  llm_cost_usd DECIMAL(10, 6),
  cache_hit BOOLEAN DEFAULT FALSE,
  generation_duration_ms INT
);

CREATE INDEX idx_readings_user_id ON readings(user_id);
CREATE INDEX idx_readings_tier ON readings(tier);
CREATE INDEX idx_readings_created_at ON readings(created_at DESC);
CREATE INDEX idx_readings_paid_at ON readings(paid_at DESC);
```

---

### questions 表

```sql
CREATE TABLE questions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  reading_id UUID REFERENCES readings(id) NOT NULL,
  
  question TEXT NOT NULL,
  answer TEXT,
  
  -- 引用的 KB 文章 ids
  relevant_kb_articles JSONB,
  -- 範例: ["bazi-tiangan-ding-huo", "bazi-hehun-rizhi-chong"]
  
  -- 危機關鍵字偵測
  crisis_detected BOOLEAN DEFAULT FALSE,
  crisis_keywords JSONB,
  -- 範例: ["想死", "活不下去"]
  
  -- 元資料
  created_at TIMESTAMPTZ DEFAULT NOW(),
  llm_tokens_used INT,
  llm_cost_usd DECIMAL(10, 6),
  generation_duration_ms INT
);

CREATE INDEX idx_questions_reading_id ON questions(reading_id);
CREATE INDEX idx_questions_crisis ON questions(crisis_detected) WHERE crisis_detected = TRUE;
```

---

### payments 表

```sql
CREATE TABLE payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  reading_id UUID REFERENCES readings(id) NOT NULL,
  user_id UUID REFERENCES users(id),
  
  -- 金額
  amount INTEGER NOT NULL,  -- TWD，整數（NT$499 -> 499）
  currency TEXT DEFAULT 'TWD',
  tier TEXT NOT NULL,        -- 'full' | 'deep'
  
  -- 綠界資料
  payment_method TEXT,        -- 'ecpay_credit_card', 'ecpay_atm', 'ecpay_cvs', 'line_pay', 'apple_pay'
  ecpay_merchant_trade_no TEXT UNIQUE,
  ecpay_trade_no TEXT,
  ecpay_payment_date TIMESTAMPTZ,
  
  -- 狀態
  status TEXT NOT NULL DEFAULT 'pending',
  -- 'pending' | 'paid' | 'failed' | 'refunded'
  
  paid_at TIMESTAMPTZ,
  refunded_at TIMESTAMPTZ,
  refund_reason TEXT,
  
  -- 元資料
  created_at TIMESTAMPTZ DEFAULT NOW(),
  raw_response JSONB  -- 完整保留綠界回應，debug 用
);

CREATE INDEX idx_payments_reading_id ON payments(reading_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_payments_paid_at ON payments(paid_at DESC);
CREATE UNIQUE INDEX idx_payments_ecpay_trade ON payments(ecpay_merchant_trade_no);
```

---

### KB runtime tables

Current source of truth:

```
supabase/migrations/20260519152111_init_kb_runtime.sql
supabase/migrations/20260525095713_add_structured_kb_runtime.sql
supabase/migrations/20260525112318_add_question_blueprint_version.sql
```

V0 uses KB runtime tables for both source-backed content and deterministic reducer records:
- `kb_articles` — compiled article metadata, variants, claim ids, controlled links.
- `kb_claims` — claim-level evidence, source location, confidence, product use.
- `kb_links` — typed / related / body wiki graph for deterministic retrieval expansion.
- `kb_atoms` — machine-readable interpretation atoms with selectors and source claim ids.
- `kb_rulesets` / `kb_rules` — question-specific reducer rules and ruleset manifests.
- `kb_question_blueprints` — question contracts, chapter structure, forbidden claims, and paid boundaries.
- `kb_guardrail_sets` / `kb_guardrails` — precision, safety, and method boundaries.
- `kb_sync_runs` — audit trail for JSON → Supabase sync jobs.

Raw books stay in the private Git repo and are not synced into Supabase.
The public frontend does not read KB tables directly; runtime APIs should select and reduce evidence server-side.
The migration enables `vector`, but does not create embedding columns yet. We will add a separate embedding migration after choosing the embedding model and vector dimension.

### kb_articles 表（early design, superseded by migration above）

```sql
-- 啟用 pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE kb_articles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- 識別
  slug TEXT UNIQUE NOT NULL,
  -- 範例: 'bazi-tiangan-yi-mu'
  
  category TEXT NOT NULL,
  -- 範例: 'bazi/tiangan', 'western/synastry', 'cross', 'context/stages'
  
  title TEXT NOT NULL,
  title_en TEXT,
  
  -- 內容（從 wiki/*.md frontmatter + body 萃取）
  content TEXT NOT NULL,
  
  -- Variants（如有，例如 in_relationship / in_breakup / in_general）
  variants JSONB,
  -- 範例: {
  --   "core": "...",
  --   "in_relationship": "...",
  --   "in_breakup": "..."
  -- }
  
  -- 來源
  source_book TEXT,
  source_chapter TEXT,
  source_secondary JSONB,
  
  -- 信心等級
  confidence TEXT NOT NULL,
  -- 'DOCTRINE' | 'INTERPRETATION' | 'SPECULATIVE'
  
  -- 適用情境（給 retrieval 用）
  applicable_products JSONB,
  -- 範例: ["relationship_compatibility", "personal_bazi"]
  
  relationship_stage JSONB,
  -- 範例: ["all"] 或 ["broke_up_recent", "cold_war"]
  
  question_relevance JSONB,
  -- 範例: ["still-love-me", "what-did-i-do-wrong"]
  
  -- 跨文章引用
  related_ids JSONB,
  -- 範例: ["bazi-tiangan-jia-mu", "bazi-wuxing-mu"]

  links JSONB,
  -- typed internal link graph from wiki frontmatter
  -- 範例: [{"target": "western-transits-timing-window", "type": "timing", "reason": "..."}]
  
  -- Embedding（用於語意搜尋）
  embedding vector(768),  -- multilingual MPNet 維度
  title_embedding vector(768),
  
  -- 元資料
  status TEXT NOT NULL DEFAULT 'published',
  -- 'draft' | 'review' | 'published' | 'deprecated'
  
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  last_reviewed_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_kb_articles_slug ON kb_articles(slug);
CREATE INDEX idx_kb_articles_category ON kb_articles(category);
CREATE INDEX idx_kb_articles_confidence ON kb_articles(confidence);
CREATE INDEX idx_kb_articles_status ON kb_articles(status);

-- Vector search index
CREATE INDEX idx_kb_articles_embedding ON kb_articles 
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

---

### ritual_orders 表

```sql
CREATE TABLE ritual_orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  reading_id UUID REFERENCES readings(id) NOT NULL,
  user_id UUID REFERENCES users(id) NOT NULL,
  payment_id UUID REFERENCES payments(id),
  
  -- 訂單內容
  ritual_types JSONB NOT NULL,
  -- 範例: ["cleansing", "self_restoration", "connection"]
  
  -- 寄送資訊
  recipient_name TEXT NOT NULL,
  recipient_phone TEXT NOT NULL,
  shipping_address TEXT NOT NULL,
  shipping_notes TEXT,
  
  -- 金額
  amount INTEGER NOT NULL,  -- 通常 890
  
  -- 物流
  shipping_status TEXT NOT NULL DEFAULT 'pending',
  -- 'pending' | 'packed' | 'shipped' | 'delivered' | 'failed'
  
  tracking_number TEXT,
  shipped_at TIMESTAMPTZ,
  delivered_at TIMESTAMPTZ,
  
  -- 元資料
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ritual_orders_user_id ON ritual_orders(user_id);
CREATE INDEX idx_ritual_orders_status ON ritual_orders(shipping_status);
```

---

### analytics_events 表（用於 funnel 追蹤）

```sql
CREATE TABLE analytics_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  reading_id UUID REFERENCES readings(id),
  
  event_type TEXT NOT NULL,
  -- 範例:
  -- 'landing_view'
  -- 'questionnaire_start'
  -- 'questionnaire_step_1'
  -- 'questionnaire_step_5'
  -- 'free_result_view'
  -- 'free_insight_view'
  -- 'unlock_cta_click'
  -- 'payment_initiated'
  -- 'payment_completed'
  -- 'full_report_view'
  -- 'ai_question_asked'
  -- 'upgrade_cta_click'
  -- 'ritual_order_placed'
  
  event_data JSONB,
  
  -- 元資料
  session_id TEXT,
  user_agent TEXT,
  referrer TEXT,
  utm_source TEXT,
  utm_medium TEXT,
  utm_campaign TEXT,
  
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_events_user_id ON analytics_events(user_id);
CREATE INDEX idx_events_type ON analytics_events(event_type);
CREATE INDEX idx_events_created_at ON analytics_events(created_at DESC);
```

注意：這些事件也會 fork 到 Posthog（雙重儲存：DB 保留完整資料 + Posthog 做視覺化分析）。

---

## Row Level Security (RLS)

Supabase 內建 RLS，需設定：

### users 表

```sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- 用戶只能看自己的資料
CREATE POLICY "Users can view own profile"
  ON users FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON users FOR UPDATE
  USING (auth.uid() = id);
```

### readings 表

```sql
ALTER TABLE readings ENABLE ROW LEVEL SECURITY;

-- 用戶只能看自己的 reading
CREATE POLICY "Users can view own readings"
  ON readings FOR SELECT
  USING (auth.uid() = user_id);

-- 但匿名用戶也能看（透過 reading_id + access_token）
-- 這個透過 server-side 邏輯實現，不靠 RLS
```

### kb_articles 表

```sql
ALTER TABLE kb_articles ENABLE ROW LEVEL SECURITY;

-- KB 文章只能 backend 服務讀取（用 service_role key）
-- 前端永遠不該直接讀 KB
CREATE POLICY "Only service role can access KB"
  ON kb_articles FOR ALL
  USING (auth.jwt()->>'role' = 'service_role');
```

---

## Migration 策略

使用 Supabase Migrations：

```
supabase/
└── migrations/
    ├── 20260517000001_initial_schema.sql
    ├── 20260517000002_kb_articles.sql
    ├── 20260517000003_ritual_orders.sql
    └── ...
```

每次 schema 變動：
1. 建立新的 migration 檔案
2. 本地 Supabase 測試
3. 部署到 production

---

## 備份策略

### 自動備份

Supabase Pro plan 包含：
- 每日 backup
- Point-in-time recovery (PITR)

### 手動備份（KB 資料）

```bash
# 每週備份 kb_articles 表（最重要的 IP）
pg_dump -t kb_articles > kb_backup_$(date +%Y%m%d).sql

# 上傳到獨立的 R2 bucket
rclone copy kb_backup_*.sql r2:valley-of-light-backups/
```

---

## 容量規劃

### 預估資料量（一年後）

```
users:          ~50,000 rows  (約 10 MB)
readings:       ~30,000 rows  (約 500 MB - 含 JSONB)
questions:      ~80,000 rows  (約 100 MB)
payments:       ~5,000 rows   (約 5 MB)
kb_articles:    ~300 rows     (約 50 MB - 含 embeddings)
ritual_orders:  ~200 rows     (約 1 MB)
analytics_events: ~5M rows    (約 2 GB - 最大表)

總計：~ 3 GB
```

Supabase Pro plan（$25/月）包含 8 GB，足夠 V1 第一年使用。

---

## 與其他文件的關聯

- 技術棧：`tech/01-tech-stack.md`
- 後端架構：`tech/02-backend-architecture.md`
- KB 整合：`tech/05-kb-integration.md`
