# Paid V1 Native Chinese Copy Contract

## Purpose

Paid V1 is already source-backed and runtime-wired. This contract protects the visible result page from sounding like translated method notes. The user should feel the reading is specific to her chart, context, and question, while still staying bounded by Western astrology evidence.

## Result Sections

The five paid V1 sections stay unchanged:

1. 星盤定位
2. 兩個人的關係契合度分析
3. 核心問題解讀
4. 時機判讀
5. 行動方向

## Writing Standard

Use everyday Traditional Chinese that sounds natural to a Taiwanese relationship-reading user.

Preferred:

- `短、輕、沒有要求的訊息`
- `看對方有沒有自然接住`
- `先停，不要補第二則`
- `不指定哪一天，只看哪種時段比較能承受互動`
- `這只能說明有反應，不能替對方下內心結論`

Avoid:

- `低壓試探`
- `低刺激測試`
- `timing reducer`
- `selector`
- `精準日期`
- `日期精度`
- `行動窗口`
- `Moon/Venus 語言`
- `Asc/Desc overlay`

## Guardrails

The result page must not promise exact dates:

- Do not say a specific day will succeed.
- Do not frame a date as the only chance.
- Do not say the user should contact on a guaranteed day.
- Use `不指定哪一天` and `比較適合互動的時段` instead.

The result page must not claim to know the partner's mind:

- Do not say `他一定還愛你`.
- Do not say `他一定不愛你`.
- Do not say `他心裡一定...`.
- Use observable wording: `穩定回應`, `自然接住`, `防衛變強`, `互動變緊`.

The result page must not leak internal system language:

- No reducer, selector, action IDs, timing band IDs, source IDs, or method IDs.
- No free, locked, upsell, or paid-version language.
- No BaZi payload or BaZi copy.
- No visible page-scoping instructions such as `這裡只看`, `這裡只處理`, `這頁先看`, `本頁`, `這一頁`, `時機頁`, or `先不把其他問題一次放進來`. Those are internal section/topic constraints, not interpretation.
- No sequencing narration such as `下一頁再看`, `往下讀`, `讀後面的頁面`, `前面的判斷`, or `後面的結果`. Navigation belongs to buttons and tabs, not the reading copy.
- State the relationship insight directly. Use `安全感需求、表達方式和壓力反應，構成你們各自的關係底色` instead of `這裡只看兩個人的需要、表達方式和壓力反應`.
- Replace page explanations with actual value. Use `現在要決定的是適合靠近、觀察，還是先停` instead of `這裡只看現在適合靠近、觀察，還是先停`.
- Result section titles must never start with `這頁先看`. Titles should name the user-facing topic directly, such as `先回答：他會不會自然回到互動` or `時機看：現在能不能輕輕靠近`.

This rule is enforced by `scripts/readable_interpretation/copy_contract.py`. Any future composer change that restores interface narration must fail the native-copy, reading-quality, and Phase 5 calibration gates.

## Runtime Proof

Every future copy change should pass:

```bash
.venv/bin/python scripts/smoke_western_native_copy_contract.py
.venv/bin/python scripts/smoke_western_complete_result_flow.py
.venv/bin/python scripts/verify_paid_v1_reading_stack.py --include-web
```

If the page feels generic, deepen the source-backed atom/rule/reducer first, then rewrite the visible copy. Do not solve weak output by adding static dummy sentences.
