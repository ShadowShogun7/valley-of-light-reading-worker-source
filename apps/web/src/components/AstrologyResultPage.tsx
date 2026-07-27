"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import type {
  CompleteRelationshipResultViewModel,
  ReadableInterpretation,
  WesternNeedPoint
} from "@/data/complete-relationship-result";
import { BrandLogo } from "@/components/BrandLogo";
import { ImmersiveCosmicDashboard } from "@/components/ImmersiveCosmicDashboard";

type ResultViewModel = CompleteRelationshipResultViewModel;
type RelationshipProfilesData = NonNullable<ResultViewModel["relationshipProfiles"]>;
type PersonProfile = RelationshipProfilesData["personA"];
type FunctionCard = PersonProfile["cards"][number];
type FitItem = RelationshipProfilesData["fitSummary"]["natural"][number];
type MetricItem = ResultViewModel["metrics"][number];
type ReasonCardData = ResultViewModel["reasons"][number];
type TimelineStepData = ResultViewModel["timeline"][number];
type RelationshipDynamicsData = NonNullable<ResultViewModel["attractionDynamics"]>;
type RelationshipInsightAspectItemData = RelationshipDynamicsData["items"][number];
type RelationshipArchetypeData = NonNullable<ResultViewModel["relationshipArchetype"]>;
type RelationshipFitLensData = NonNullable<ResultViewModel["relationshipFitLens"]>;
type PartnerNeedsData = NonNullable<ResultViewModel["partnerNeeds"]>;
type FightLandminesData = NonNullable<ResultViewModel["fightLandmines"]>;
type RelationshipTurningWindowsData = NonNullable<ResultViewModel["relationshipTurningWindows"]>;

type BoundaryItem = {
  body: string;
  readableInterpretation?: Partial<ReadableInterpretation>;
};

const RESULT_STEPS = [
  {
    id: "chart-positioning",
    number: "01",
    shortTitle: "定位",
    title: "星盤定位",
    summary:
      "先分開看懂你和他，再把兩個人的星盤放在一起看：關係型態、契合雷達、自然靠近與壓力來源。"
  },
  {
    id: "core-answer",
    number: "02",
    shortTitle: "問題",
    title: "核心問題解讀",
    summary:
      "針對你最想問的那句話，把問題整理成清楚方向，而不是只給你一堆星盤術語。"
  },
  {
    id: "timing-reading",
    number: "03",
    shortTitle: "時機",
    title: "時機節奏",
    summary:
      "判斷現在適合主動聯絡、輕輕靠近、繼續觀察，還是先暫停行動。"
  },
  {
    id: "action-direction",
    number: "04",
    shortTitle: "行動",
    title: "行動方向",
    summary:
      "整理你現在可以做的下一步：要不要聯絡、怎麼靠近、哪些話先不要說。"
  }
] as const;

type ResultStepId = (typeof RESULT_STEPS)[number]["id"];
type FinalReadingSection = Partial<ReadableInterpretation>;
type FinalReadingSectionId = ResultStepId | "relationship-fit";

type ReviewedSummaryCopy = {
  headline: string;
  paragraph: string;
  caution: string;
};

function reviewedSummaryCopy(section?: FinalReadingSection): ReviewedSummaryCopy | null {
  const headline = String(section?.headline ?? "").trim();
  const meaning = String(section?.meaning ?? "").trim();
  const body = String(section?.body ?? "").trim();
  const nextMove = String(section?.nextMove ?? "").trim();
  const caution = String(section?.caution ?? "").trim();

  if (!headline || !meaning || !body || !nextMove || !caution) return null;

  return {
    headline,
    paragraph: `${meaning}${body}${nextMove}`,
    caution
  };
}

const DEFAULT_RESULT_STEP_ID: ResultStepId = "chart-positioning";

const DECISION_JOURNEY_STEPS = [
  "星盤定位與契合",
  "問題答案",
  "時機",
  "行動"
];

const POINT_LABELS: Record<FunctionCard["point"], string> = {
  Moon: "情緒安定",
  Mercury: "說話與修復",
  Venus: "表達喜歡",
  Mars: "靠近與衝突",
  Saturn: "壓力與界線"
};

const POINT_ICONS: Record<FunctionCard["point"], string> = {
  Moon: "moon",
  Mercury: "chat-bubble",
  Venus: "heart",
  Mars: "sparkles",
  Saturn: "hourglass"
};

const FUNCTION_ORDER: FunctionCard["point"][] = ["Moon", "Mercury", "Venus", "Mars", "Saturn"];

const FUNCTION_LENSES: Record<FunctionCard["point"], string> = {
  Moon: "不安時要怎樣才會安心",
  Mercury: "誤會時要怎樣才談得下去",
  Venus: "靠近時怎樣感覺被喜歡",
  Mars: "想推進或生氣時怎麼反應",
  Saturn: "有壓力時怎麼退開或保護自己"
};

const RELATION_LABELS = {
  natural: "自然合拍",
  effort: "需要說清楚",
  friction: "容易誤會"
} as const;

const FIT_BUCKET_META: Record<FitItem["relation"], { description: string; icon: string; questionBridge: string }> = {
  natural: {
    description: "不用太多解釋，就比較容易感覺對方懂你。",
    icon: "heart",
    questionBridge: "這會成為後面判斷「還有沒有靠近空間」的基礎。"
  },
  effort: {
    description: "不是不合，而是需要把需求講明白，才不會各自猜錯。",
    icon: "chat-bubble",
    questionBridge: "這會影響現在適不適合談清楚、怎麼談才不會加壓。"
  },
  friction: {
    description: "壓力一上來，最容易在這裡誤會、退開或把話說硬。",
    icon: "hourglass",
    questionBridge: "這會決定下一步要先降溫，還是可以慢慢靠近。"
  }
};

const BLOCKED_ACTION_COPY: Record<string, { body: string; label: string }> = {
  alternate_account_contact: {
    label: "不要換帳號聯絡",
    body: "對方已經拉開界線時，不要用新的帳號或其他方式繞過去。"
  },
  repeated_messages: {
    label: "不要連續傳訊息",
    body: "連續補充會讓對方感覺被追著要反應，先停在一則訊息內。"
  },
  third_party_pressure: {
    label: "不要請別人傳話",
    body: "透過共同朋友施壓，容易讓關係變得更尷尬、更難自然回應。"
  },
  emotional_confrontation: {
    label: "不要情緒對質",
    body: "情緒很滿時先不要攤牌，否則容易把本來能談的話變硬。"
  },
  long_explanation: {
    label: "不要一次講太長",
    body: "現在適合短句與具體事，不適合一次把委屈、道歉和期待全部丟出去。"
  },
  asking_for_answer_now: {
    label: "不要立刻要答案",
    body: "越急著定生死，越容易讓對方只想退開，而不是留下來理解你。"
  },
  pressure_for_commitment: {
    label: "不要逼承諾",
    body: "承諾需要在互動變穩後才有位置，不能靠追問推出來。"
  },
  checking_social_media: {
    label: "不要反覆查動態",
    body: "動態很容易被焦慮放大，先不要用它替代真實互動。"
  },
  public_confrontation: {
    label: "不要公開對質",
    body: "公開場合會讓雙方更難下台，先把關係議題留在可退場的空間。"
  },
  rapid_escalation: {
    label: "不要突然加速",
    body: "不要把一次回覆直接推成談復合、談承諾或談全部關係。"
  },
  relationship_definition_push: {
    label: "不要急著定義關係",
    body: "先看互動能不能穩住，再談關係名稱，順序不能反過來。"
  },
  turning_reply_into_commitment: {
    label: "不要把回覆當承諾",
    body: "一次回覆只能代表當下能接話，還不能代表對方已準備好回來。"
  },
  using_shared_space_as_pressure: {
    label: "不要用共同空間施壓",
    body: "如果還會見面或共事，先保留禮貌距離，不要把場域變成攤牌現場。"
  },
  forcing_relationship_definition: {
    label: "不要逼關係定位",
    body: "還能說話時先修復互動，不要一開始就把對方推到只能表態。"
  },
  long_pressure_message: {
    label: "不要傳壓迫長文",
    body: "長文容易讓對方只感覺到負擔，先保留一句清楚、容易回的話。"
  },
  testing_loyalty: {
    label: "不要測試對方",
    body: "試探會讓信任更薄，先用清楚表達取代拐彎確認。"
  }
};

const ACTION_MODE_COPY: Record<string, { body: string; responseRule: string; title: string }> = {
  observe_or_single_low_stimulation_test: {
    title: "只適合短、輕地試一次",
    body: "如果真的要開口，先停在一句短、輕、沒有要求的訊息；送出後不要補第二則。",
    responseRule: "看對方有沒有自然接住。沒有回應，就先停；有回應，也先看是否能穩定延續。"
  },
  small_bid_response_led: {
    title: "跟著回應慢慢走",
    body: "對方有接話時再往下走，不要把一次回覆立刻推成表態、復合或承諾。",
    responseRule: "看回覆是否連續、語氣是否放鬆、對方是否願意多停留一點。"
  },
  shared_space_boundary: {
    title: "先保護共同場域",
    body: "如果還會見面、共事或出現在同一個圈子，先維持禮貌自然，不把現場變成攤牌。",
    responseRule: "看日常互動能不能不尷尬地維持住，再決定要不要另找更適合的時間談。"
  }
};

const ZODIAC_SIGNS = ["牡羊", "金牛", "雙子", "巨蟹", "獅子", "處女", "天秤", "天蠍", "射手", "摩羯", "水瓶", "雙魚"];
const CHART_EMBLEM_ASSETS = {
  mine: "/cosmic/my-chart-emblem.webp",
  partner: "/cosmic/partner-chart-emblem.webp"
};
const ZODIAC_ICON_ASSETS: Record<string, string> = {
  Aries: "/cosmic/zodiac/aries.webp",
  Taurus: "/cosmic/zodiac/taurus.webp",
  Gemini: "/cosmic/zodiac/gemini.webp",
  Cancer: "/cosmic/zodiac/cancer.webp",
  Leo: "/cosmic/zodiac/leo.webp",
  Virgo: "/cosmic/zodiac/virgo.webp",
  Libra: "/cosmic/zodiac/libra.webp",
  Scorpio: "/cosmic/zodiac/scorpio.webp",
  Sagittarius: "/cosmic/zodiac/sagittarius.webp",
  Capricorn: "/cosmic/zodiac/capricorn.webp",
  Aquarius: "/cosmic/zodiac/aquarius.webp",
  Pisces: "/cosmic/zodiac/pisces.webp",
  牡羊: "/cosmic/zodiac/aries.webp",
  金牛: "/cosmic/zodiac/taurus.webp",
  雙子: "/cosmic/zodiac/gemini.webp",
  巨蟹: "/cosmic/zodiac/cancer.webp",
  獅子: "/cosmic/zodiac/leo.webp",
  處女: "/cosmic/zodiac/virgo.webp",
  天秤: "/cosmic/zodiac/libra.webp",
  天蠍: "/cosmic/zodiac/scorpio.webp",
  射手: "/cosmic/zodiac/sagittarius.webp",
  摩羯: "/cosmic/zodiac/capricorn.webp",
  水瓶: "/cosmic/zodiac/aquarius.webp",
  雙魚: "/cosmic/zodiac/pisces.webp"
};
const POSITIONING_ROWS: Array<{
  point: FunctionCard["point"];
  icon: string;
  label: string;
  title: string;
}> = [
  { point: "Moon", icon: "moon", label: "月亮", title: "安全感模式" },
  { point: "Mercury", icon: "chat-bubble", label: "水星", title: "溝通方式" },
  { point: "Venus", icon: "heart", label: "金星", title: "好感表達" },
  { point: "Mars", icon: "sparkles", label: "火星", title: "行動節奏" },
  { point: "Saturn", icon: "hourglass", label: "土星", title: "壓力下的反應" }
];

