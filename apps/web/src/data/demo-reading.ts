export type SignalLevel = "低" | "中" | "中高" | "高" | "有條件";

export type Metric = {
  key: "attraction" | "pressure" | "chance" | "action";
  label: string;
  value: SignalLevel | string;
  helper: string;
};

export type Insight = {
  label: string;
  title: string;
  body: string;
  source: string;
};

export type ReasonCard = {
  label: string;
  body: string;
  value: number;
};

export type TimelineStep = {
  range: string;
  title: string;
  body: string;
};

export const demoReading = {
  brand: {
    title: "光之谷",
    subtitle: "Valley of Light"
  },
  reading: {
    badge: "完整合盤解讀",
    question: "他現在心裡還有我嗎？",
    stage: "冷戰 / 斷聯中",
    answer:
      "有牽動，但不是輕鬆靠近的狀態。你們之間還有反應，也有壓力；現在最重要的不是急著確認答案，而是看清楚這段關係卡在哪裡。",
    score: 78,
    safety: "需要慢一點，不適合衝動聯絡"
  },
  metrics: [
    {
      key: "attraction",
      label: "情感牽動",
      value: "高",
      helper: "仍有反應"
    },
    {
      key: "pressure",
      label: "關係壓力",
      value: "中高",
      helper: "容易防衛"
    },
    {
      key: "chance",
      label: "復合可能",
      value: "有條件",
      helper: "先降壓"
    },
    {
      key: "action",
      label: "最佳行動",
      value: "先穩住",
      helper: "再觀察"
    }
  ] satisfies Metric[],
  insights: [
    {
      label: "星盤定位",
      title: "情緒安全與防衛節奏都被牽動",
      body: "月亮與土星訊號顯示，這段關係不是單純斷掉，而是安全感、壓力與防衛反應同時被拉起來。",
      source: "western-relationship-profiles"
    },
    {
      label: "西洋核心訊號",
      title: "Sun-Mars 強互動",
      body: "你們之間有明顯行動力與吸引力，但互動速度太快時，也容易把彼此推入壓力反應。",
      source: "western-aspects-sun-mars"
    },
    {
      label: "關係階段",
      title: "冷戰不是結束，而是情緒防衛",
      body: "目前重點不是證明誰還愛誰，而是避免把對方逼到只能繼續退開的位置。",
      source: "context-stage-cold-war"
    },
    {
      label: "安全提醒",
      title: "不要用追問換聯絡",
      body: "你越想立刻要答案，越容易讓這段關係進入更高壓的循環。",
      source: "safety-from-stage-risk"
    }
  ] satisfies Insight[],
  thoughts: [
    "他不是完全沒感覺，而是在避免再進入高壓互動。",
    "目前比較像觀望與防衛，不代表完全放下。",
    "如果你現在太急著確認，反而容易讓他後退。"
  ],
  reasons: [
    {
      label: "吸引模式",
      body: "吸引仍在，但互動模式容易讓彼此壓力升高。",
      value: 78
    },
    {
      label: "防衛模式",
      body: "對方更怕失控或被逼問，而不是完全不在乎。",
      value: 68
    },
    {
      label: "確認焦慮",
      body: "你越想立刻得到答案，越容易把關係推向防衛。",
      value: 72
    }
  ] satisfies ReasonCard[],
  chance: {
    value: 67,
    notes: [
      "有機會，但節奏距離要放慢。",
      "若能降低壓力，仍有重新靠近的空間。",
      "這段時間適合把焦點放在觀察回應，而不是追問答案。"
    ]
  },
  timeline: [
    {
      range: "Day 1-2",
      title: "不主動追問",
      body: "先讓情緒降下來，不用新的訊息刺激對方防衛。"
    },
    {
      range: "Day 3-5",
      title: "觀察輕一點的回應",
      body: "看對方是否有自然互動，不主動丟問題測對方反應。"
    },
    {
      range: "Day 6-7",
      title: "一句輕量訊息",
      body: "若情緒穩定，再用一句不要求答案的訊息測試。"
    }
  ] satisfies TimelineStep[],
  donts: ["不要連續傳訊息", "不要用長文道歉", "不要問「你到底還愛不愛我」"],
  evidence: {
    western: {
      title: "西洋合盤",
      signal: "Sun-Mars 強互動",
      chips: ["Sun-Mars", "Saturn pressure", "attraction-pressure", "balance-pressure"],
      aspects: [
        { label: "Sun-Mars", value: "強互動" },
        { label: "Moon-Saturn", value: "中高壓力" },
        { label: "Venus-Saturn", value: "慢熱防衛" }
      ]
    }
  },
  includedReadingRows: [
    "星盤定位",
    "兩個人的關係契合度分析",
    "核心問題解讀",
    "時機判讀",
    "行動方向"
  ],
  sources: ["Horoscope Symbols", "Skymates", "Synastry", "The Astrology of Relationships"],
  debug: {
    stageSlot: "context-stage-cold-war",
    questionSlot: "context-question-still-love-me",
    westernSlot: "western-aspects-sun-mars"
  }
};

export type DemoReading = typeof demoReading;
