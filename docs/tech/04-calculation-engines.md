# 04 - Calculation Engines
## 命盤計算引擎設計

> 已驗證 working：sxtwl (八字) + immanuel-python (西洋占星) 在環境內測試成功。

---

## 三個計算層

```
Layer 1：個人命盤計算
  - 八字四柱（sxtwl）
  - 西洋本命盤（immanuel）

Layer 2：合盤計算
  - 八字合婚（自寫邏輯）
  - 西洋 Synastry（immanuel）
  - 中西交叉訊號偵測（自寫邏輯）

Layer 3：流動計算
  - 八字流年/流月/流日
  - 西洋 Transits
```

---

## Layer 1.1：八字四柱計算（sxtwl）

### 輸入

```python
{
  "birth_date": "1995-11-04",
  "birth_time": "13:00",  # optional
  "timezone": "Asia/Taipei",  # default
  "gender": "female"
}
```

### 輸出

```python
{
  "bazi": {
    "year_pillar":  {"gan": "乙", "zhi": "亥", "ganzhi": "乙亥"},
    "month_pillar": {"gan": "丙", "zhi": "戌", "ganzhi": "丙戌"},
    "day_pillar":   {"gan": "丁", "zhi": "丑", "ganzhi": "丁丑"},
    "hour_pillar":  {"gan": "丁", "zhi": "未", "ganzhi": "丁未"}
    # 沒有出生時間時，hour_pillar 為 null
  },
  
  "day_master": "丁",  # 日主（丁火）
  "day_master_element": "火",
  "day_master_yin_yang": "陰",
  
  "wuxing_distribution": {
    "木": 2,  # 乙、乙
    "火": 3,  # 丙、丁、丁
    "土": 2,  # 戌、丑、未
    "金": 0,
    "水": 1   # 亥
  },
  
  "shishen": {
    "year_gan_shishen":  "偏印",  # 乙對丁為偏印
    "month_gan_shishen": "劫財",  # 丙對丁為劫財
    "hour_gan_shishen":  "比肩",  # 丁對丁為比肩
    # ...
  },
  
  "marriage_palace": {
    "branch": "丑",  # 日支
    "hidden_stems": ["己", "癸", "辛"]  # 丑藏干
  },
  
  "spouse_star": {
    "type": "正官",  # 女命看正官
    "found_in": ["year_pillar"],  # 在哪幾個柱出現
    "strength": "weak"  # 喜忌判斷
  }
}
```

### 實作細節

```python
# calculation/bazi/core.py

import sxtwl

def calculate_bazi(birth_date: date, birth_time: time | None, gender: str) -> BaziChart:
    """
    計算八字四柱
    """
    lunar = sxtwl.fromSolar(birth_date.year, birth_date.month, birth_date.day)
    
    # 年柱（從立春開始算）
    year_gan_zhi = lunar.getYearGZ()
    
    # 月柱（節氣劃分）
    month_gan_zhi = lunar.getMonthGZ()
    
    # 日柱
    day_gan_zhi = lunar.getDayGZ()
    
    # 時柱（需要出生時間）
    if birth_time:
        hour_index = get_hour_index(birth_time)  # 子時、丑時...
        hour_gan_zhi = lunar.getHourGZ(hour_index)
    else:
        hour_gan_zhi = None
    
    # 組合結果
    return BaziChart(...)
```

### 已知問題

1. **節氣邊界**：立春前後的「年」歸屬要小心。sxtwl 已處理。
2. **冬至 / 立春爭議**：採用立春系統（多數派）
3. **時辰邊界**：23:00-00:59 是子時，但「早子時 vs 晚子時」有派別差異
   - 我們採用「早子時算今日」（多數派）

### V1 日主強弱權重

Current implementation:
- location: `calculation/bazi/signals.py`
- output: `bazi.analysis.day_master_strength_profiles`
- method: `v1_weighted_month_branch_visible_hidden`

