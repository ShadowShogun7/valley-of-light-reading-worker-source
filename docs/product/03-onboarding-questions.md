# 03 - Onboarding Questions
## 七屏問卷設計

> Partial legacy reference.
> Field ideas such as relationship status, contact status, desired outcome, and
> main question still matter. Any free-result, locked-content, `NT$499`, or
> paid-report framing in this document is obsolete for current Western V1.
> Use `docs/product/00-current-v1-contract.md` and
> `docs/product/07-reading-contract.md` as the active contract.

---

## 為什麼是五步而非一頁

### 心理學原則

1. **單頁長表單轉換率比分頁低 30-40%**
2. **每填完一頁有「進度感」**（progress bar: 1/5, 2/5...）
3. **每一頁只專注一個情境，避免疲勞**
4. **後面的問題建立在前面的答案上**，用戶感到系統在「認真收集」
5. **情感投入累積到 Step 5 時達到頂峰**，付費抗拒力最低（commitment effect）

### 問題順序原則

從**外部事實**漸進到**內心問題**：

```
Step 1-2：生日資料（純客觀，零心理負擔）
Step 3：關係狀態 + 誰提分手（事實，但開始觸動）
Step 4：聯絡狀態 + 交往時間（需要回憶，情感投入加深）
Step 5：你最想知道什麼（觸及內心最深問題，情感最大化）
```

到 Step 5 時，用戶已投入 60-90 秒，回答了感情最私密的問題。
這個情感投入會讓她在 NT$499 解鎖時，抵抗力幾乎為零。

---

## Runtime Context Contract

UI 目前不再詢問「情緒狀態 / 安全感」作為獨立步驟，因為它不影響命盤準確度，且會讓流程變重。
Backend/runtime 需要把答案整理成四個用戶輸入 context fields，再由系統必要時推導 safety/risk。
這些欄位會直接影響 KB selector、free answer framing、paid report framing。

```json
{
  "relationship_stage": "cold-war",
  "main_question": "still-love-me",
  "contact_status": "no-contact",
  "desired_outcome": "reconnect",
  "emotional_risk": "not-collected"
}
```

Field mapping:

| Runtime field | 來源 | 用途 |
|---|---|---|
| `relationship_stage` | Step 3 關係狀態 | 選 `context-stage-*`，決定 `in_breakup` / `in_relationship` variant |
| `main_question` | Step 5 最想知道什麼 | 選 `context-question-*`，決定 free result 的 question lens；可見主標由 LLM 根據實際命盤重寫 |
| `contact_status` | Step 4 最近一次聯絡 | 影響 timing/action slot 與聯絡建議 |
| `desired_outcome` | Step 5 選項 + 後續 UI 可追問 | 決定 CTA 與 paid report 的策略 framing |
| `emotional_risk` | 不再由獨立 UI 問題收集；預設 `not-collected`，只在未來安全機制需要時推導 | 只作 safety guardrail，不作命盤判斷依據 |

Birth data is separate from this contract:
- birth data → calculation engine
- five context fields → selector + prompt tone

The free result should answer the selected `main_question` first, then use one BaZi core signal and one Western core signal as evidence.

---

## Step 1：你的資料

### 標題
```
先告訴我你自己的資料
```

### 副標
```
30 秒即可完成
```

### 欄位

```
[ 出生日期（必填） ]
  [日期選擇器]
  
[ 出生時間（選填） ]
  Hint: "知道時間？準確度 +70%"
  Sub-hint: "不知道也沒關係，仍能完成 80% 的分析"

[ 出生地（必填） ]
  Placeholder: "城市即可，例如：台北"
  Hint: "用於時區與西洋星盤計算"
  
[ 性別（必填） ]
  ○ 女
  ○ 男
  ○ 其他
```

### CTA
```
[ 下一步 → ]
進度：1 / 5
```

---

## Step 2：對方的資料

### 標題
```
接下來告訴我對方的資料
```

### 副標
```
兩個人的命盤，才能真正合盤
```

### 欄位

```
[ 出生日期（必填） ]
  [日期選擇器]
  
[ 出生時間（選填） ]
  Hint: "知道時間更精準"

[ 出生地（必填） ]
  Placeholder: "城市即可，例如：台北"
  Hint: "用於時區與西洋星盤計算"
  
[ 性別（必填） ]
  ○ 女
  ○ 男
  ○ 其他
```

### 底部小字
```
不知道對方生日？仍可只分析你自己 →
（連結到「個人命盤分析」分支，未來 V2 功能）
```

### CTA
```
[ 下一步 → ]
進度：2 / 5
```

---

## Step 3：你們現在的狀態

### 標題
```
告訴我，你們現在的狀況
```

### 副標
```
不同階段需要不同的解讀
```

### 問題 1：關係狀態

```
你們現在的關係狀態是？

○ 剛分手（兩週內）
○ 分手 2 週 - 2 個月
○ 分手 2 個月以上
○ 還在一起，但有危機
○ 一直曖昧，從未在一起
```

**用途：**
- 對應 `wiki/context/stages/` 的 4 個階段文章
- 決定 LLM 解讀的語氣與重點
- 觸發保護機制（剛分手用戶不推升級）

### 問題 2：誰提分手

```
是誰主動提分手的？

○ 他/她主動提的
○ 我主動提的，但現在後悔
○ 雙方協議分手
○ 沒明確分手，慢慢冷掉
○ 我們還沒分手
```