function cleanCopy(value?: string | null) {
  const raw = value ?? "";
  if (/birth_time|noon fallback|date_noon_fallback|time-sensitive/i.test(raw)) {
    return "出生時間不完整時，會避開上升、宮位與其他時間敏感結論；這些只作背景，不拿來下精準判斷。";
  }
  if (/house overlay|not wired|calculation/i.test(raw)) {
    return "目前還沒有合盤宮位覆蓋計算，所以宮位只作背景，不拿來做精準關係結論。";
  }

  return raw
    .replaceAll("免費版", "這份解讀")
    .replaceAll("免費頁", "這份解讀")
    .replaceAll("免費閱讀", "這份解讀")
    .replaceAll("免費結果", "這份解讀")
    .replaceAll("付費報告", "完整解讀")
    .replaceAll("付費層", "完整解讀")
    .replaceAll("完整報告", "完整解讀")
    .replaceAll("完整解鎖", "完整整理")
    .replaceAll("解鎖", "整理")
    .replaceAll("靠近的入口", "靠近的位置")
    .replaceAll("修復入口", "修復位置")
    .replaceAll("協調入口", "協調位置")
    .replaceAll("入口", "位置")
    .replaceAll("低壓", "壓力比較小")
    .replaceAll("低刺激", "短、輕、可退場")
    .replaceAll("低壓靠近入口", "壓力比較小的靠近方式")
    .replaceAll("壓力比較小靠近位置", "壓力比較小的靠近方式")
    .replaceAll("月亮與金星在乎和需要被照顧的方式", "月亮與金星代表的安全感和被重視感")
    .replaceAll("需求語言", "在乎和需要被照顧的方式")
    .replaceAll("安全感語言", "需要安全感的方式")
    .replaceAll("被重視語言", "需要被重視的方式")
    .replaceAll("安全感與被重視的橋接", "安全感和被重視的感覺怎麼接上")
    .replaceAll("安全感與被重視的接得上的地方", "安全感和被重視的感覺怎麼接上")
    .replaceAll("把安全感和被重視的感覺怎麼接上說清楚", "說清楚你們在哪些地方能讓彼此安心、覺得被重視")
    .replaceAll("交叉橋接", "能互相接上的地方")
    .replaceAll("橋接", "接得上的地方")
    .replaceAll("有橋", "有能接上的地方")
    .replaceAll("讓這個橋變得可用", "讓這個連結真的用得上")
    .replaceAll("控速、降刺激", "先放慢、不要再加壓")
    .replaceAll("降速、降刺激", "放慢、不要再加壓")
    .replaceAll("降低刺激", "降低壓力")
    .replaceAll("降刺激", "不要再加壓")
    .replaceAll("控速", "放慢")
    .replaceAll("推進速度與衝突反應重複出現", "一靠近就容易變急或起衝突")
    .replaceAll("推進速度和衝突反應", "靠近時變急或起衝突的反應")
    .replaceAll("推進速度與衝突反應", "靠近時變急或起衝突的反應")
    .replaceAll("責任與長期承接入口", "能把責任放進日常互動的地方")
    .replaceAll("責任與長期承接位置", "能把責任放進日常互動的地方")
    .replaceAll("長期承接位置", "可以穩定負責的地方")
    .replaceAll("壓力層承接", "壓力能不能被處理")
    .replaceAll("現實回應承接", "穩定的現實回應")
    .replaceAll("情緒承接位置", "情緒比較容易被接住的位置")
    .replaceAll("情緒承接", "情緒比較容易被接住")
    .replaceAll("可預期承接", "可預期回應")
    .replaceAll("成熟承接", "成熟回應")
    .replaceAll("被安全承接", "被安全地接住")
    .replaceAll("被承接", "被接住")
    .replaceAll("可承接", "比較接得住")
    .replaceAll("是否能承接", "能不能接住")
    .replaceAll("能否承接", "能不能接住")
    .replaceAll("能承接", "能接住")
    .replaceAll("穩定承接", "穩定接住")
    .replaceAll("需要翻譯", "需要說清楚")
    .replaceAll("先翻譯成", "先說成")
    .replaceAll("修復槓桿", "可以怎麼修")
    .replaceAll("行動尺度", "目前適合做到哪一步")
    .replaceAll("開口門檻", "開口前先看什麼")
    .replaceAll("精準證據", "主要依據")
    .replaceAll("orb 約", "角度差約")
    .replaceAll("Saturn-in-sign", "土星落星座")
    .replaceAll("Saturn timing", "土星時機訊號")
    .replaceAll("Saturn pressure", "土星壓力")
    .replaceAll("降低 certainty", "降低確定語氣")
    .replaceAll("降 certainty", "改用保守語氣")
    .replaceAll("fatal verdict", "命定結論")
    .replaceAll("Hard contact", "緊張相位")
    .replaceAll("hard contact", "緊張相位")
    .replaceAll("Soft contact", "柔和相位")
    .replaceAll("soft contact", "柔和相位")
    .replaceAll("星盤只能支持很小的試水溫", "目前只適合很小、很輕地試一次")
    .replaceAll("不要把某一天當成唯一機會", "不要把所有壓力放在一次行動上")
    .replaceAll("沒有足夠資料時，不應該把星象寫成精準聯絡日。", "資料不夠完整時，先用保守節奏處理。")
    .replaceAll("不應該把星象寫成精準聯絡日", "先用星象抓互動節奏")
    .replaceAll("精準聯絡日", "互動節奏")
    .replaceAll("時機頁不是排一個保證成功的日期，而是", "")
    .replaceAll("時機頁不是排一個保證成功的日期，", "")
    .replaceAll("不承諾哪一天一定發生或一定成功。", "")
    .replaceAll("不承諾哪一天一定發生或一定成功", "")
    .replaceAll("不指定哪一天一定發生。", "")
    .replaceAll("不指定哪一天一定發生", "")
    .replaceAll("不公開指定日期", "用月旬區間")
    .replaceAll("不提供指定日期", "用月旬區間")
    .replaceAll("不給指定日期", "用月旬區間")
    .replaceAll("不作指定日期承諾", "用月旬區間")
    .replaceAll("不作互動節奏承諾", "用月旬區間")
    .replaceAll("指定日保證", "月旬區間")
    .replaceAll("某日成功", "單一時間點")
    .replaceAll("精準成功日期", "月旬區間")
    .replaceAll("事件保證", "互動條件")
    .replaceAll("占星保證", "互動條件")
    .replaceAll("復合保證", "復合依據")
    .replaceAll("保證對方回覆", "代表對方會回覆")
    .replaceAll("保證對方會立刻回應", "代表對方會立刻回應")
    .replaceAll("保證對方會立刻行動", "代表對方會立刻行動")
    .replaceAll("保證對方會承諾", "代表對方會承諾")
    .replaceAll("保證承諾", "代表承諾")
    .replaceAll("不保證對方回覆、復合、承諾或時間點。", "仍要看壓力、回應和後續互動能不能接住。")
    .replaceAll("不保證對方回覆、復合、承諾或時間點", "仍要看壓力、回應和後續互動能不能接住")
    .replaceAll("不保證回覆、承諾、復合或單一時間點", "仍要看回覆、邊界和後續互動")
    .replaceAll("不保證聯絡、復合、承諾或對方內心變化", "仍要看實際聯絡、承諾和對方後續回應")
    .replaceAll("不保證聯絡、復合、承諾或長期結果", "仍要看實際聯絡、承諾和長期互動")
    .replaceAll("不保證某天一定聯絡或復合", "仍要看實際聯絡和後續互動")
    .replaceAll("不能當成指定日保證", "要放回月旬區間看")
    .replaceAll("不是具體人物、互動條件或第三方內心", "不是具體人物或第三方內心")
    .replaceAll("不是互動條件或硬性期限", "要配合現實互動調整")
    .replaceAll("不能給成功日", "用時段看互動節奏")
    .replaceAll("只能說趨勢", "先看互動趨勢")
    .replaceAll("不作承諾", "先保留彈性")
    .replaceAll("不公開", "先用")
    .replaceAll("這裡應", "要")
    .replaceAll("精準日期", "互動節奏")
    .replaceAll("精準日", "互動節奏")
    .replaceAll("不排指定日期", "先看互動節奏")
    .replaceAll("不指定日期", "先看互動節奏")
    .replaceAll("不指定哪一天", "先看互動節奏")
    .replaceAll("互動氣候", "互動節奏")
    .replaceAll("可不回", "對方可以先不回")
    .replaceAll("不保證對方會回來", "不能當成對方會回來的證明")
    .replaceAll("保證對方會回來", "當成對方會回來的證明")
    .replaceAll("不保證會回來", "不能當成會回來的證明")
    .replaceAll("保證會回來", "當成會回來的證明")
    .replaceAll("窗口", "時段")
    .replaceAll("反而讓互動進入防衛", "反而讓氣氛變硬")
    .replaceAll("行動速度就容易變急，互動很快從想處理變成對抗或升溫", "一急著把問題處理好，你們就容易越講越硬，最後變成像在吵誰對誰錯")
    .replaceAll("你們之間有會互相反應的地方，但它更像一個位置，不是直接等於關係答案", "你們確實容易被彼此牽動，但這只能說明還有火花，不能代表關係已經有結果")
    .replaceAll("你們之間有會互相牽動的地方，但它更像一個入口，不是直接等於關係答案", "你們確實容易被彼此牽動，但這只能說明還有火花，不能代表關係已經有結果")
    .replaceAll("你們確實容易被彼此反應", "你們確實容易被彼此牽動")
    .replaceAll("合盤有牽動", "星盤有吸引線索")
    .replaceAll("可以當位置，但訊息要比感覺更輕", "如果真的要開口，也只適合一句短而輕的訊息")
    .replaceAll("可以當入口，但訊息要比感覺更輕", "如果真的要開口，也只適合一句短而輕的訊息")
    .replaceAll("可以當方式，但訊息要比感覺更輕", "如果真的要開口，也只適合一句短而輕的訊息")
    .replaceAll("訊息要比感覺更輕", "訊息要短一點、輕一點")
    .replaceAll("它提醒你還想靠近，但開口方式要小於你的情緒強度", "這份想靠近可以被看見，但開口要比情緒小很多")
    .replaceAll("這份想靠近可以被看見，但開口要比情緒小很多", "你想靠近是可以理解的，但如果要傳訊息，只適合短短一句，不要把情緒全部放進去")
    .replaceAll("開口方式要小於你的情緒強度", "開口要比情緒小很多")
    .replaceAll("開口要比情緒小很多", "不要把情緒全部放進訊息裡")
    .replaceAll("把行動縮小到不需要立刻定義關係的一步", "下一步要小到對方不用立刻表態")
    .replaceAll("火花可以保留，但下一步要輕，不要把吸引變成壓力測試", "有火花可以先放著，下一步只要短、輕，不要急著逼出答案")
    .replaceAll("沉默期先看互動會不會自然出現，不要把一次主動變成壓力測試", "沉默期先看對方會不會自然出現，不要一主動就逼對方給答案")
    .replaceAll("不要把第一次主動用成壓力測試", "第一次主動不要變成逼對方給答案")
    .replaceAll("看互動能不能不升溫，而不是誰先贏回主導權", "看你們能不能越聊越平，而不是誰先把局面扳回來")
    .replaceAll("把火花落到具體、低要求、可延續的小互動", "不要只看有沒有曖昧，要看能不能變成壓力小、能接下去的小互動")
    .replaceAll("聯絡受阻時，先以界線和自我穩定為主", "如果對方已經不讓你聯絡，現在先不要繞路找他，先把自己穩住")
    .replaceAll("用穩定行動校準強烈感受，不靠猜測下結論", "對方有沒有穩定行動，不要只靠猜測下結論")
    .replaceAll("感覺越重，越要尊重界線，用可看見的行動校準判斷", "感覺越重，越要尊重界線，回頭看對方有沒有清楚行動")
    .replaceAll("小而可觀察的互動", "一件小、看得到回應的互動")
    .replaceAll("修復方向", "接下來")
    .replaceAll("小訊號", "小回應")
    .replaceAll("聯絡受阻", "聯絡被擋住")
    .replaceAll("自我穩定", "先把自己穩住")
    .replaceAll("校準", "調整")
    .replaceAll("低要求", "壓力小")
    .replaceAll("壓力測試", "逼答案")
    .replaceAll("現實逼答案關係能不能長久", "在意這段關係能不能經得起現實")
    .replaceAll("現實壓力測試關係能不能長久", "在意這段關係能不能經得起現實")
    .replaceAll("偶爾回覆只代表通道未斷，還不能當成穩定投入", "偶爾回覆只表示還有零星聯絡，不能直接當成關係已經變穩")
    .replaceAll("偶爾回覆還不能直接當成穩定投入", "偶爾回覆不能直接當成關係已經變穩")
    .replaceAll("副動力要用來分辨值得等待和繼續消耗", "另一條線索要幫你分辨這段關係是在變好，還是在繼續消耗你")
    .replaceAll("副動力", "另一條線索")
    .replaceAll("單一星盤線索", "一個線索")
    .replaceAll("把距離直接解讀成不在乎", "一退開就追問他是不是不在乎")
    .replaceAll("責任、承諾和距離感會讓回應變得比較保守，就算有在意也可能先退回安全距離", "一談到關係定位或距離，對方可能會先慢下來；這不一定是不在意，而是現在還接不住太重的話題")
    .replaceAll("承諾和距離感會讓回應變得比較保守", "一談到承諾或距離，回應可能會先慢下來")
    .replaceAll("避免推進速度又把對方推進防衛", "避免越想靠近，氣氛越緊")
    .replaceAll("通道未斷", "還有零星聯絡")
    .replaceAll("穩定投入", "持續行動")
    .replaceAll("行動速度", "靠近的步調")
    .replaceAll("直接等於關係答案", "代表關係已經有結果")
    .replaceAll("關係答案", "關係結果")
    .replaceAll("壓力下的防衛", "壓力下的反應")
    .replaceAll("壓力防衛", "壓力下的反應")
    .replaceAll("防衛模式", "壓力下的反應")
    .replaceAll("防衛反應", "反應變硬")
    .replaceAll("進入防衛", "變得比較緊")
    .replaceAll("變成防衛", "變硬")
    .replaceAll("互相防衛", "彼此變硬")
    .replaceAll("降低防衛", "降低緊張")
    .replaceAll("更防衛", "更想退開")
    .replaceAll("比較不防衛", "比較不緊")
    .replaceAll("防衛", "保護自己")
    .replace(/(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])/g, "");
}

function actionModeAdvice(mode?: string | null) {
  return ACTION_MODE_COPY[mode ?? ""] ?? {
    title: "先把步調放穩",
    body: "現在先用短、輕、可退場的方式處理，不要把所有答案一次推到對方面前。",
    responseRule: "看對方是否能自然回應，再決定下一步要靠近、等待，還是先停下。"
  };
}