The profile weighs:
- month branch main qi
- visible stems
- branch main elements
- hidden stems

It groups those weights into relationship-useful roles:
- `self` / 比劫
- `resource` / 印星
- `output` / 食傷
- `wealth` / 財星
- `officer` / 官殺

It then emits:
- `support_score`
- `pressure_score`
- `strength_score`
- `strength_label`
- `balance_elements`
- `technical_summary`
- `relationship_meaning`

Boundary:
This is a production-useful V1 heuristic for relationship pressure and repair
framing. It is **not** yet a complete 格局成敗 or formal 用神取法.

### V1 流年 / 流月關係觸發

Current implementation:
- locations:
  - `calculation/bazi/sxtwl_adapter.py`
  - `calculation/bazi/signals.py`
  - `scripts/calc_spike.py`
- input: `analysis_date` from the reading context or runtime API
- output: `bazi.analysis.timing_profile`
- method: `bazi_current_year_month_v1`

The profile calculates the current `year`, `month`, and `day` Ganzhi from
`analysis_date`, but the free result currently uses only the year/month trend
language. The profile checks:
- whether the flow stem/branch activates the user's spouse-role energy
  (`官殺` for female charts, `財星` for male charts, both when gender is unknown)
- whether the flow branch combines, clashes, or harms each person's day branch
  relationship palace
- whether the flow element touches the V1 day-master balance elements

It then emits:
- `target_date`
- `transits`
- `period_profiles`
- `relationship_triggers`
- `strongest_trigger`
- `window_label`
- `technical_summary`
- `relationship_meaning`
- `limits`

Boundary:
This is a medium-confidence timing signal for relationship trend framing. It is
**not** a complete 大運 / 流日 / 起運歲數 / formal 喜忌 timing method.

### V1 大運 / 起運 / 流日關係觸發

Current implementation:
- locations:
  - `calculation/bazi/lunar_verifier.py`
  - `calculation/bazi/signals.py`
  - `scripts/calc_spike.py`
- input: birth date/time, gender, and `analysis_date`
- output: `bazi.analysis.luck_timing_profile`
- method: `bazi_da_yun_liu_ri_v1`

The profile uses `lunar_python.getYun()` to calculate:
- 起運 direction
- 起運 year / month / day / hour
- 起運 solar date
- current 大運
- current 流年 inside the active 大運

It also uses the analysis-date 流日 from the `sxtwl` transit payload.

The profile checks:
- whether current 大運 / 流日 activates spouse-role energy
  (`官殺` for female charts, `財星` for male charts, both when gender is unknown)
- whether current 大運 / 流日 branches combine, clash, or harm each person's day branch
  relationship palace
- whether current 大運 / 流日 elements touch the V1 day-master balance elements

It then emits:
- `target_date`
- `cycle_summaries`
- `period_profiles`
- `relationship_triggers`
- `strongest_trigger`
- `window_label`
- `technical_summary`
- `relationship_meaning`
- `limits`

Boundary:
This gives the timing layer a real long-cycle background plus short-term 流日
weather. It is **not** complete 格局成敗, formal 喜忌, 神煞-level timing, or a
擇日-grade contact-window search.

---

## Layer 1.2：西洋本命盤計算（immanuel）

### 輸入

```python
{
  "birth_date": "1995-11-04",
  "birth_time": "13:00",
  "timezone": "Asia/Taipei",
  "latitude": 22.9908,  # 台南
  "longitude": 120.2133
}
```

### 輸出（簡化版）