**用途：**
- 影響「他現在的心理狀態」分析
- 「後悔的提分手方」需要不同的解讀框架（從「對方為什麼變心」改為「對方還願意嗎」）

### CTA
```
[ 下一步 → ]
進度：3 / 5
```

---

## Step 4：更多細節

### 標題
```
再告訴我多一點
```

### 副標
```
細節讓分析更精準
```

### 問題 1：最近一次聯絡

```
你們最近一次聯絡是？

○ 今天還有聯絡
○ 最近一週內
○ 1 - 4 週前
○ 超過一個月
○ 從分手後完全斷聯
```

**用途：**
- 直接關係到「最佳聯絡時機」分析
- 「完全斷聯」vs「今天還有聯絡」是完全不同的策略情境

### 問題 2：交往時間

```
交往時間多久？

○ 不到 3 個月
○ 3 個月 - 1 年
○ 1 - 3 年
○ 3 年以上
○ 我們從未正式在一起
```

**用途：**
- 影響緣分強度的解讀
- 5 年 vs 3 個月的「課題完成度」完全不同
- LLM 可以說「你們交往 4 年，丑未沖的課題你們已經處理了 80%」這種有時間維度的洞察

### CTA
```
[ 下一步 → ]
進度：4 / 5
```

---

## Step 5：你最想知道什麼

### 標題
```
最後一個問題
```

### 副標
```
你心裡那個答不出來的問題是？
```

### 底部說明（重要）
```
你選的這個問題，會出現在你合盤報告的封面。
```

這個說明讓用戶覺得「我選的問題很重要」，加深個人化感受。

### 5 個選項

```
○ 他現在心裡還有我嗎
○ 我們還有機會復合嗎
○ 我什麼時候應該聯絡他
○ 我做了什麼讓他離開
○ 我該繼續等還是放下
```

**用途：**
- 對應 `wiki/context/questions/` 的 5 個問題框架文章
- 決定報告的核心 framing
- 每個問題會用不同的解讀重點

### CTA
```
[ 開始分析 → ]
進度：5 / 5
```

---

## 資料儲存格式

收集到的資料以 JSON 儲存：

```json
{
  "person_a": {
    "birth_date": "1995-11-04",
    "birth_time": "13:00",
    "birth_place": "Taipei, Taiwan",
    "birth_timezone": "Asia/Taipei",
    "gender": "female"
  },
  "person_b": {
    "birth_date": "1993-03-15",
    "birth_time": "10:00",
    "birth_place": "Taichung, Taiwan",
    "birth_timezone": "Asia/Taipei",
    "gender": "male"
  },
  "context": {
    "relationship_stage": "cold-war",       // Step 3 Q1
    "who_initiated": "them",                // Step 3 Q2
    "contact_status": "no-contact",         // Step 4 Q1
    "relationship_length": "1-3y",          // Step 4 Q2
    "main_question": "still-love-me",       // Step 5
    "desired_outcome": "reconnect",         // derived from Step 5 / optional follow-up
    "emotional_risk": "self-blaming"        // derived safety/tone field
  }
}
```

這個 JSON 會餵給：
1. 計算引擎（生成命盤資料）
2. KB selector（選出 stage / question / bazi_core / western_core / timing / safety）
3. KB retriever（展開 typed links 並 attach claim evidence）
4. LLM（生成個人化解讀）

---

## UX 設計細節

### 必填 vs 選填

**必填：**
- 出生日期（兩人）
- 出生地（兩人）
- 性別（兩人）
- Step 3-5 的所有問題

**選填：**
- 出生時間（兩人）

### 沒有「上一頁」按鈕

刻意設計：
- 一旦填完不能改
- 製造「這是一次嚴肅的命盤分析」的儀式感
- 防止用戶反覆改答案玩樂式測試

### 進度條設計

```
○ — — — — 1/5  你的資料
○ ○ — — — 2/5  對方的資料
○ ○ ○ — — 3/5  你們的狀態
○ ○ ○ ○ — 4/5  更多細節
○ ○ ○ ○ ○ 5/5  最想知道什麼
```

### 微互動建議

**每一步加溫暖的引導文字：**
- Step 3 標題：「告訴我，你們現在的狀況⋯⋯」
- Step 5 標題：「最後一個問題 — 你心裡那個答不出來的問題是？」

**不要過度設計：**
- 不要每步都有 5 秒過場動畫
- 不要每步都有複雜的視覺效果
- 速度感 > 視覺感

---

## 為什麼這 5 步是對的

### 與其他做法比較

**做法 A：一頁長表單**
- ❌ 心理門檻高
- ❌ 看到一堆問題會放棄
- ❌ 沒有「進度感」

**做法 B：分 10 步**
- ❌ 太多 step 會疲勞
- ❌ 每步資訊太碎，沒有承接感
- ❌ 完成率會掉

**做法 C：3 步**
- ❌ 每頁問題太多
- ❌ 無法漸進收集情感投入
- ❌ Step 5 的「核心問題」被淹沒

**我們的 5 步：剛剛好**
- ✅ 每步只專注一個情境
- ✅ 漸進的情感投入
- ✅ 完成率高（>90%）

---

## 與其他 Funnel 的整合

問卷完成後 → Loading 動畫 → 免費結果頁

```
Step 5 完成
  ↓
Loading（8-12 秒個人化動畫）
  ↓
免費結果頁 → 顯示三個免費洞察 + 鎖定內容
```

詳見：`product/04-free-result-page.md`