function removeActionMeta(value?: string | null) {
  return cleanCopy(value)
    .replace(/下一步[^。！？]*[。！？]/g, "")
    .replace(/同時因為合盤重複主題是「[^」]+」，行動建議要先服務這個模式，而不是只看你想不想聯絡。/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function AstrologyResultPage({ data }: { data: ResultViewModel }) {
  const profiles = data.relationshipProfiles;
  const personA = profiles?.personA;
  const personB = profiles?.personB;
  const [activeStepId, setActiveStepId] = useState<ResultStepId>(DEFAULT_RESULT_STEP_ID);
  const activeStep = RESULT_STEPS.find((step) => step.id === activeStepId) ?? RESULT_STEPS[0];

  useEffect(() => {
    window.history.scrollRestoration = "manual";
    const returnToChartTop = () => {
      window.requestAnimationFrame(() => {
        scrollWindowToTopInstantly();
      });
      [40, 120, 280, 560, 900].forEach((delay) => {
        window.setTimeout(() => {
          scrollWindowToTopInstantly();
        }, delay);
      });
    };
    const syncStepFromLocation = () => {
      const nextStepId = resultStepIdFromHash(window.location.hash);
      if (nextStepId) {
        setActiveStepId(nextStepId);
        returnToChartTop();
      }
    };

    syncStepFromLocation();
    window.addEventListener("hashchange", syncStepFromLocation);
    window.addEventListener("popstate", syncStepFromLocation);
    return () => {
      window.removeEventListener("hashchange", syncStepFromLocation);
      window.removeEventListener("popstate", syncStepFromLocation);
    };
  }, []);

  if (!profiles || !personA || !personB) {
    return (
      <main className="cosmic-result-shell reading-report-shell">
        <section className="cosmic-result-frame reading-report-app" aria-label="關係星盤解讀">
          <ReadingSidebar activeStepId={DEFAULT_RESULT_STEP_ID} brand={data.brand} onSelect={() => undefined} />
          <div className="reading-app">
            <section className="cosmic-empty-state">
              <CosmicChartWheel variant="small" />
              <p>目前還沒有足夠的星盤定位資料可以展示，請回到填寫流程重新生成。</p>
            </section>
          </div>
        </section>
      </main>
    );
  }

  const questionSections = data.readableQuestionAnswer?.sections;
  const donts: BoundaryItem[] = questionSections?.donts ?? data.donts.map((body) => ({ body }));
  const finalInterpretation = data.finalInterpretation ?? questionSections?.finalInterpretation;
  const finalReadingSections: Partial<Record<FinalReadingSectionId, FinalReadingSection>> = finalInterpretation?.sections ?? {};

  const openStep = (stepId: ResultStepId) => {
    setActiveStepId(stepId);
    if (typeof window === "undefined") return;
    const nextUrl = `${window.location.pathname}${window.location.search}#${stepId}`;
    if (`${window.location.pathname}${window.location.search}${window.location.hash}` !== nextUrl) {
      window.history.pushState({ activeResultStep: stepId }, "", nextUrl);
    }
    window.requestAnimationFrame(() => {
      scrollWindowToTopInstantly();
    });
    [40, 120, 280].forEach((delay) => {
      window.setTimeout(() => {
        scrollWindowToTopInstantly();
      }, delay);
    });
  };

  const stepSections: Record<ResultStepId, ReactNode> = {
    "chart-positioning": (
      <ResultStepSection
        id="chart-positioning"
        number="01"
        title="星盤定位"
        summary="把你和對方先看成兩份關係使用說明：你需要什麼安全感、對方壓力下怎麼保護自己，以及哪些地方不要因出生時間不足而過度解讀。"
        finalReading={finalReadingSections["chart-positioning"]}
        nextStepId="core-answer"
        onNext={openStep}
      >
        <ChartPositioningDossier
          personA={personA}
          personB={personB}
          personANeeds={data.westernRelationshipCaseFile?.identityLayer.personA.needs}
          personBNeeds={data.westernRelationshipCaseFile?.identityLayer.personB.needs}
          profiles={profiles}
        />
        <PositioningCompatibilitySnapshot
          archetype={data.relationshipArchetype}
          attractionDynamics={data.attractionDynamics}
          conflictDynamics={data.conflictDynamics}
          finalReading={finalReadingSections["relationship-fit"]}
          growthDynamics={data.growthDynamics}
          relationshipFitLens={data.relationshipFitLens}
          profiles={profiles}
        />
      </ResultStepSection>
    ),
    "core-answer": (
      <ResultStepSection
        id="core-answer"
        number="02"
        title="核心問題解讀"
        summary="先回答方向，再把星盤線索和現實互動分開看清楚。"
        finalReading={finalReadingSections["core-answer"]}
        nextStepId="timing-reading"
        onNext={openStep}
      >
        <CoreQuestionPanel data={data} finalReading={finalReadingSections["core-answer"]} />
      </ResultStepSection>
    ),
    "timing-reading": (
      <ResultStepSection
        id="timing-reading"
        number="03"
        title="時機節奏"
        summary="現在適合先觀察、輕輕聯絡、暫停一下，還是先不要主動，取決於互動能承受多少壓力。"
        finalReading={finalReadingSections["timing-reading"]}
        nextStepId="action-direction"
        onNext={openStep}
      >
        <TimingPanel
          finalReading={finalReadingSections["timing-reading"]}
          relationshipTurningWindows={data.relationshipTurningWindows}
          timingGuidance={data.timingGuidance ?? data.readableQuestionAnswer?.sections.timing}
        />
      </ResultStepSection>
    ),
    "action-direction": (
      <ResultStepSection
        id="action-direction"
        number="04"
        title="行動方向"
        summary="下一步先看四件事：可以做、先不要、停止線，以及對方回應後怎麼接。"
        finalReading={finalReadingSections["action-direction"]}
      >
        <ActionDirectionPanel
          actionGuidance={data.actionGuidance ?? data.readableQuestionAnswer?.sections.action}
          chance={data.chance}
          donts={donts}
          finalReading={finalReadingSections["action-direction"]}
          fightLandmines={data.fightLandmines}
          timeline={data.timeline}
          reasons={data.reasons}
        />
      </ResultStepSection>
    )
  };

  return (
    <main className="cosmic-result-shell reading-report-shell">
      <section className="cosmic-result-frame reading-report-app" aria-label="完整關係星盤解讀">
        <ReadingSidebar activeStepId={activeStepId} brand={data.brand} onSelect={openStep} />
        <div className="reading-app" id="top">
          <ChartZone activeStepId={activeStepId} data={data} />
          <div className="cosmic-reading-tabs reading-tabs-wrap" id="cosmic-reading-tabs">
            <StepNavigation activeStepId={activeStepId} onSelect={openStep} />
          </div>
          <div className="reading-main">
            <div className="cosmic-tab-stage reading-tab-stage" aria-live="polite" data-active-step={activeStep.id}>
              {stepSections[activeStep.id]}
            </div>
            <div className="reading-footer-line" />
            <footer className="reading-footer">
              <BrandLogo className="reading-footer-logo" decorative variant="wordmark" />
              <span>星盤是一張關係地圖；真正值得信任的方向，會同時出現在感受、行動與你的安定感裡。</span>
            </footer>
          </div>
        </div>
        <div className="reading-page-rail" aria-hidden="true" />
      </section>
    </main>
  );
}

function ReadingSidebar({
  activeStepId,
  brand,
  onSelect
}: {
  activeStepId: ResultStepId;
  brand: ResultViewModel["brand"];
  onSelect: (stepId: ResultStepId) => void;
}) {
  const navIcons: Record<ResultStepId, string> = {
    "chart-positioning": "✦",
    "core-answer": "☾",
    "timing-reading": "⌁",
    "action-direction": "♙"
  };
  const navItems = RESULT_STEPS.map((step) => ({
    icon: navIcons[step.id],
    label: step.id === "core-answer" ? "核心問題" : step.title,
    stepId: step.id
  }));

  return (
    <aside className="reading-sidebar" aria-label={`${brand.title} 結果導覽`}>
      <div className="reading-brand">
        <BrandLogo className="reading-brand-logo" variant="horizontal" />
        <BrandLogo className="reading-brand-logo-mobile" variant="mark" />
      </div>
      <div className="reading-side-rule" />
      <nav className="reading-global-nav" aria-label="結果導覽">
        {navItems.map((item) => {
          const isActive = item.stepId === activeStepId;
          return (
            <a
              className={isActive ? "active" : undefined}
              href={`#${item.stepId}`}
              key={item.stepId}
              onClick={(event) => {
                event.preventDefault();
                onSelect(item.stepId);
              }}
            >
              <span className="reading-nav-icon">{item.icon}</span>
              <span className="reading-nav-label">{item.label}</span>
            </a>
          );
        })}
      </nav>
      <div className="reading-side-bottom">
        <a className="reading-side-button" href="#chart-positioning" onClick={(event) => {
          event.preventDefault();
          onSelect("chart-positioning");
        }}>
          <span>↩</span>
          <span>回到星盤定位</span>
        </a>
        <a className="reading-side-button" href="#cosmic-reading-tabs">
          <span>⚙</span>
          <span>閱讀設定</span>
        </a>
        <div className="reading-profile">
          <div className="reading-avatar" aria-hidden="true" />
          <div>
            <strong>星語指引者</strong>
            <small>本次解讀已保存</small>
          </div>
        </div>
      </div>
    </aside>
  );
}

function ChartZone({ activeStepId, data }: { activeStepId: ResultStepId; data: ResultViewModel }) {
  return (
    <header className="reading-chart-zone">
      <div className="reading-chart-meta">
        <div className="reading-eyebrow">雙人互動星盤</div>
        <h2>關係軌跡</h2>
        <p>以西洋占星觀察情緒牽動、互動壓力與靠近節奏</p>
      </div>
      <div className="reading-chart-actions">
        <button className="reading-ghost-btn" type="button">☆ 保存解讀</button>
        <button className="reading-ghost-btn" type="button">⇩ 下載報告</button>
        <a className="reading-ghost-btn is-circle" href="#cosmic-reading-tabs" aria-label="開啟目錄">•••</a>
      </div>
      <ImmersiveCosmicDashboard activeStepId={activeStepId} data={data} />
    </header>
  );
}

function DecisionSpine({ data }: { data: ResultViewModel }) {
  const answerGuidance = data.answerGuidance ?? data.readableQuestionAnswer?.sections.answer;
  const actionGuidance = data.actionGuidance ?? data.readableQuestionAnswer?.sections.action;
  const timingGuidance = data.timingGuidance ?? data.readableQuestionAnswer?.sections.timing;
  const question = cleanCopy(answerGuidance?.questionLabel ?? data.reading.question);
  const shortAnswer = cleanCopy(answerGuidance?.shortAnswer ?? answerGuidance?.readableInterpretation?.headline ?? data.reading.answer);
  const actionDirection = cleanCopy(
    actionGuidance?.nextMove ??
      actionGuidance?.readableInterpretation?.nextMove ??
      timingGuidance?.recommendedActionLabel ??
      timingGuidance?.nextMove ??
      data.chance.nextMove
  );

  return (
    <section className="cosmic-decision-spine" aria-label="本次閱讀路徑">
      <div className="cosmic-decision-question">
        <span>你問的是</span>
        <strong>{question}</strong>
      </div>
      <div className="cosmic-decision-current">
        <span>目前方向</span>
        <p>{shortAnswer}</p>
        {actionDirection ? <small>{actionDirection}</small> : null}
      </div>
      <div className="cosmic-decision-path" aria-label="閱讀路徑">
        <span>本次閱讀會依序看</span>
        <ol>
          {DECISION_JOURNEY_STEPS.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function StepNavigation({
  activeStepId,
  onSelect
}: {
  activeStepId: ResultStepId;
  onSelect: (stepId: ResultStepId) => void;
}) {
  return (
    <nav className="cosmic-step-nav reading-tabs" aria-label="解讀分頁" role="tablist">
      {RESULT_STEPS.map((step) => (
        <button
          aria-label={`${step.number} ${step.title}`}
          aria-controls={`${step.id}-panel`}
          aria-selected={activeStepId === step.id}
          className={`reading-tab ${activeStepId === step.id ? "active" : ""}`}
          id={`${step.id}-tab`}
          key={step.id}
          onClick={() => onSelect(step.id)}
          role="tab"
          tabIndex={activeStepId === step.id ? 0 : -1}
          type="button"
        >
          <span className="reading-tab-no">{step.number}</span>
          <strong>{step.title}</strong>
        </button>
      ))}
    </nav>
  );
}

function CosmicHero({
  data,
  profiles
}: {
  data: ResultViewModel;
  profiles: RelationshipProfilesData;
}) {
  return (
    <section className="cosmic-hero-panel">
      <div className="cosmic-hero-copy">
        <span className="cosmic-kicker">Relationship Reading</span>
        <h1>完整關係星盤解讀</h1>
        <p>
          這份解讀會先看懂兩個人，再把契合、核心問題、時機與下一步整理成清楚方向。
        </p>
        <div className="cosmic-hero-actions" aria-label="重點導覽">
          <a href="#chart-positioning">開始閱讀</a>
          <a href="#core-answer">直接看答案</a>
        </div>
      </div>

      <div className="cosmic-hero-orbit" aria-label="關係訊號總覽">
        <CosmicTwinLuminaries />
        <div className="cosmic-orbit-card moon-card">
          <img src="/celestial-icons/moon.svg" alt="" aria-hidden="true" />
          <span>你</span>
          <strong>{profiles.personA.cards[0]?.placement ?? "星盤定位"}</strong>
        </div>
        <div className="cosmic-orbit-card sun-card">
          <img src="/celestial-icons/sun-face.svg" alt="" aria-hidden="true" />
          <span>對方</span>
          <strong>{profiles.personB.cards[0]?.placement ?? "星盤定位"}</strong>
        </div>
      </div>
    </section>
  );
}

function ResultStepSection({
  children,
  finalReading,
  id,
  nextStepId,
  number,
  onNext,
  summary,
  title,
  visual
}: {
  children: ReactNode;
  finalReading?: FinalReadingSection;
  id: ResultStepId;
  nextStepId?: ResultStepId;
  number: string;
  onNext?: (stepId: ResultStepId) => void;
  summary: string;
  title: string;
  visual?: "chart";
}) {
  const sectionKicker =
    id === "core-answer" ? "先看答案，再看理由" : id === "action-direction" ? "看下一步怎麼做" : "沿著關係地圖閱讀";
  const sectionSummary = id === "action-direction" || id === "chart-positioning" ? summary : cleanCopy(finalReading?.meaning ?? summary);
  const nextStep = nextStepId ? RESULT_STEPS.find((step) => step.id === nextStepId) : undefined;

  return (
    <section
      aria-labelledby={`${id}-tab`}
      className="cosmic-section"
      data-reading-step={id}
      id={`${id}-panel`}
      role="tabpanel"
      tabIndex={0}
    >
      <div className="cosmic-section-head reading-section-head">
        <div>
          <div className="reading-title-line">
            <span className="reading-sigil">{number}</span>
            <h2 className="reading-section-title">{title}</h2>
          </div>
          <p className="reading-section-sub">{sectionSummary}</p>
        </div>
        <div className="reading-section-kicker">{sectionKicker}</div>
      </div>
      <div className="reading-ornament" aria-hidden="true" />
      {visual === "chart" ? (
        <div className="cosmic-chart-banner" aria-hidden="true">
          <CosmicChartBanner />
        </div>
      ) : null}
      {children}
      {nextStep && onNext ? (
        <footer className="cosmic-tab-bridge">
          <button className="cosmic-tab-bridge-action" onClick={() => onNext(nextStep.id)} type="button">
            前往 {nextStep.number} {nextStep.title} <span aria-hidden="true">→</span>
          </button>
        </footer>
      ) : null}
    </section>
  );
}

function resultStepIdFromHash(hash: string): ResultStepId | null {
  const stepId = hash.replace("#", "");
  return isResultStepId(stepId) ? stepId : null;
}

function isResultStepId(value: string): value is ResultStepId {
  return RESULT_STEPS.some((step) => step.id === value);
}

function scrollWindowToTopInstantly() {
  if (typeof window === "undefined") return;
  const root = document.documentElement;
  const previousScrollBehavior = root.style.scrollBehavior;
  root.style.scrollBehavior = "auto";
  window.scrollTo(0, 0);
  window.setTimeout(() => {
    root.style.scrollBehavior = previousScrollBehavior;
  }, 40);
}

function ChartPositioningDossier({
  personA,
  personANeeds,
  personB,
  personBNeeds,
  profiles
}: {
  personA: PersonProfile;
  personANeeds?: WesternNeedPoint[];
  personB: PersonProfile;
  personBNeeds?: WesternNeedPoint[];
  profiles: RelationshipProfilesData;
}) {
  const notes = [
    ...profiles.precisionWarnings,
    ...personA.precisionWarnings,
    ...personB.precisionWarnings
  ].filter(Boolean);

  return (
    <section className="cosmic-positioning-dossier" aria-label="星盤定位">
      <div className="cosmic-positioning-profile-pair">
        <PositioningProfilePanel profile={personA} owner="mine" />
        <PositioningProfilePanel profile={personB} owner="partner" />
      </div>

      <div className="cosmic-positioning-board" aria-label="五個關係功能比較">
        {POSITIONING_ROWS.map((row) => (
          <PositioningComparisonRow
            key={row.point}
            personACard={findFunctionCard(personA, row.point, personANeeds)}
            personBCard={findFunctionCard(personB, row.point, personBNeeds)}
            row={row}
          />
        ))}
      </div>

      <footer className="cosmic-positioning-footer">
        <span aria-hidden="true">✦</span>
        <p>{notes.length ? cleanCopy(notes[0]) : "星盤先幫你看懂兩個人的關係使用方式，真正的答案仍要回到互動裡慢慢驗證。"}</p>
        <span aria-hidden="true">✦</span>
      </footer>
    </section>
  );
}

function PositioningProfilePanel({
  owner,
  profile
}: {
  owner: "mine" | "partner";
  profile: PersonProfile;
}) {
  const title = owner === "mine" ? "我的星盤" : "他的星盤";

  return (
    <article className={`cosmic-positioning-profile cosmic-positioning-profile-${owner}`}>
      <ChartEmblem label={title} owner={owner} size="portrait" />
      <div>
        <span>{title}</span>
        <h3>{cleanCopy(profile.headline)}</h3>
      </div>
    </article>
  );
}

function PositioningComparisonRow({
  personACard,
  personBCard,
  row
}: {
  personACard?: FunctionCard;
  personBCard?: FunctionCard;
  row: (typeof POSITIONING_ROWS)[number];
}) {
  return (
    <article className="cosmic-positioning-row">
      <div className="cosmic-positioning-function">
        <IconAsset name={row.icon} />
        <div>
          <strong>{row.label}</strong>
          <span>{row.title}</span>
        </div>
      </div>
      <PositioningPersonCell card={personACard} ownerLabel="你" />
      <PositioningPersonCell card={personBCard} ownerLabel="對方" />
    </article>
  );
}

function PositioningPersonCell({
  card,
  ownerLabel
}: {
  card?: FunctionCard;
  ownerLabel: "你" | "對方";
}) {
  if (!card) {
    return (
      <div className="cosmic-positioning-cell is-empty">
        <span>{ownerLabel}</span>
        <strong>資料不足</strong>
        <p>這張功能卡目前沒有足夠資料可判斷。</p>
      </div>
    );
  }

  const meta = positioningMeta(card);

  return (
    <div className="cosmic-positioning-cell">
      <ZodiacIcon card={card} />
      <div>
        <strong>
          {ownerLabel}｜{displaySignLabel(card)}
        </strong>
        <span>{meta.join(" / ")}</span>
        <p>{positioningCardCopy(card)}</p>
      </div>
    </div>
  );
}

function ZodiacIcon({ card }: { card: FunctionCard }) {
  const src = zodiacIconSrc(card);
  return (
    <span className="cosmic-zodiac-token" aria-label={displaySignLabel(card)} role="img">
      <img alt="" src={src} />
    </span>
  );
}

function zodiacIconSrc(card: FunctionCard) {
  const sign = card.sign ? String(card.sign) : "";
  const signLabel = card.signLabel ? String(card.signLabel) : "";
  return ZODIAC_ICON_ASSETS[sign] ?? ZODIAC_ICON_ASSETS[signLabel] ?? "/cosmic/zodiac-glyph-wheel.webp";
}

function displaySignLabel(card: FunctionCard) {
  const label = cleanCopy(card.signLabel || card.placement);
  if (!label) return cleanCopy(card.placement);
  return label.endsWith("座") ? label : `${label}座`;
}

function optionalHouseLabel(card: FunctionCard) {
  const maybe = card as FunctionCard & {
    house?: number | string;
    houseLabel?: string;
    houseNumber?: number;
  };
  if (maybe.houseLabel) return cleanCopy(maybe.houseLabel);
  if (maybe.houseNumber) return `第 ${maybe.houseNumber} 宮`;
  if (typeof maybe.house === "number") return `第 ${maybe.house} 宮`;
  if (typeof maybe.house === "string" && maybe.house.trim()) return cleanCopy(maybe.house);
  return "";
}

function positioningMeta(card: FunctionCard) {
  return [
    optionalHouseLabel(card),
    card.elementLabel,
    card.modalityLabel
  ].filter(Boolean).map((item) => cleanCopy(String(item)));
}

function positioningCardCopy(card: FunctionCard) {
  return cleanCopy(
    card.readableInterpretation?.body ??
      card.naturalResponse ??
      card.style ??
      card.readableInterpretation?.meaning ??
      card.relationshipUse ??
      "這張功能卡目前沒有足夠資料可判斷。"
  );
}

function ProfileConstellationBoard({
  personA,
  personB
}: {
  personA: PersonProfile;
  personB: PersonProfile;
}) {
  return (
    <section className="cosmic-placement-board" aria-label="兩人的星盤功能定位">
      <div className="cosmic-board-title">
        <span>Calculated Placements</span>
        <h3>先看兩份關係使用說明</h3>
        <p>
          先看月亮、水星、金星、火星、土星：你在關係裡需要什麼、對方在壓力下怎麼保護自己，以及你們最容易錯讀彼此的地方。
        </p>
        <div className="cosmic-board-oracle" aria-hidden="true">
          <CosmicChartWheel variant="small" />
        </div>
      </div>
      <div className="cosmic-board-grid">
        {FUNCTION_ORDER.map((point) => {
          const cardA = findFunctionCard(personA, point);
          const cardB = findFunctionCard(personB, point);
          if (!cardA || !cardB) return null;

          return (
            <article className="cosmic-board-row" key={point}>
              <div className="cosmic-board-function">
                <IconAsset name={POINT_ICONS[point]} />
                <div>
                  <span>{POINT_LABELS[point]}</span>
                  <strong>{FUNCTION_LENSES[point]}</strong>
                </div>
              </div>
              <PlacementBadge label="我的星盤" card={cardA} />
              <PlacementBadge label="他的星盤" card={cardB} />
            </article>
          );
        })}
      </div>
    </section>
  );
}

function PlacementBadge({ card, label }: { card: FunctionCard; label: string }) {
  return (
    <div className="cosmic-placement-badge">
      <ChartEmblem label={label} owner={label === "我的星盤" ? "mine" : "partner"} size="badge" />
      <strong>{card.placement}</strong>
      <small>
        {card.elementLabel} · {card.modalityLabel}
      </small>
    </div>
  );
}

function findFunctionCard(profile: PersonProfile, point: FunctionCard["point"], fallbackNeeds?: WesternNeedPoint[]) {
  const profileCard = profile.cards.find((card) => card.point === point);
  if (profileCard) return profileCard;
  const need = fallbackNeeds?.find((item) => item.point === point);
  return need ? fallbackFunctionCard(need, point) : undefined;
}

function fallbackFunctionCard(need: WesternNeedPoint, point: FunctionCard["point"]): FunctionCard {
  const row = POSITIONING_ROWS.find((item) => item.point === point);
  return {
    confidence: need.confidence ?? "low",
    doesNotFit: "這個位置只能先用計算出的星座與基本意義保守理解。",
    key: functionCardKey(point),
    naturalResponse: need.meaning,
    placement: need.label,
    point,
    readableInterpretation: {
      body: need.meaning,
      headline: need.label,
      locale: "zh-TW",
      meaning: need.meaning,
      module: "person_function_sign",
      nextMove: need.precisionNote,
      sourceClaimIds: [],
      stuckPattern: need.precisionNote ?? "這個位置目前先作基本星座理解。",
      version: "readable-interpretation-v1"
    },
    relationshipUse: need.meaning,
    sign: need.sign,
    signLabel: displayNeedSign(need.sign),
    style: need.meaning,
    suitableFor: "先用這個位置理解關係裡的反應方式。",
    title: row?.title ?? POINT_LABELS[point],
    tensionPattern: need.precisionNote ?? "這個位置目前先作基本星座理解。"
  };
}

function functionCardKey(point: FunctionCard["point"]): FunctionCard["key"] {
  const keys: Record<FunctionCard["point"], FunctionCard["key"]> = {
    Mars: "pursuitConflict",
    Mercury: "communicationRepair",
    Moon: "emotionalSafety",
    Saturn: "defenseDelay",
    Venus: "affectionAttraction"
  };
  return keys[point];
}

function displayNeedSign(sign: string) {
  const normalized = cleanCopy(sign).replaceAll("白羊", "牡羊");
  const signLabels: Record<string, string> = {
    Aries: "牡羊",
    Taurus: "金牛",
    Gemini: "雙子",
    Cancer: "巨蟹",
    Leo: "獅子",
    Virgo: "處女",
    Libra: "天秤",
    Scorpio: "天蠍",
    Sagittarius: "射手",
    Capricorn: "摩羯",
    Aquarius: "水瓶",
    Pisces: "雙魚"
  };
  return signLabels[normalized] ?? normalized;
}

function ChartEmblem({
  label,
  owner,
  size
}: {
  label: string;
  owner: "mine" | "partner";
  size: "badge" | "portrait";
}) {
  return (
    <span aria-label={label} className={`cosmic-chart-emblem cosmic-chart-emblem-${size}`} role="img">
      <img alt="" src={CHART_EMBLEM_ASSETS[owner]} />
    </span>
  );
}

function PersonArchiveCard({ profile, tone }: { profile: PersonProfile; tone: "moon" | "sun" }) {
  const moonCard = findFunctionCard(profile, "Moon");
  const mercuryCard = findFunctionCard(profile, "Mercury");
  const saturnCard = findFunctionCard(profile, "Saturn");
  const foundationItems = [
    moonCard ? { label: "不安時需要", card: moonCard, text: moonCard.readableInterpretation?.body ?? moonCard.naturalResponse ?? moonCard.style } : null,
    mercuryCard ? { label: "比較聽得進去的說法", card: mercuryCard, text: mercuryCard.readableInterpretation?.body ?? mercuryCard.naturalResponse ?? mercuryCard.style } : null,
    saturnCard ? { label: "有壓力時會先怎麼保護自己", card: saturnCard, text: saturnCard.readableInterpretation?.body ?? saturnCard.naturalResponse ?? saturnCard.style } : null
  ].filter(Boolean) as { card: FunctionCard; label: string; text: string }[];
  const relationshipNeeds = profile.suitableFor.slice(0, 2);
  const emblemOwner = profile.label === "你" ? "mine" : "partner";
  const chartLabel = profile.label === "你" ? "我的星盤" : "他的星盤";

  return (
    <article className={`cosmic-person-card ${tone}`}>
      <div className="cosmic-person-intro">
        <div className="cosmic-person-portrait">
          <ChartEmblem label={chartLabel} owner={emblemOwner} size="portrait" />
        </div>
        <div className="cosmic-person-title">
          <span>{profile.label === "你" ? "我的檔案" : "他的檔案"}</span>
          <p>{cleanCopy(profile.headline)}</p>
        </div>
      </div>

      <div className="cosmic-placement-row" aria-label={`${profile.label}的重點行星`}>
        {profile.cards.slice(0, 3).map((card) => (
          <div key={`${profile.role}-${card.point}`}>
            <IconAsset name={POINT_ICONS[card.point]} />
            <span>{POINT_LABELS[card.point]}</span>
            <strong>{card.placement}</strong>
          </div>
        ))}
      </div>

      <section className="cosmic-profile-foundation" aria-label={`${profile.label}的關係基礎`}>
        <div className="cosmic-foundation-head">
          <span>先看三件事</span>
          <h4>{profile.label === "你" ? "你的關係底色" : "他的關係底色"}</h4>
        </div>
        <div className="cosmic-foundation-grid">
          {foundationItems.map((item) => (
            <article key={`${profile.role}-${item.card.point}-foundation`}>
              <IconAsset name={POINT_ICONS[item.card.point]} />
              <div>
                <strong>{item.label}</strong>
                <p>{cleanCopy(item.text)}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <div className="cosmic-profile-summary">
        <strong>{profile.label === "你" ? "比較適合你的互動" : "對方比較容易接受的互動"}</strong>
        <div>
          {relationshipNeeds.map((item) => (
            <span key={`${profile.role}-${item}`}>{cleanCopy(item)}</span>
          ))}
        </div>
      </div>

      <div className="cosmic-function-grid">
        {profile.cards.slice(0, 5).map((card) => (
          <FunctionSignalCard card={card} key={`${profile.role}-${card.point}-${card.placement}`} owner={profile.label} />
        ))}
      </div>

      {profile.precisionWarnings.length > 0 ? (
        <div className="cosmic-warning-strip">
          <IconAsset name="info-circle" />
          <span>{cleanCopy(profile.precisionWarnings[0])}</span>
        </div>
      ) : null}
    </article>
  );
}

function FunctionSignalCard({ card, owner }: { card: FunctionCard; owner: PersonProfile["label"] }) {
  const ownerPrefix = owner === "你" ? "你會" : "他會";

  return (
    <article className="cosmic-function-card">
      <div className="cosmic-function-top">
        <IconAsset name={POINT_ICONS[card.point]} />
        <div>
          <span>{card.point}</span>
          <strong>{card.title}</strong>
        </div>
      </div>
      <p className="cosmic-placement">{card.placement}</p>
      <div className="cosmic-function-lens">
        <span>這張卡看什麼</span>
        <strong>{FUNCTION_LENSES[card.point]}</strong>
      </div>
      <p>{cleanCopy(card.readableInterpretation?.meaning ?? card.relationshipUse)}</p>
      <div className="cosmic-function-detail">
        <strong>{ownerPrefix}怎麼反應</strong>
        <span>{cleanCopy(card.readableInterpretation?.body ?? card.naturalResponse ?? card.style)}</span>
      </div>
      <div className="cosmic-function-detail muted">
        <strong>壓力下容易變成</strong>
        <span>{cleanCopy(card.readableInterpretation?.stuckPattern ?? card.tensionPattern ?? card.doesNotFit)}</span>
      </div>
    </article>
  );
}

function PrecisionNotes({ profiles }: { profiles: RelationshipProfilesData }) {
  const notes = [
    ...profiles.precisionWarnings,
    ...profiles.personA.precisionWarnings,
    ...profiles.personB.precisionWarnings
  ].filter(Boolean);

  if (!notes.length) return null;

  return (
    <section className="cosmic-precision-notes" aria-label="出生資料精度提醒">
      <IconAsset name="info-circle" />
      <div>
        <strong>精度提醒</strong>
        <p>{cleanCopy(notes[0])}</p>
      </div>
    </section>
  );
}

function PositioningCompatibilitySnapshot({
  archetype,
  attractionDynamics,
  conflictDynamics,
  finalReading,
  growthDynamics,
  relationshipFitLens,
  profiles
}: {
  archetype?: RelationshipArchetypeData;
  attractionDynamics?: RelationshipDynamicsData;
  conflictDynamics?: RelationshipDynamicsData;
  finalReading?: FinalReadingSection;
  growthDynamics?: RelationshipDynamicsData;
  relationshipFitLens?: RelationshipFitLensData;
  profiles: RelationshipProfilesData;
}) {
  const lens = relationshipFitLens ?? fallbackRelationshipFitLens({ archetype, attractionDynamics, conflictDynamics, growthDynamics, profiles });
  const relationshipType = lens.relationshipType;
  const radar = lens.radar.slice(0, 6);
  const compatibilityScore = relationshipCompatibilityScore(radar);
  const reviewedSummary = reviewedSummaryCopy(finalReading);
  const thesisBody = cleanCopy(finalReading?.body);
  const visibleRelationshipReasons = relationshipType.reasons
    .slice(0, 3)
    .filter((reason) => !reason.startsWith("最常反覆出現：") && !reason.startsWith("星盤重點：") && !reason.includes("靠近時容易變緊"));

  return (
    <div className="compatibility-fit-page compatibility-positioning-snapshot">
      <section className="compatibility-fit-section" aria-labelledby="positioning-compatibility-type-title">
        <div className="compatibility-section-head">
          <div className="compatibility-section-title-lock">
            <div>
              <h3 id="positioning-compatibility-type-title">關係型態</h3>
              <p>先用一句話，說清楚這段關係主要怎麼運作。</p>
            </div>
          </div>
          <div className="compatibility-section-note">RELATIONSHIP ARCHETYPE</div>
        </div>

        <article className="compatibility-fit-panel compatibility-type-card">
          <div className="compatibility-type-main" data-reviewed-summary="relationship-fit">
            <div className="compatibility-micro-label">這段關係的主要型態</div>
            <h3>{reviewedSummary?.headline ?? cleanCopy(relationshipType.title)}</h3>
            <p className="compatibility-type-summary">
              {reviewedSummary?.paragraph ?? (thesisBody || cleanCopy(relationshipType.meaning))}
            </p>
            {reviewedSummary ? <small className="reviewed-summary-caution">{reviewedSummary.caution}</small> : null}
            {visibleRelationshipReasons.length ? (
              <div className="compatibility-reason-chips" aria-label="關係型態選擇原因">
                {visibleRelationshipReasons.map((reason, index) => (
                  <span className="compatibility-reason-chip" key={`${reason}-${index}`}>{cleanCopy(reason)}</span>
                ))}
              </div>
            ) : null}
          </div>
          <aside className="reading-boundary compatibility-score-side" aria-label="星盤契合度">
            <div className="reading-boundary-title">星盤契合度</div>
            <div className="reading-boundary-chip">
              <span className="reading-chip-icon">合</span>
              <span className="compatibility-score-rating">{compatibilityScore.rating}</span>
            </div>
            <div className="reading-boundary-note">依契合雷達六個面向平均計算。</div>
          </aside>
        </article>
      </section>

      <section className="compatibility-fit-section" aria-labelledby="positioning-compatibility-radar-title">
        <div className="compatibility-section-head">
          <div className="compatibility-section-title-lock">
            <div>
              <h3 id="positioning-compatibility-radar-title">契合雷達</h3>
              <p>用六個面向快速看懂這段關係的平衡。</p>
            </div>
          </div>
          <div className="compatibility-section-note">QUICK RELATIONSHIP SNAPSHOT</div>
        </div>

        <div className="compatibility-radar-grid">
          {radar.map((item) => (
            <article className={`compatibility-radar-tile${item.key === "conflictPressure" ? " pressure" : ""}`} key={item.key}>
              <div className="compatibility-tile-icon" aria-hidden="true">
                <CompatibilityRadarIcon name={item.key} />
              </div>
              <span className="compatibility-radar-label">{cleanCopy(item.label)}</span>
              <strong className={`compatibility-radar-rating${item.rating.includes("觀察") ? " observe" : ""}`}>
                {cleanCopy(item.rating)}
              </strong>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function relationshipCompatibilityScore(radar: RelationshipFitLensData["radar"]) {
  const values = radar.map((item) => Number(item.value)).filter((value) => Number.isFinite(value));
  const average = values.length ? values.reduce((total, value) => total + value, 0) / values.length : 0;
  if (average >= 72) return { average, rating: "高" };
  if (average >= 58) return { average, rating: "中高" };
  return { average, rating: "中低" };
}

function CompatibilityRadarIcon({ name }: { name: string }) {
  if (name === "emotionalSafety") {
    return (
      <svg viewBox="0 0 24 24">
        <path d="M12 3c3.4 0 6 2.5 6 5.8 0 4.3-6 8.8-6 8.8S6 13.1 6 8.8C6 5.5 8.6 3 12 3z" />
        <path d="M8.5 18.2c1.1 1 2.3 1.8 3.5 2.8 1.2-1 2.4-1.8 3.5-2.8" />
      </svg>
    );
  }
  if (name === "communicationStability") {
    return (
      <svg viewBox="0 0 24 24">
        <path d="M4 5h12v9H9l-4 3v-3H4V5z" />
        <path d="M12 9h8v8h-3v3l-4-3h-1" />
      </svg>
    );
  }
  if (name === "conflictPressure") {
    return (
      <svg viewBox="0 0 24 24">
        <path d="M13 2L5 13h6l-1 9 8-12h-6l1-8z" />
      </svg>
    );
  }
  if (name === "repairPotential") {
    return (
      <svg viewBox="0 0 24 24">
        <path d="M4 12a8 8 0 0113.4-5.8" />
        <path d="M17 3v4h-4" />
        <path d="M20 12a8 8 0 01-13.4 5.8" />
        <path d="M7 21v-4h4" />
      </svg>
    );
  }
  if (name === "longTermAdjustment") {
    return (
      <svg viewBox="0 0 24 24">
        <path d="M12 21V9" />
        <path d="M12 9c-4 0-6-2-6-5 4 0 6 2 6 5z" />
        <path d="M12 13c4 0 6-2 6-5-4 0-6 2-6 5z" />
        <path d="M7 21h10" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24">
      <path d="M12 2l1.7 5.1L19 9l-5.3 1.9L12 16l-1.7-5.1L5 9l5.3-1.9L12 2z" />
      <path d="M5 15l.9 2.6L8.5 19l-2.6.9L5 22l-.9-2.1L1.5 19l2.6-1.4L5 15z" />
    </svg>
  );
}

function CompatibilityInsightArt({ type }: { type: "natural" | "loop" }) {
  if (type === "loop") {
    return (
      <svg viewBox="0 0 120 120" fill="none">
        <defs>
          <linearGradient id="compatibilityLoopLine" x1="18" y1="22" x2="104" y2="96">
            <stop stopColor="#8fbce8" />
            <stop offset=".52" stopColor="#d5ad67" />
            <stop offset="1" stopColor="#7f9fc8" />
          </linearGradient>
        </defs>
        <path d="M34 34c20-18 48-7 48 14 0 18-22 18-22 33 0 9 8 14 18 14 16 0 28-12 28-28" stroke="url(#compatibilityLoopLine)" strokeWidth="2" />
        <path d="M86 28c-20 18-48 7-48-14" stroke="#d7ad62" strokeWidth="1.2" opacity=".7" />
        <path d="M28 73c0-15 10-27 24-31" stroke="#8fbce8" strokeWidth="1.2" opacity=".65" />
        <path d="M24 71l5 5 5-6M88 27l-5-5-5 6" stroke="#f0d49a" strokeWidth="1.2" />
        <circle cx="59" cy="60" r="8" fill="#0c2647" stroke="#d7ad62" strokeWidth="1" />
        <path d="M59 52v16M51 60h16" stroke="#9fc8f4" strokeWidth="1" opacity=".8" />
        <circle cx="23" cy="36" r="2" fill="#9fc8f4" />
        <circle cx="97" cy="82" r="2" fill="#f0d49a" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 120 120" fill="none">
      <defs>
        <radialGradient id="compatibilityGoodOrb" cx="50%" cy="42%">
          <stop offset="0" stopColor="#e8f4ff" />
          <stop offset=".28" stopColor="#95c2ef" />
          <stop offset=".72" stopColor="#2b5a91" />
          <stop offset="1" stopColor="#07172f" />
        </radialGradient>
      </defs>
      <circle cx="44" cy="57" r="21" fill="url(#compatibilityGoodOrb)" opacity=".9" />
      <circle cx="76" cy="57" r="21" fill="none" stroke="#d9b169" strokeWidth="1.5" />
      <path d="M25 81c15-13 55-13 70 0" stroke="#d9b169" strokeWidth="1.2" opacity=".8" />
      <path d="M60 19v14M53 26h14" stroke="#f0d49a" strokeWidth="1.2" />
      <circle cx="60" cy="26" r="4" fill="#f0d49a" opacity=".9" />
      <path d="M40 96c12 7 28 7 40 0" stroke="#8fbce8" strokeWidth="1" opacity=".7" />
      <circle cx="24" cy="39" r="2" fill="#f0d49a" />
      <circle cx="96" cy="37" r="2" fill="#9fc8f4" />
    </svg>
  );
}

function fallbackRelationshipFitLens({
  archetype,
  attractionDynamics,
  conflictDynamics,
  growthDynamics,
  profiles
}: {
  archetype?: RelationshipArchetypeData;
  attractionDynamics?: RelationshipDynamicsData;
  conflictDynamics?: RelationshipDynamicsData;
  growthDynamics?: RelationshipDynamicsData;
  profiles: RelationshipProfilesData;
}): RelationshipFitLensData {
  const fit = profiles.fitSummary;
  const attraction = attractionDynamics?.items?.[0];
  const conflict = conflictDynamics?.items?.[0];
  const growth = growthDynamics?.items?.[0];
  return {
    version: "relationship-fit-lens-v1",
    relationshipType: {
      becauseA: cleanCopy(profiles.personA.headline),
      becauseB: cleanCopy(profiles.personB.headline),
      doesNotProve: cleanCopy(archetype?.doesNotProve ?? "關係類型不是命定結論。"),
      meaning: cleanCopy(archetype?.meaning ?? fit.summary),
      reasons: (archetype?.whySelected ?? []).slice(0, 3),
      subtitle: cleanCopy(archetype?.subtitle ?? "先看吸引、壓力和修復條件。"),
      title: cleanCopy(archetype?.title ?? fit.headline)
    },
    radar: [
      fallbackRadarItem("attraction", "吸引力", attraction?.technical ?? attractionDynamics?.summary, "中高"),
      fallbackRadarItem("emotionalSafety", "情緒安全", fit.summary, "中"),
      fallbackRadarItem("communicationStability", "溝通穩定", conflict?.technical ?? conflictDynamics?.summary, "中低"),
      fallbackRadarItem("conflictPressure", "衝突壓力", conflict?.meaning ?? conflictDynamics?.summary, "中高"),
      fallbackRadarItem("repairPotential", "修復潛力", growth?.meaning ?? growthDynamics?.summary, "中"),
      fallbackRadarItem("longTermAdjustment", "長期磨合度", archetype?.meaning ?? fit.summary, "中")
    ],
    bestPlaces: [
      {
        becauseA: cleanCopy(profiles.personA.headline),
        becauseB: cleanCopy(profiles.personB.headline),
        body: cleanCopy(attraction?.everydaySignal ?? attraction?.meaning ?? "你們有可以互相牽動的位置。"),
        proof: cleanCopy(attraction?.technical ?? attractionDynamics?.summary ?? ""),
        title: "有可以靠近的入口"
      }
    ],
    conditions: [
      {
        body: cleanCopy(growth?.advice ?? "把期待拆成小而可執行的行動。"),
        label: "比較有機會穩下來",
        watchFor: "看回應是否自然延伸，而不是只看一次熱絡。"
      },
      {
        body: cleanCopy(conflict?.everydaySignal ?? "一靠近就變成攻防時，關係會持續消耗。"),
        label: "會繼續消耗的狀態",
        watchFor: "互動後你更焦慮，對方更想退開。"
      }
    ],
    doesNotProve: "契合雷達與關係類型只說明互動條件，不能保證承諾、復合或長久結果。",
    stuckLoop: {
      summary: cleanCopy(conflict?.everydaySignal ?? "你們容易在靠近時觸發壓力。"),
      title: cleanCopy(conflict?.title ?? "一靠近就容易變急"),
      steps: [
        { body: cleanCopy(profiles.personA.headline), label: "你的起點" },
        { body: cleanCopy(profiles.personB.headline), label: "他的起點" },
        { body: cleanCopy(conflict?.meaning ?? "合盤壓力讓互動容易變重。"), label: "互相誤會" },
        { body: cleanCopy(conflict?.advice ?? "先把問題拆小。"), label: "怎麼中斷" }
      ]
    },
    summary: cleanCopy(profiles.answerBridge || fit.summary)
  };
}

function fallbackRadarItem(key: string, label: string, proof = "", rating = "中"): RelationshipFitLensData["radar"][number] {
  return {
    becauseA: "從你的星盤定位看關係需求",
    becauseB: "從他的星盤定位看接收方式",
    key,
    label,
    proof: cleanCopy(proof),
    rating,
    reason: cleanCopy(`因為從你的星盤定位看關係需求；同時從他的星盤定位看接收方式。合盤證據是：${proof}`),
    value: rating === "高" ? 84 : rating === "中高" ? 70 : rating === "中低" ? 56 : 42
  };
}

function insightMechanismCards(
  attractionDynamics: RelationshipDynamicsData | undefined,
  conflictDynamics: RelationshipDynamicsData | undefined,
  growthDynamics: RelationshipDynamicsData | undefined,
  buckets: readonly { key: FitItem["relation"]; title: string; items: FitItem[] }[]
) {
  const fallbackCards = fitMechanismCards(buckets);
  return [
    insightMechanismCard({
      block: attractionDynamics,
      fallback: fallbackCards[0],
      icon: "heart",
      key: "natural",
      title: "核心吸引力"
    }),
    insightMechanismCard({
      block: conflictDynamics,
      fallback: fallbackCards[2],
      icon: "hourglass",
      key: "friction",
      title: "衝突相位"
    }),
    insightMechanismCard({
      block: growthDynamics,
      fallback: fallbackCards[1],
      icon: "sparkles",
      key: "effort",
      title: "成長線索"
    })
  ];
}

function insightMechanismCard({
  block,
  fallback,
  icon,
  key,
  title
}: {
  block?: RelationshipDynamicsData;
  fallback: ReturnType<typeof fitMechanismCards>[number];
  icon: string;
  key: FitItem["relation"];
  title: string;
}) {
  const firstItem = block?.items?.[0];
  return {
    asset: fallback.asset,
    body: cleanCopy(firstItem?.everydaySignal ?? block?.summary ?? fallback.body),
    icon,
    key,
    title
  };
}

function insightInteractionCards(
  attractionDynamics: RelationshipDynamicsData | undefined,
  conflictDynamics: RelationshipDynamicsData | undefined,
  growthDynamics: RelationshipDynamicsData | undefined,
  buckets: readonly { key: FitItem["relation"]; title: string; items: FitItem[] }[],
  fit: RelationshipProfilesData["fitSummary"]
) {
  const fallbackCards = fitInteractionCards(buckets, fit);
  const attractionItems = uniqueInsightItems(attractionDynamics?.items).slice(0, 2);
  const conflictItems = uniqueInsightItems(conflictDynamics?.items).slice(0, 2);
  const growthItems = uniqueInsightItems(growthDynamics?.items).slice(0, 1);
  const cards = [
    attractionItems[0]
      ? insightInteractionCardFromItem({
          eyebrow: "核心吸引力相位",
          icon: "heart",
          item: attractionItems[0],
          title: attractionItems[0].title
        })
      : undefined,
    attractionItems[1]
      ? insightInteractionCardFromItem({
          eyebrow: "另一條吸引力",
          icon: "heart",
          item: attractionItems[1],
          title: attractionItems[1].title
        })
      : undefined,
    conflictItems[0]
      ? insightInteractionCardFromItem({
          eyebrow: "衝突相位",
          icon: "hourglass",
          item: conflictItems[0],
          title: conflictItems[0].title
        })
      : undefined,
    growthItems[0]
      ? insightInteractionCardFromItem({
          eyebrow: "成長相位",
          icon: "sparkles",
          item: growthItems[0],
          title: growthItems[0].title
        })
      : conflictItems[1]
        ? insightInteractionCardFromItem({
            eyebrow: "第二個卡點",
            icon: "hourglass",
            item: conflictItems[1],
            title: conflictItems[1].title
          })
        : undefined
  ].filter((card): card is ReturnType<typeof insightInteractionCardFromItem> => Boolean(card));

  return cards.length >= 4 ? cards.slice(0, 4) : [...cards, ...fallbackCards].slice(0, 4);
}

function insightInteractionCardFromItem({
  eyebrow,
  icon,
  item,
  title
}: {
  eyebrow: string;
  icon: string;
  item: RelationshipInsightAspectItemData;
  title: string;
}) {
  return {
    eyebrow,
    evidence: cleanCopy(item.technical),
    icon,
    phenomenon: cleanCopy(item.everydaySignal || item.meaning),
    repair: cleanCopy(item.advice),
    title: cleanCopy(title || eyebrow)
  };
}

function uniqueInsightItems(items: RelationshipInsightAspectItemData[] = []) {
  const seen = new Set<string>();
  return items.filter((item) => {
    const key = `${item.title}|${item.technical}|${item.everydaySignal}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function fitMechanismCards(
  buckets: readonly { key: FitItem["relation"]; title: string; items: FitItem[] }[]
) {
  return buckets.map((bucket) => {
    const item = bucket.items[0];
    const meta = FIT_BUCKET_META[bucket.key];
    return {
      asset: `/cosmic/relationship-fit-${bucket.key}.webp`,
      body: fitReadableBody(item, meta.description),
      icon: meta.icon,
      key: bucket.key,
      takeaway: cleanCopy(item?.nextMove ?? meta.questionBridge),
      title: bucket.title
    };
  });
}

function fitInteractionCards(
  buckets: readonly { key: FitItem["relation"]; title: string; items: FitItem[] }[],
  fit: RelationshipProfilesData["fitSummary"]
) {
  const naturalItem = buckets.find((bucket) => bucket.key === "natural")?.items[0] ?? fit.pivotalAspect ?? undefined;
  const effortItem = buckets.find((bucket) => bucket.key === "effort")?.items[0] ?? naturalItem;
  const frictionItem = buckets.find((bucket) => bucket.key === "friction")?.items[0] ?? effortItem;
  const repairItem = effortItem ?? naturalItem ?? frictionItem;

  return [
    interactionCardFromItem({
      fallbackEvidence: "自然牽動訊號",
      fallbackPhenomenon: "這段關係裡仍有比較容易靠近的位置，先看靠近之後能不能穩定延續。",
      icon: "heart",
      item: naturalItem,
      repair: cleanCopy(naturalItem?.nextMove ?? "先讓自然互動存在，不急著把好感推成關係定義。"),
      title: "自然牽動"
    }),
    interactionCardFromItem({
      fallbackEvidence: "溝通與修復訊號",
      fallbackPhenomenon: "你們需要把話說短、說清楚，才比較不會各自用自己的語言猜對方。",
      icon: "chat-bubble",
      item: effortItem,
      repair: cleanCopy(effortItem?.nextMove ?? "先說成具體、可回應的一句話，不要一次談全部。"),
      title: "需要說清楚"
    }),
    interactionCardFromItem({
      fallbackEvidence: "壓力或卡住訊號",
      fallbackPhenomenon: "壓力一升高，互動容易變急、變硬，或讓其中一方先退開。",
      icon: "hourglass",
      item: frictionItem,
      repair: cleanCopy(frictionItem?.nextMove ?? "先降溫，不用追問、試探或要求立即表態。"),
      title: "壓力觸發"
    }),
    interactionCardFromItem({
      fallbackEvidence: "可修復的互動訊號",
      fallbackPhenomenon: "真正有用的修復不是把話講更多，而是讓對方有空間自然接住。",
      icon: "sparkles",
      item: repairItem,
      repair: cleanCopy(repairItem?.nextMove ?? "用短、輕、可退場的方式接近；如果沒有延伸，就先停。"),
      title: "可以怎麼修"
    })
  ];
}

function interactionCardFromItem({
  fallbackEvidence,
  fallbackPhenomenon,
  icon,
  item,
  repair,
  title
}: {
  fallbackEvidence: string;
  fallbackPhenomenon: string;
  icon: string;
  item?: FitItem;
  repair: string;
  title: string;
}) {
  return {
    evidence: cleanCopy(item ? `${item.title}｜${item.relationLabel}` : fallbackEvidence),
    icon,
    phenomenon: fitReadableBody(item, fallbackPhenomenon),
    repair: cleanCopy(repair),
    title
  };
}

function fitReadableBody(item: FitItem | undefined, fallback: string) {
  if (!item) return cleanCopy(fallback);
  const body = cleanCopy(item.readableInterpretation?.body ?? item.body)
    .replace(/^你的[^。！？]+形成[^。！？]+[。！？]/u, "")
    .replace(/^這條[^：]+：/u, "")
    .trim();
  const conclusion = body.match(/這代表[^。！？]+[。！？]/u)?.[0];
  return cleanCopy(conclusion || body || fallback);
}

function fitBridgeSummary(
  buckets: readonly { key: FitItem["relation"]; title: string; items: FitItem[] }[]
) {
  const strongest = [...buckets].sort((first, second) => second.items.length - first.items.length)[0];
  const pressure = buckets.find((bucket) => bucket.key === "friction");
  const effort = buckets.find((bucket) => bucket.key === "effort");
  const strongestText = strongest?.items.length
    ? `先從「${strongest.title}」看起，會比較清楚這段關係現在是容易靠近、需要放慢，還是容易被壓力卡住。`
    : "先確認哪些互動最明顯。";
  const pressureText = pressure?.items.length
    ? "如果一急就容易誤會，下一步要先降溫，而不是直接逼對方表態。"
    : "如果摩擦訊號不多，後面會更重視時機與穩定回應。";
  const effortText = effort?.items.length
    ? "需要磨合的地方，會影響聯絡時要不要說得更短、更清楚。"
    : "需要磨合的地方少時，也不能直接等於一定順利，還要看現實狀態和當下時機。";
  return `${strongestText}${pressureText}${effortText}`;
}

function fitFocusCards(
  buckets: readonly { key: FitItem["relation"]; title: string; items: FitItem[] }[]
) {
  return buckets.map((bucket) => {
    if (bucket.key === "natural") {
      return {
        body: bucket.items.length
          ? "先看哪裡還能自然靠近，這代表互動裡仍有比較容易被接住的位置。"
          : "自然吸引不是主軸時，會先看其他更明顯的互動線索。",
        key: bucket.key,
        title: bucket.title
      };
    }
    if (bucket.key === "effort") {
      return {
        body: bucket.items.length
          ? "真正需要練習的是節奏和說法：把話放短、放清楚，壓力就比較不會升高。"
          : "目前磨合線索不重，仍要看現實回應和當下時機，不能直接判定順利。",
        key: bucket.key,
        title: bucket.title
      };
    }
    return {
      body: bucket.items.length
        ? "容易誤會的地方要先降溫，不適合用追問或試探去逼答案。"
        : "壓力線不是主軸時，仍要用現實回應確認關係是否能穩住。",
      key: bucket.key,
      title: bucket.title
    };
  });
}

function PivotalSynastrySignal({ doesNotProve, item }: { doesNotProve?: string; item: FitItem }) {
  const body = cleanCopy(item.readableInterpretation?.body ?? item.body);
  const shortBody = extractRelationshipConclusion(body);
  const technicalSignal = extractTechnicalSignal(body);

  return (
    <article className="cosmic-fit-feature">
      <div className="cosmic-fit-feature-visual" aria-hidden="true">
        <CosmicChartWheel variant="small" />
        <span className="fit-feature-node node-a" />
        <span className="fit-feature-node node-b" />
        <i />
      </div>
      <div className="cosmic-fit-feature-copy">
        <span>關鍵合盤訊號</span>
        <h3>{cleanCopy(item.title)}</h3>
        <strong>{cleanCopy(item.relationLabel)}</strong>
        <p>{shortBody}</p>
        {technicalSignal ? <small>{technicalSignal}</small> : null}
        {item.nextMove ? <b>{cleanCopy(item.nextMove)}</b> : null}
        {doesNotProve ? <em>先用這個訊號看你們怎麼互相牽動，再回到現實回應。</em> : null}
      </div>
    </article>
  );
}

function extractRelationshipConclusion(body: string) {
  const conclusion = body.match(/這代表[^。]+。/u)?.[0];
  if (conclusion) return conclusion;
  return body.length > 124 ? `${body.slice(0, 124)}...` : body;
}

function extractTechnicalSignal(body: string) {
  const technical = body.match(/你的[^。；]+形成[^。；]+(?:。|；)/u)?.[0];
  return technical ? cleanCopy(technical.replace(/[；。]$/u, "")) : "";
}

function FitSignal({ item }: { item: FitItem }) {
  const meta = FIT_BUCKET_META[item.relation];

  return (
    <article className={`cosmic-fit-signal ${item.relation}`}>
      <div>
        <span>{item.relationLabel}</span>
        <strong>{item.title}</strong>
      </div>
      <p>{cleanCopy(item.readableInterpretation?.body ?? item.body)}</p>
      <em>{meta.questionBridge}</em>
      {item.nextMove ? <small>{cleanCopy(item.nextMove)}</small> : null}
    </article>
  );
}

function CoreQuestionPanel({
  data,
  finalReading
}: {
  data: ResultViewModel;
  finalReading?: FinalReadingSection;
}) {
  const reviewedSummary = reviewedSummaryCopy(finalReading);
  const answerGuidance = data.answerGuidance ?? data.readableQuestionAnswer?.sections.answer;
  const answerReadable = answerGuidance?.readableInterpretation;
  const normalUserAnswer = data.normalUserAnswer ?? answerGuidance?.normalUserAnswer;
  const answerTitle = cleanCopy(answerGuidance?.questionLabel ?? data.reading.question);
  const answerHeadline = reviewedSummary?.headline ?? cleanCopy(finalReading?.headline ?? normalUserAnswer?.headline ?? answerReadable?.headline);
  const answerBody = reviewedSummary?.paragraph ?? normalizeCoreAnswerBody(
    cleanCopy(finalReading?.body ?? normalUserAnswer?.directAnswer ?? answerGuidance?.shortAnswer ?? answerReadable?.body ?? data.reading.answer)
  );
  const answerNextMove = cleanCopy(finalReading?.nextMove ?? normalUserAnswer?.nextStep ?? answerGuidance?.nextMove ?? answerReadable?.nextMove);
  const answerEvidenceBridge = cleanCopy(normalUserAnswer?.evidenceBridge);

  return (
    <div className="cosmic-answer-grid reading-core-page">
      <article className="cosmic-answer-card reading-glass reading-answer-panel">
        <i className="reading-corner tl" />
        <i className="reading-corner tr" />
        <i className="reading-corner bl" />
        <i className="reading-corner br" />
        <div className="reading-answer-main">
          <div className="reading-question-block">
            <div className="reading-micro-label">你問的是</div>
            <p className="reading-question">{answerTitle}</p>
            <div className="reading-question-note">
              此處聚焦你最在意的情緒問題，並把星盤線索翻成現實裡看得到的方向。
            </div>
          </div>
          <div className="cosmic-answer-copy reading-answer-copy" data-reviewed-summary="core-answer">
            <span>這題的短答案</span>
            {answerHeadline ? <h3 className="reading-answer-headline">{answerHeadline}</h3> : null}
            <p className="reading-answer-body">{answerBody}</p>
            {reviewedSummary ? (
              <small className="reviewed-summary-caution">{reviewedSummary.caution}</small>
            ) : answerEvidenceBridge ? <small>{answerEvidenceBridge}</small> : answerNextMove ? <small>{answerNextMove}</small> : null}
          </div>
        </div>
        <aside className="reading-boundary">
          <div className="reading-boundary-title">閱讀範圍</div>
          <div className="reading-boundary-chip"><span className="reading-chip-icon">✦</span><span>看看得見的反應</span></div>
          <div className="reading-boundary-chip"><span className="reading-chip-icon">☾</span><span>看現實回應</span></div>
          <div className="reading-boundary-chip"><span className="reading-chip-icon">⌛</span><span>看互動節奏</span></div>
          <div className="reading-boundary-note">把答案放回你能看見、能選擇的事情上。</div>
        </aside>
      </article>

      <PartnerNeedsPanel partnerNeeds={data.partnerNeeds} />
    </div>
  );
}

function normalizeCoreAnswerBody(body: string) {
  return body
    .replaceAll("最容易誤會的是", "容易看錯的是")
    .replaceAll("容易誤會的是", "容易看錯的是");
}

function stripTimingWindowDatePrefix(title?: string | null) {
  return cleanCopy(title).replace(/^20\d{2}\s*年[^：:]{1,24}[：:]\s*/u, "");
}

function PartnerNeedsPanel({ partnerNeeds }: { partnerNeeds?: PartnerNeedsData }) {
  const items = partnerNeeds?.items?.slice(0, 3) ?? [];
  const profile = partnerNeeds?.profile;
  if (!items.length) return null;

  return (
    <section className="cosmic-partner-needs-panel reading-card" aria-label="對方在感情裡真正需要什麼">
      <div className="reading-section-head compact">
        <div>
          <div className="reading-title-line">
            <span className="reading-sigil">☾</span>
            <h3 className="reading-section-title">對方在感情裡真正需要什麼</h3>
          </div>
          <p className="reading-section-sub">
            先看他想要的關係輪廓、愛意語言和壓力下的反應，最後才收成一個靠近建議。
          </p>
        </div>
        <div className="reading-section-kicker">先理解，不急著行動</div>
      </div>
      {profile ? (
        <article className="cosmic-partner-profile-card">
          <div className="cosmic-partner-profile-head">
            <span>對方在感情裡真正需要什麼</span>
            <strong>{cleanCopy(profile.title ?? "他想要的關係輪廓")}</strong>
          </div>
          <dl>
            <div>
              <dt>他在找的關係</dt>
              <dd>{cleanCopy(profile.relationshipStyleWanted ?? partnerNeeds?.framing)}</dd>
            </div>
            <div>
              <dt>安全感怎麼來</dt>
              <dd>{cleanCopy(profile.emotionalSafetyCondition)}</dd>
            </div>
            <div>
              <dt>愛意語言</dt>
              <dd>{cleanCopy(profile.affectionLanguage)}</dd>
            </div>
            <div>
              <dt>壓力下的反應</dt>
              <dd>{cleanCopy(profile.conflictDefense)}</dd>
            </div>
            <div>
              <dt>承諾節奏</dt>
              <dd>{cleanCopy(profile.commitmentPace)}</dd>
            </div>
            <div>
              <dt>什麼會打開他</dt>
              <dd>{cleanCopy(profile.whatOpensHimUp)}</dd>
            </div>
            <div>
              <dt>什麼會讓他關上</dt>
              <dd>{cleanCopy(profile.whatShutsHimDown)}</dd>
            </div>
            <div>
              <dt>容易誤會</dt>
              <dd>{cleanCopy(profile.commonMisread)}</dd>
            </div>
          </dl>
          {profile.boundaryNote ? <small>{cleanCopy(profile.boundaryNote)}</small> : null}
        </article>
      ) : null}
      <div className="cosmic-partner-source-head">
        <span>星盤依據</span>
        <p>下面只列出哪些關係功能支持這個輪廓，不再把每顆星各自重複成一份完整建議。</p>
      </div>
      <div className="cosmic-partner-source-grid">
        {items.map((item) => (
          <article className="cosmic-partner-source-card" key={`${item.point}-${item.title}`}>
            <div className="cosmic-partner-need-top">
              <span>{cleanCopy(item.point)}</span>
              <strong>{cleanCopy(item.title)}</strong>
            </div>
            <p>{cleanCopy(item.need)}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function MetricSigil({ metric }: { metric: MetricItem }) {
  const iconName = metric.key === "action" ? "arrow-right" : metric.key === "pressure" ? "hourglass" : metric.key === "attraction" ? "heart" : "sparkles";

  return (
    <article className="cosmic-metric-card">
      <IconAsset name={iconName} />
      <span>{metric.label}</span>
      <strong>{metric.value}</strong>
      <small>{metric.helper}</small>
    </article>
  );
}

function TimingPanel({
  finalReading,
  relationshipTurningWindows,
  timingGuidance
}: {
  finalReading?: FinalReadingSection;
  relationshipTurningWindows?: RelationshipTurningWindowsData;
  timingGuidance?: ResultViewModel["timingGuidance"];
}) {
  const reviewedSummary = reviewedSummaryCopy(finalReading);
  const timingReadable = timingGuidance?.readableInterpretation;
  const timingSignals = timingGuidance?.selectedSignals?.slice(0, 5) ?? [];
  const recommendedAction = cleanCopy(timingGuidance?.recommendedActionLabel ?? timingActionDisplayLabel(timingGuidance, "先保守看"));
  const topSignal = timingSignals[0];
  const cautionSignal = timingSignals.find((signal) => signal.state === "caution");
  const supportSignal = timingSignals.find((signal) => signal.state === "support");
  const decisionReasonSignal = cautionSignal ?? supportSignal ?? topSignal;
  const decisionReason = cleanCopy(
    decisionReasonSignal?.body ??
      timingReadable?.body ??
      "先把當下星象、聯絡狀態與關係壓力放在一起看，重點是抓現在的互動節奏。"
  );
  const timingHeadline = reviewedSummary?.headline ?? stripTimingWindowDatePrefix(timingReadable?.headline ?? finalReading?.headline ?? "現在先看節奏，不急著加速");
  const timingBody = reviewedSummary?.paragraph ?? cleanCopy(finalReading?.body ?? timingReadable?.body ?? "這一段會把近期氣候整理成現在適合靠近、觀察、等待，還是暫停。");
  return (
    <div className="cosmic-timing-layout cosmic-timing-editorial-grid">
        <div className="cosmic-timing-left-column">
          <article className="cosmic-timing-oracle cosmic-timing-panel cosmic-timing-summary-card">
            <div className="cosmic-timing-summary-copy" data-reviewed-summary="timing-reading">
              <div className="cosmic-timing-section-label">目前互動節奏</div>
              <h2>{timingHeadline}</h2>
              <p className="cosmic-timing-summary-body">{timingBody}</p>
              {reviewedSummary ? <small className="reviewed-summary-caution">{reviewedSummary.caution}</small> : null}
              <p className="cosmic-timing-summary-note">
                <strong>{recommendedAction}</strong>
                <span>{decisionReason}</span>
              </p>
            </div>
            <aside className="cosmic-timing-state-area">
              <div className="cosmic-timing-section-label">此刻建議</div>
              <div className="cosmic-timing-decision cosmic-timing-primary-state" aria-label="目前行動燈號">
                <span className="cosmic-timing-state-dot" aria-hidden="true" />
                <span>{recommendedAction}</span>
              </div>
              <p className="cosmic-timing-state-reason">{decisionReason}</p>
            </aside>
          </article>
        </div>

        <div className="cosmic-timing-right-column">
          <TurningWindowsPanel relationshipTurningWindows={relationshipTurningWindows} />
        </div>
    </div>
  );
}

function TurningWindowsPanel({
  relationshipTurningWindows
}: {
  relationshipTurningWindows?: RelationshipTurningWindowsData;
}) {
  const windows = visibleTurningWindows(relationshipTurningWindows);
  if (!windows.length) return null;

  return (
    <section className="cosmic-timing-panel cosmic-turning-window-panel" aria-label="2026 關係重要轉折氣候">
      <div className="cosmic-timing-panel-title-row">
        <div>
          <h2>2026 關係重要轉折氣候</h2>
          <p>{cleanCopy(relationshipTurningWindows?.summary ?? "月旬區間可以顯示互動比較緊或比較鬆的時段。")}</p>
        </div>
        <span className="cosmic-timing-soft-tag">月旬區間</span>
      </div>
      <div className="cosmic-turning-window-list">
        {windows.map((window) => (
          <article className="cosmic-turning-window-card" key={`${window.title}-${window.technical}`}>
            <div className="cosmic-turning-window-head">
              <span>{cleanCopy(window.periodLabel ?? window.windowLabel)}</span>
              <strong>{cleanCopy(window.title)}</strong>
            </div>
            <p>{cleanCopy(window.meaning)}</p>
            <dl>
              <div>
                <dt>{cleanCopy(window.categoryLabel).includes("水星") ? "可以怎麼開口" : "適合怎麼用"}</dt>
                <dd>{cleanCopy(window.suggestion)}</dd>
              </div>
              <div>
                <dt>先避開</dt>
                <dd>{cleanCopy(window.whatToAvoid)}</dd>
              </div>
            </dl>
            <small>{cleanCopy(window.technical)}</small>
          </article>
        ))}
      </div>
    </section>
  );
}

function visibleTurningWindows(relationshipTurningWindows?: RelationshipTurningWindowsData) {
  const items = relationshipTurningWindows?.items ?? [];
  const softWindow = items.find((window) => stripTimingWindowDatePrefix(cleanCopy(window.title)) === "關係氣氛比較柔和");
  const tensionWindow =
    items.find((window) => stripTimingWindowDatePrefix(cleanCopy(window.title)) === "容易擦槍走火的時段") ??
    items.find((window) => isTensionTurningWindow(window));
  return [softWindow, tensionWindow ? normalizeTensionTurningWindow(tensionWindow) : undefined].filter(
    (window): window is RelationshipTurningWindowsData["items"][number] => Boolean(window)
  );
}

function isTensionTurningWindow(window: RelationshipTurningWindowsData["items"][number]) {
  const title = stripTimingWindowDatePrefix(cleanCopy(window.title));
  if (title === "關係氣氛比較柔和") return false;
  const text = [
    window.title,
    window.categoryLabel,
    window.technical,
    window.meaning,
    window.suggestion,
    window.whatToAvoid,
    window.transitPoint
  ]
    .map((item) => cleanCopy(item))
    .join(" ");
  return /火星|土星|壓力|責任|承諾|界線|放慢|緊|急|衝|activation|pressure|saturn|mars/i.test(text);
}

function normalizeTensionTurningWindow(window: RelationshipTurningWindowsData["items"][number]) {
  return {
    ...window,
    categoryLabel: cleanCopy(window.categoryLabel) || "關係緊張",
    meaning:
      cleanCopy(window.meaning) ||
      "這段時間比較容易因為語氣、速度或壓力讓互動變緊；先縮小動作，比急著推進更重要。",
    suggestion:
      cleanCopy(window.suggestion) ||
      "先降火，不要用行動證明在乎；等刺激下降再談。",
    title: "容易擦槍走火的時段",
    whatToAvoid:
      cleanCopy(window.whatToAvoid) ||
      "避免質問、長文、連續追問，或把一次回應直接推成關係結果。"
  };
}

function timingStepLabel(index: number) {
  return ["第一步", "第二步", "第三步"][index] ?? `第 ${index + 1} 步`;
}

function timingActionDisplayLabel(timingGuidance: ResultViewModel["timingGuidance"] | undefined, fallback: string) {
  const key = `${timingGuidance?.recommendedAction ?? ""} ${timingGuidance?.contactMode ?? ""} ${fallback}`.toLowerCase();
  if (key.includes("avoid_push") || key.includes("do_not_push") || fallback.includes("避開推進")) {
    return "只觀察，不追問";
  }
  if (key.includes("observe_only")) return "先觀察，不行動";
  if (key.includes("low_pressure")) return "短訊息試水溫";
  return fallback;
}

function ActionDirectionPanel({
  actionGuidance,
  chance,
  donts,
  finalReading,
  fightLandmines,
  timeline,
  reasons
}: {
  actionGuidance?: ResultViewModel["actionGuidance"];
  chance: ResultViewModel["chance"];
  donts: BoundaryItem[];
  finalReading?: FinalReadingSection;
  fightLandmines?: FightLandminesData;
  timeline: TimelineStepData[];
  reasons: ReasonCardData[];
}) {
  const reviewedSummary = reviewedSummaryCopy(finalReading);
  const topReason = reasons[0];
  const actionReadable = finalReading ?? actionGuidance?.readableInterpretation;
  const actionScale = actionGuidance?.actionScale ?? null;
  const blockedActions = actionGuidance?.blockedActions?.slice(0, 4) ?? [];
  const actionModeKey = actionGuidance?.actionMode ?? "";
  const actionMode = actionModeAdvice(actionGuidance?.actionMode);
  const actionNextMove = removeActionMeta(actionGuidance?.nextMove ?? actionReadable?.nextMove ?? chance.nextMove ?? chance.notes[0]);
  const actionBody = removeActionMeta(actionReadable?.body ?? topReason?.nextMove ?? "先把自己的步調穩住，再判斷是否需要靠近或等待。");
  const actionCaution = removeActionMeta(actionReadable?.caution ?? donts[0]?.readableInterpretation?.body ?? donts[0]?.body);
  const primaryBlockedAction = blockedActions[0] ? blockedActionAdvice(blockedActions[0]) : null;
  const avoidLine = cleanCopy(primaryBlockedAction ? `${primaryBlockedAction.label}：${primaryBlockedAction.body}` : actionCaution || "不要把一次回應直接推成復合、承諾或關係定義。");
  const stopLine = cleanCopy(actionMode.responseRule);
  const messageScripts = buildActionMessageScripts(actionMode);
  const responseBranches = buildActionResponseBranches();
  const landmineItems = buildVisibleLandmines(fightLandmines, actionMode, donts);
  const primaryLandmine = landmineItems[0] ?? null;
  const strategyTitle = cleanCopy(actionReadable?.headline ?? chance.readableInterpretation?.headline ?? actionMode.title);
  const primaryAction = cleanCopy(actionNextMove || actionBody || actionMode.body);
  const actionLevel = clampActionLevel(actionScale ?? actionModeDefaultScale(actionModeKey));
  const modePill = actionModePill(actionModeKey, actionMode.title);
  const strategyHeadline = actionStrategyHeadline(actionModeKey, strategyTitle || actionMode.title);
  const checklistItems = buildActionChecklistItems({
    actionMode,
    avoidLine,
    primaryAction,
    primaryBlockedAction,
    stopLine
  });
  const rhythmSteps = buildActionRhythmSteps(timeline, actionMode);

  return (
    <div className="reading-action-flow">
      <ActionSectionHeader
        eyebrow="CURRENT ACTION MODE"
        title="行動策略"
        subtitle="先把此刻最安全的行動模式說清楚。"
      />

      <article className="cosmic-action-score reading-action-panel reading-action-strategy-card">
        <div className="reading-action-strategy-main" data-reviewed-summary="action-direction">
          <div className="reading-action-micro-label">目前適合做到哪一步</div>
          <h3>{reviewedSummary?.headline ?? strategyHeadline}</h3>
          <p className="reading-action-strategy-body">{reviewedSummary?.paragraph ?? (actionBody || actionMode.body)}</p>
          <p className="reading-action-strategy-foot">
            {reviewedSummary?.caution ?? "你要觀察的不是一句話說得夠不夠好，而是對方是否願意自然延伸互動。"}
          </p>
        </div>
        <aside className="reading-action-strategy-side">
          <div className="reading-action-micro-label">目前模式</div>
          <div className="reading-action-mode-pill"><i /> <span>{modePill}</span></div>
          <div className="reading-action-meter-title">目前適合做到哪一步</div>
          <div className="reading-action-meter" aria-label={`行動強度 1 到 5，目前為第 ${actionLevel} 階段`}>
            {ACTION_METER_LABELS.map((label, index) => {
              const step = index + 1;
              const state = step < actionLevel ? "past" : step === actionLevel ? "current" : "";
              return (
                <div className={`reading-action-meter-step ${state}`} key={label}>
                  <span className="reading-action-meter-dot">{step}</span>
                  <span className="reading-action-meter-name">{label}</span>
                </div>
              );
            })}
          </div>
          <p className="reading-action-meter-caption">{actionMode.body}</p>
        </aside>
      </article>

      <ActionSectionHeader
        eyebrow="CLEAR BEFORE YOU ACT"
        title="先確認這 4 件事"
        subtitle="把可以做、需要停，以及容易誤讀的地方分開來看。"
      />
      <section className="cosmic-action-checklist reading-action-check-grid" aria-label="行動選擇">
        {checklistItems.map((item) => (
          <article className="reading-action-check-card" key={item.label}>
            <div className="reading-action-check-top">
              <div className="reading-action-micro-label">{item.label}</div>
              <span className="reading-action-check-symbol">{item.symbol}</span>
            </div>
            <h3>{item.title}</h3>
            <p>{item.body}</p>
            <div className="reading-action-check-rule"><b>判斷方式：</b>{item.rule}</div>
          </article>
        ))}
      </section>

      <ActionSectionHeader
        eyebrow="THREE-STEP RHYTHM"
        title="接下來的節奏"
        subtitle="每一步都包含：要做什麼、看什麼，以及在哪裡停。"
      />
      <section className="cosmic-action-timeline-panel reading-action-panel reading-action-rhythm-panel" aria-label="接下來的節奏">
        <div className="reading-action-rhythm-track">
          {rhythmSteps.map((step, index) => (
            <article className="reading-action-rhythm-step" key={`${step.title}-${index}`}>
              <div className="reading-action-rhythm-node">{String(index + 1).padStart(2, "0")}</div>
              <h3>{timingStepLabel(index)}｜{step.title}</h3>
              <div className="reading-action-rhythm-detail">
                {step.rows.map((row) => (
                  <div className="reading-action-detail-row" key={`${step.title}-${row.label}`}>
                    <span>{row.label}</span>
                    <p>{row.body}</p>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>

      <ActionSectionHeader
        title="行動前檢查"
        subtitle="送出之前，安靜確認自己還有沒有選擇。"
      />
      <section className="reading-action-panel reading-action-checkpoint-card" aria-label="行動前檢查">
        <div className="reading-action-checkpoint-intro">
          <div className="reading-action-micro-label">安靜停一下</div>
          <p>三個問題都能坦然回答，再決定是否行動。</p>
        </div>
        <div className="reading-action-prompt-grid">
          {ACTION_CHECKPOINT_PROMPTS.map((prompt) => (
            <article className="reading-action-prompt" key={prompt.question}>
              <div className="reading-action-prompt-question"><i /> <span>{prompt.question}</span></div>
              <p>{prompt.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="reading-action-section" id="messages">
        <div className="reading-action-section-head">
          <div className="reading-action-section-title-lock">
            <div>
              <h2>短訊息範例</h2>
              <p>保留真心，也保留對方決定是否接住的空間。</p>
            </div>
          </div>
          <div className="reading-action-message-banner">選一則就好，不要連發</div>
        </div>
        <div className="cosmic-message-scripts reading-action-message-grid" aria-label="可直接使用的短訊息">
          {messageScripts.map((script) => (
            <article className="reading-action-message-card" key={script.title}>
              <span>{script.title}</span>
              <blockquote>{script.body}</blockquote>
              <footer>{messageScriptUsage(script.title)}</footer>
            </article>
          ))}
        </div>
      </section>

      <ActionSectionHeader
        eyebrow="RESPONSE GUIDE"
        title="回應分岔"
        subtitle="不用預測結果，只需要知道每種回應出現時怎麼接。"
      />
      <section className="cosmic-response-branches reading-action-branch-grid" aria-label="對方不同反應時怎麼做">
        {responseBranches.map((branch) => (
          <article className="reading-action-branch-card" key={branch.title}>
            <div className="reading-action-branch-header">
              <h3>{branch.title}</h3>
              <span>{branch.tag}</span>
            </div>
            <div className="reading-action-branch-line">
              <span>下一步</span>
              <p>{branch.nextStep}</p>
            </div>
            <div className="reading-action-branch-line">
              <span>界線</span>
              <p>{branch.boundary}</p>
            </div>
          </article>
        ))}
      </section>

      {primaryLandmine ? (
        <>
          <ActionSectionHeader
            title="最需要避開的一個地雷"
            subtitle="找出最容易讓互動失去節奏的那一刻。"
          />
          <section className="cosmic-boundary-panel cosmic-action-landmine-brief reading-action-panel reading-action-minefield-card" aria-label="最需要避開的一個地雷">
            <div className="reading-action-minefield-lead">
              <div className="reading-action-micro-label">地雷名稱</div>
              <h3>{cleanCopy(primaryLandmine.title)}</h3>
            </div>
            <div className="reading-action-minefield-content">
              <article className="reading-action-minefield-row">
                <span>最容易被點燃的情境</span>
                <strong>{cleanCopy(primaryLandmine.trigger)}</strong>
                <p>{cleanCopy(primaryLandmine.whyItHappens)}</p>
              </article>
              <article className="reading-action-minefield-row">
                <span>關係裡容易發生什麼</span>
                <strong>想靠說清楚換回安全感，對方卻只感受到更多壓力</strong>
                <p>內容越完整，不一定越容易被理解；在接收度不足時，訊息量本身就可能成為負擔。</p>
              </article>
              <article className="reading-action-minefield-row wide">
                <span>改成這樣做</span>
                <strong>{cleanCopy(primaryLandmine.whatToDoInstead)}</strong>
                <p>先讓互動停在可承受的位置，等你能接受對方不立刻回覆時，再決定是否需要補充。</p>
              </article>
            </div>
          </section>
        </>
      ) : null}

    </div>
  );
}

function ActionSectionHeader({
  eyebrow,
  subtitle,
  title
}: {
  eyebrow?: string;
  subtitle: string;
  title: string;
}) {
  return (
    <header className="reading-action-section-head">
      <div className="reading-action-section-title-lock">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
      </div>
      {eyebrow ? <div className="reading-action-section-note">{eyebrow}</div> : null}
    </header>
  );
}

const ACTION_METER_LABELS = ["靜待", "輕觸", "對話", "深談", "決定"];

const ACTION_CHECKPOINT_PROMPTS = [
  {
    body: "能把話說清楚就好，不把回覆當成立刻止住不安的方法。",
    question: "我現在是在表達，還是在逼答案？"
  },
  {
    body: "如果不能，訊息裡可能已經帶著超過目前節奏的期待。",
    question: "這句話對方可以不回嗎？"
  },
  {
    body: "能停，才代表這一步仍然在你的選擇裡，而不是被焦慮推著走。",
    question: "送出後我能不能真的停？"
  }
];

function clampActionLevel(value: number) {
  return Math.min(5, Math.max(1, Math.round(value)));
}

function actionModeDefaultScale(key: string) {
  if (key.includes("shared_space")) return 1;
  if (key.includes("small_bid")) return 2;
  if (key.includes("low_stimulation")) return 2;
  return 1;
}

function actionModePill(key: string, fallback: string) {
  if (key.includes("shared_space")) return "保護場域";
  if (key.includes("small_bid")) return "跟著回應走";
  if (key.includes("low_stimulation")) return "可以輕觸";
  return cleanCopy(fallback);
}

function actionStrategyHeadline(key: string, fallback: string) {
  const cleaned = cleanCopy(fallback);
  if (cleaned) return cleaned;
  if (key.includes("shared_space")) return "先保護共同場域，不把現場變成攤牌";
  if (key.includes("small_bid")) return "跟著回應慢慢走，不主動加速";
  if (key.includes("low_stimulation")) return "可以輕觸，但先不要把話題推進";
  return "讓行動變小、變清楚，而且隨時能停";
}

function buildActionChecklistItems({
  actionMode,
  avoidLine,
  primaryAction,
  primaryBlockedAction,
  stopLine
}: {
  actionMode: { body: string; responseRule: string; title: string };
  avoidLine: string;
  primaryAction: string;
  primaryBlockedAction: ReturnType<typeof blockedActionAdvice> | null;
  stopLine: string;
}) {
  return [
    {
      body: primaryAction || actionMode.body,
      label: "可以做",
      rule: "說完之後，不需要再補第二句。",
      symbol: "○",
      title: "留下一個能自然結束的輕觸"
    },
    {
      body: avoidLine,
      label: "先不要",
      rule: "一段訊息只處理一件事。",
      symbol: "—",
      title: cleanCopy(primaryBlockedAction?.label ?? "不要一次談完所有關係問題")
    },
    {
      body: stopLine,
      label: "停止線",
      rule: "沒有雙向投入，就不主動加碼。",
      symbol: "⌁",
      title: "沒有自然延伸，就停在這裡"
    },
    {
      body: "沒有立即回覆，不代表你不重要；回得短，也不一定等於完全拒絕。先只理解成：此刻的接收空間有限。",
      label: "不要怎麼自我解讀",
      rule: "只看實際互動，不用猜測沉默的含義。",
      symbol: "◇",
      title: "不要替沉默補上一整個故事"
    }
  ];
}

function buildActionRhythmSteps(timeline: TimelineStepData[], actionMode: { body: string; responseRule: string; title: string }) {
  const sourceSteps: Array<Partial<TimelineStepData> & { body: string; nextMove?: string; title: string }> = timeline.length ? timeline.slice(0, 3) : [
    { title: "先穩住，再決定要不要行動", body: actionMode.body, nextMove: actionMode.responseRule },
    { title: "只做一次壓力比較小的輕觸", body: actionMode.body, nextMove: actionMode.responseRule },
    { title: "讓回應決定下一步", body: actionMode.responseRule, nextMove: actionMode.responseRule }
  ];

  return sourceSteps.map((step, index) => {
    const body = cleanCopy(step.readableInterpretation?.body ?? step.body);
    const nextMove = cleanCopy(step.nextMove ?? step.readableInterpretation?.nextMove ?? actionMode.responseRule);
    const title = cleanCopy(step.title);
    const observation = index === 0
      ? "情緒平一點之後，確認這句話是不是仍然值得被說。"
      : index === 1
        ? "看對方有沒有自然補充、問你問題，或主動延長對話。"
        : "看互動是否穩定，以及雙方是否都願意持續投入。";
    const stop = index === 0
      ? "如果你只是希望對方立刻給答案，就先不送出。"
      : index === 1
        ? "回覆很短或沒有延伸，就不再加上第二個話題。"
        : nextMove || "又回到你單方面維持時，就把節奏收回來。";

    return {
      rows: [
        { body, label: "要做" },
        { body: observation, label: "觀察" },
        { body: stop, label: "停止" }
      ],
      title
    };
  });
}

function messageScriptUsage(title: string) {
  if (title.includes("不逼問")) return "適合：前一次互動有壓力，需要先把語氣放平。";
  if (title.includes("退場")) return "適合：你想表達開放，但不要求當下得到答案。";
  return "適合：沒有新的衝突，只想輕輕恢復聯絡。";
}

function buildVisibleLandmines(
  fightLandmines: FightLandminesData | undefined,
  actionMode: { body: string; responseRule: string; title: string },
  donts: BoundaryItem[]
) {
  const seen = new Set<string>();
  const sourceItems = fightLandmines?.items ?? [];
  const deduped = sourceItems.filter((item) => {
    const key = `${item.title}|${item.trigger}|${item.whatToDoInstead}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  const fallbackItems = donts.slice(0, 3).map((item, index) => ({
    title: index === 0 ? "把焦慮變成第二則訊息" : index === 1 ? "一次想談完整段關係" : "把沒有回覆解讀成自己不夠重要",
    trigger: cleanCopy(item.readableInterpretation?.body ?? (item.body || actionMode.body)),
    whyItHappens: index === 0
      ? "越想確認答案，越容易用更多訊息增加對方壓力。"
      : "壓力大的時候，一次談太多會讓對話變硬，而不是修復。",
    whatToDoInstead: index === 0
      ? "先停在一則短訊息，等對方自然回應再決定下一步。"
      : actionMode.responseRule
  }));

  return [...deduped, ...fallbackItems].slice(0, 3);
}

function blockedActionAdvice(action: string) {
  return BLOCKED_ACTION_COPY[action] ?? {
    label: "先不要做這個行動",
    body: "這個行動目前容易增加關係負擔，先不要把它當成下一步。"
  };
}

function buildActionMessageScripts(actionMode: { body: string; responseRule: string; title: string }) {
  const baseBoundary = actionMode.title.includes("共同場域")
    ? "如果現場遇到，就先保持自然禮貌，不用急著談那件事。"
    : "不用特別回，我只是剛好想到，跟你說一聲。";

  return [
    {
      body: "剛剛看到一個東西想到你，覺得有點好笑，就傳給你。",
      title: "輕觸型"
    },
    {
      body: "最近突然想到以前聊過的那件事，希望你最近一切都還好。",
      title: "不逼問型"
    },
    {
      body: baseBoundary,
      title: "可退場型"
    }
  ];
}

function buildActionResponseBranches() {
  return [
    {
      boundary: "不要因為一次暖回，就立刻把對話推向關係結論。",
      nextStep: "先接住當下話題，保持輕鬆；來回穩定後，再看是否適合約一個平靜的時間聊。",
      tag: "有延伸",
      title: "暖回"
    },
    {
      boundary: "沒有自然延伸，就先不要把短回解讀成繼續推進的邀請。",
      nextStep: "禮貌收住，不補問，讓對話停在一個不尷尬也不施壓的位置。",
      tag: "沒延伸",
      title: "短回"
    },
    {
      boundary: "不要用更多說明補足沉默，也不用反覆改寫同一個意思。",
      nextStep: "不追加訊息，把注意力移回日常，等新的自然互動出現。",
      tag: "先停下",
      title: "不回"
    },
    {
      boundary: "不辯解、不說服，也不把一段已經變冷的對話繼續拖長。",
      nextStep: "簡短回應或直接收尾，先尊重對方目前表現出的距離。",
      tag: "收尾",
      title: "冷回"
    }
  ];
}

function IconAsset({
  fallback,
  name
}: {
  fallback?: string;
  name: string;
}) {
  const safeName = name === "warning" ? fallback ?? "info-circle" : name;
  return <img src={`/celestial-icons/${safeName}.svg`} alt="" aria-hidden="true" />;
}

function CosmicTwinLuminaries() {
  return (
    <div className="cosmic-twin-luminaries" aria-hidden="true">
      <div className="cosmic-chart-wheel hero-wheel">
        {ZODIAC_SIGNS.map((sign, index) => (
          <span
            key={sign}
            style={{
              transform: `rotate(${index * 30}deg) translateY(-46%) rotate(${-index * 30}deg)`
            }}
          >
            {sign}
          </span>
        ))}
        <i className="chart-line line-one" />
        <i className="chart-line line-two" />
        <i className="chart-line line-three" />
      </div>
      <div className="cosmic-disc moon-disc">
        <b />
      </div>
      <div className="cosmic-disc sun-disc">
        <b />
      </div>
      <span className="orbit-glow glow-one" />
      <span className="orbit-glow glow-two" />
    </div>
  );
}

function CosmicPersonDial({ tone }: { tone: "moon" | "sun" }) {
  return (
    <div className={`cosmic-person-dial ${tone}`} aria-hidden="true">
      <span />
      <i />
      <b />
    </div>
  );
}

function CosmicChartWheel({ variant = "default" }: { variant?: "default" | "small" }) {
  return (
    <div className={`cosmic-chart-wheel ${variant}`} aria-hidden="true">
      {ZODIAC_SIGNS.map((sign, index) => (
        <span
          key={sign}
          style={{
            transform: `rotate(${index * 30}deg) translateY(-45%) rotate(${-index * 30}deg)`
          }}
        >
          {sign}
        </span>
      ))}
      <i className="chart-line line-one" />
      <i className="chart-line line-two" />
      <i className="chart-line line-three" />
    </div>
  );
}

function CosmicChartBanner() {
  return (
    <div className="cosmic-chart-composition">
      <CosmicChartWheel />
      <div className="chart-banner-copy">
        <span>Synastry Map</span>
        <strong>把兩個人的星盤放在同一張關係地圖裡</strong>
      </div>
      <div className="chart-aspect-lines">
        <i />
        <i />
        <i />
      </div>
    </div>
  );
}