```python
{
  "natal_chart": {
    "sun": {
      "sign": "scorpio",
      "degree": 11.5,
      "house": 9
    },
    "moon": {
      "sign": "aries",
      "degree": 23.2,
      "house": 2
    },
    "mercury": {...},
    "venus": {...},
    "mars": {...},
    "jupiter": {...},
    "saturn": {...},
    "uranus": {...},
    "neptune": {...},
    "pluto": {...},
    
    "ascendant": {
      "sign": "aquarius",
      "degree": 5.8
    },
    "midheaven": {
      "sign": "scorpio",
      "degree": 27.3
    },
    
    "north_node": {...},
    "chiron": {...}
  },
  
  "aspects": [
    {
      "planet1": "sun",
      "planet2": "moon",
      "aspect_type": "opposition",
      "orb": 1.2,
      "applying": true
    },
    # ... 其他相位
  ],
  
  "houses": {
    "1": {"sign": "aquarius", "ruler": "saturn"},
    "2": {"sign": "aries", "ruler": "mars"},
    # ...
  }
}
```

### 實作細節

```python
# calculation/western/core.py

from immanuel import charts

def calculate_natal_chart(
    birth_date: date,
    birth_time: time,
    latitude: float,
    longitude: float,
    timezone: str
) -> NatalChart:
    """
    使用 immanuel-python 計算本命盤
    底層用 Swiss Ephemeris (NASA JPL DE441)
    """
    subject = charts.Subject(
        date_time=datetime.combine(birth_date, birth_time),
        latitude=latitude,
        longitude=longitude
    )
    
    natal = charts.Natal(subject)
    
    return NatalChart(
        planets=natal.planets,
        houses=natal.houses,
        aspects=natal.aspects,
        ...
    )
```

### House system 選擇

```python
# 採用 Placidus 系統（最常見的西洋占星）
# immanuel 預設就是 Placidus

# 如果用戶沒有出生時間，無法計算 houses 與 ascendant
# 此時只回傳行星位置（仍然有意義）
```

### Orb（容許度）設定

```python
ORBS = {
    "conjunction": 8,
    "opposition": 8,
    "trine": 6,
    "square": 6,
    "sextile": 4,
    "quincunx": 3,
    "semisextile": 2,
}
```

---

## Layer 2.1：八字合婚計算

### 輸入

兩個人的 BaziChart（從 Layer 1.1 產出）

### 輸出

```python
{
  "rigan_relationship": {
    # 日干關係
    "type": "wood_generates_fire",  # 乙木生丁火
    "person_a_to_b": "supports",
    "person_b_to_a": "is_supported",
    "description": "乙木生丁火，他天然滋養你的情感"
  },
  
  "rizhi_relationship": {
    # 日支關係
    "type": "chong",  # 丑未沖
    "branches": ["丑", "未"],
    "severity": "high",
    "description": "婚姻宮相沖，本質性的對立"
  },
  
  "tiangan_interactions": [
    # 四柱天干間的合化
    {
      "from": "person_a.month_gan",  # 丙
      "to": "person_b.hour_gan",     # 辛
      "type": "he",  # 丙辛合
      "result": "水"  # 化水
    }
  ],
  
  "dizhi_interactions": [
    # 四柱地支間的沖合刑害
    {
      "from": "person_a.day_zhi",  # 丑
      "to": "person_b.day_zhi",    # 未
      "type": "chong"
    }
  ],
  
  "wuxing_complementarity": {
    "combined_distribution": {
      "木": 4, "火": 5, "土": 3, "金": 1, "水": 3
    },
    "person_a_needs": ["金"],
    "person_b_provides": [],
    "missing_elements": ["金"]  # 兩人合起來仍缺金
  },
  
  "spouse_star_match": {
    # 女命看對方是否符合「正官」期待
    "person_a_spouse_star": "正官 = 壬水",
    "person_b_provides": false,  # 對方沒有壬水
    "alternative": "癸水（正官的偏星）"
  }
}
```

### 實作細節（核心邏輯）

```python
# calculation/bazi/compatibility.py

WUXING_GENERATION = {
    # 五行相生
    ("木", "火"): "wood_generates_fire",
    ("火", "土"): "fire_generates_earth",
    ("土", "金"): "earth_generates_metal",
    ("金", "水"): "metal_generates_water",
    ("水", "木"): "water_generates_wood",
}

WUXING_OVERCOMING = {
    # 五行相剋
    ("木", "土"): "wood_overcomes_earth",
    ("土", "水"): "earth_overcomes_water",
    ("水", "火"): "water_overcomes_fire",
    ("火", "金"): "fire_overcomes_metal",
    ("金", "木"): "metal_overcomes_wood",
}

DIZHI_LIUCHONG = [
    ("子", "午"), ("丑", "未"), ("寅", "申"),
    ("卯", "酉"), ("辰", "戌"), ("巳", "亥")
]

DIZHI_LIUHE = [
    ("子", "丑"), ("寅", "亥"), ("卯", "戌"),
    ("辰", "酉"), ("巳", "申"), ("午", "未")
]

DIZHI_XING = {
    # 地支相刑
    "无恩之刑": [("寅", "巳", "申")],
    "无礼之刑": [("子", "卯")],
    "恃势之刑": [("丑", "未", "戌")],
    "自刑": [("辰", "辰"), ("午", "午"), ("酉", "酉"), ("亥", "亥")]
}

def analyze_compatibility(chart_a: BaziChart, chart_b: BaziChart) -> Compatibility:
    """
    完整的八字合婚分析
    """
    result = {}
    
    # 1. 日干關係
    result["rigan"] = analyze_rigan(chart_a.day_master, chart_b.day_master)
    
    # 2. 日支關係
    result["rizhi"] = analyze_rizhi(chart_a.day_zhi, chart_b.day_zhi)
    
    # 3. 四柱天干合化
    result["tiangan"] = find_tiangan_interactions(chart_a, chart_b)
    
    # 4. 四柱地支沖合刑害
    result["dizhi"] = find_dizhi_interactions(chart_a, chart_b)
    
    # 5. 五行互補
    result["wuxing"] = analyze_wuxing(chart_a, chart_b)
    
    # 6. 配偶星檢查
    result["spouse_star"] = check_spouse_star_match(chart_a, chart_b)
    
    return Compatibility(**result)
```

---

## Layer 2.2：西洋合盤計算（Synastry）

### 輸入

兩個 NatalChart

### 輸出

```python
{
  "interaspects": [
    # 所有 inter-chart aspects
    {
      "person_a_planet": "venus",
      "person_b_planet": "mars",
      "aspect": "trine",
      "orb": 1.5,
      "applying": true,
      "weight": "major"  # major | medium | minor
    },
    # ...
  ],
  
  "house_overlays": {
    # A 的行星落在 B 的哪一宮
    "a_in_b": [
      {"planet": "venus", "house": 7},
      {"planet": "mars", "house": 5}
    ],
    "b_in_a": [...]
  },
  
  "key_themes": [
    # 從相位歸納的主題
    "strong_emotional_connection",
    "communication_challenges",
    "karmic_tie"  # Saturn 或 Node 相關
  ]
}
```

### 實作細節

```python
# calculation/western/synastry.py

from immanuel import charts

def calculate_synastry(subject_a: charts.Subject, natal_b: charts.Natal) -> Synastry:
    """
    計算合盤相位。

    Current immanuel exposes synastry through `aspects_to`, not a dedicated
    `charts.Synastry` class.
    """
    synastry = charts.Natal(subject_a, aspects_to=natal_b)
    
    # 萃取核心 inter-aspects
    important_aspects = []
    for active_id, passive_aspects in synastry.aspects.items():
        for passive_id, aspect in passive_aspects.items():
            if not is_relationship_relevant(active_id, passive_id, aspect):
                continue
            important_aspects.append({
                "active_id": active_id,
                "passive_id": passive_id,
                "aspect": aspect.type,
                "orb": aspect.orb,
                "applying": aspect.movement.applicative,
            })
    
    # 房宮疊加
    house_overlays = calculate_house_overlays(natal_a, natal_b)
    
    return Synastry(...)
```

### 重要的合盤相位（給 LLM 用）

關係分析中最重要的相位：

```python
RELATIONSHIP_KEY_ASPECTS = [
    # 情感與愛情
    ("sun", "moon"),
    ("venus", "mars"),
    ("venus", "venus"),
    ("moon", "moon"),
    
    # 心智溝通
    ("mercury", "mercury"),
    ("sun", "mercury"),
    
    # 承諾與穩定
    ("saturn", "moon"),
    ("saturn", "venus"),
    ("saturn", "sun"),
    
    # 業力 / 命運感
    ("north_node", "sun"),
    ("north_node", "moon"),
    ("north_node", "venus"),
    
    # 轉化 / 強度
    ("pluto", "venus"),
    ("pluto", "moon"),
    
    # 突破 / 不穩定
    ("uranus", "venus"),
    ("uranus", "moon"),
]
```

---

## Layer 2.3：中西交叉訊號偵測 ⭐ 獨家

### 邏輯

當八字與西洋同時指向同一個主題，那是「雙重確認」訊息。

### 對應關係（從 KB cross/ 取得）

```python
CROSS_CONFIRMATIONS = {
    # 例 1：本質衝突
    "essential_conflict": {
        "bazi_signals": ["日支相沖", "日干相剋"],
        "western_signals": [
            ("mars", "mars", "opposition"),
            ("saturn", "sun", "square"),
            ("uranus", "venus", "square")
        ],
        "description": "本質性的對立 — 你們的核心價值或行動方式有結構性衝突"
    },
    
    # 例 2：強烈吸引
    "strong_attraction": {
        "bazi_signals": ["日干相生", "桃花相見"],
        "western_signals": [
            ("venus", "mars", "trine"),
            ("venus", "mars", "conjunction"),
            ("sun", "moon", "trine")
        ],
        "description": "強烈的命中吸引力 — 兩個系統都看到深層的相互吸引"
    },
    
    # 例 3：成長型課題
    "karmic_lesson": {
        "bazi_signals": ["日支相刑"],
        "western_signals": [
            ("saturn", "venus", "conjunction"),
            ("north_node", "sun", "conjunction"),
            ("chiron", "venus", "conjunction")
        ],
        "description": "課題型關係 — 你們在一起是為了學習特定的人生功課"
    },
    
    # ...
}

def detect_cross_confirmations(
    compatibility: Compatibility,
    synastry: Synastry
) -> List[CrossConfirmation]:
    """
    偵測雙重確認訊號
    """
    confirmations = []
    
    for theme_name, theme in CROSS_CONFIRMATIONS.items():
        bazi_match = any(
            signal in compatibility.signals 
            for signal in theme["bazi_signals"]
        )
        western_match = any(
            check_western_signal(synastry, signal) 
            for signal in theme["western_signals"]
        )
        
        if bazi_match and western_match:
            confirmations.append({
                "theme": theme_name,
                "description": theme["description"],
                "bazi_evidence": [...],
                "western_evidence": [...]
            })
    
    return confirmations
```

---

## Layer 3：流動計算

### 八字流年 / 流月 / 流日

```python
def calculate_bazi_transits(
    chart: BaziChart,
    target_date: date
) -> BaziTransits:
    """
    計算當下的流年、流月、流日 干支
    """
    lunar = sxtwl.fromSolar(target_date.year, target_date.month, target_date.day)
    
    return BaziTransits(
        liunian=lunar.getYearGZ(),    # 流年
        liuyue=lunar.getMonthGZ(),    # 流月
        liuri=lunar.getDayGZ()        # 流日
    )

def analyze_transit_impact(
    chart: BaziChart,
    transits: BaziTransits
) -> TransitImpact:
    """
    分析流年/流月對本命的影響
    """
    # 流年天干對日主：是喜神還是忌神？
    # 流年地支對日支（婚姻宮）：合？沖？
    # ...
```

### 西洋 Transits

```python
from immanuel import charts

def calculate_western_transits(
    natal_chart: NatalChart,
    target_date: date
) -> WesternTransits:
    """
    計算當下行星對本命盤的相位
    """
    transit_subject = charts.Subject(
        date_time=f"{target_date.isoformat()} 12:00",
        latitude=natal_chart.latitude,
        longitude=natal_chart.longitude,
        timezone=natal_chart.timezone
    )
    
    # immanuel target-date V1: build the analysis-date chart and compare it
    # against the natal chart through aspects_to.
    transit_chart = charts.Natal(transit_subject, aspects_to=natal_chart.raw)
    
    return WesternTransits(
        aspects=transit_chart.aspects,
        ...
    )
```

### V1 西洋行運關係觸發

Current implementation:
- locations:
  - `calculation/western/immanuel_adapter.py`
  - `calculation/western/signals.py`
  - `scripts/calc_spike.py`
- input: `analysis_date` from the reading context or runtime API
- output: `western.analysis.timing_profile`
- method: `western_current_transits_v1`

The installed `immanuel` package exposes `charts.Transits` as a current-moment
chart, not a target-date transit constructor. For deterministic reading output,
V1 builds a target-date noon chart using `charts.Subject(...)` and
`charts.Natal(transit_subject, aspects_to=natal)`. This gives current transit
objects compared to each person's natal chart.

V1 currently checks:
- transit Sun / Moon / Venus / Mars / Saturn
- natal Sun / Moon / Venus / Mars / Saturn
- aspect type, orb, applying flag, and whether a Moon claim is time-sensitive
- relationship timing categories:
  - Saturn pressure
  - Mars activation pressure
  - Venus softening / relationship focus
  - Moon short-term emotional weather

It then emits:
- `target_date`
- `transits`
- `relationship_triggers`
- `strongest_trigger`
- `window_label`
- `technical_summary`
- `relationship_meaning`
- `limits`

Boundary:
This is a directional timing layer for "why now" and short-term climate. It is
**not** a composite, Davison, secondary progression, solar arc, or precise
contact-window search. Unknown birth time disables natal-Moon timing claims for
that person.

---

## 已驗證的計算範例

**範例：陳沅鈺 (2025-11-04 13:00, 台南)**

```
八字四柱：
  年柱：乙巳
  月柱：丙戌
  日柱：丁丑（日主丁火）
  時柱：丁未

西洋星盤：
  Sun: Scorpio 11°51', House 9
  Moon: Aries 23°15', House 2
  Ascendant: Aquarius 5°48'
```

這個結果與多個獨立命盤計算工具（八字命理網、Astro.com）交叉驗證一致。

---

## 計算引擎的測試

```python
# tests/test_calculation.py

def test_bazi_known_birthday():
    """
    用已知正確結果的範例測試
    """
    chart = calculate_bazi(
        birth_date=date(1995, 11, 4),
        birth_time=time(13, 0),
        gender="female"
    )
    
    assert chart.year_pillar.ganzhi == "乙亥"
    assert chart.month_pillar.ganzhi == "丙戌"
    assert chart.day_pillar.ganzhi == "丁丑"
    assert chart.hour_pillar.ganzhi == "丁未"
    assert chart.day_master == "丁"

def test_synastry_calculation():
    """
    測試合盤計算
    """
    natal_a = calculate_natal_chart(...)
    natal_b = calculate_natal_chart(...)
    
    synastry = calculate_synastry(natal_a, natal_b)
    
    assert len(synastry.interaspects) > 0
    assert synastry.house_overlays is not None
```

---

## 與其他文件的關聯

- 技術棧：`tech/01-tech-stack.md`
- 後端架構：`tech/02-backend-architecture.md`
- KB 整合：`tech/05-kb-integration.md`（計算結果如何餵給 KB retrieval）
- LLM Prompt：`tech/06-llm-prompt-strategy.md`（計算結果如何進入 prompt）
