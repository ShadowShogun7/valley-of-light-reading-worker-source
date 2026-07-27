"use client";

import { useEffect, useRef, useState } from "react";
import { BrandLogo } from "@/components/BrandLogo";
import { supportedBirthPlaces } from "@/lib/paid-reading/locations";

type IconName =
  | "anxiety-scribble"
  | "broken-heart"
  | "calendar"
  | "chat-bubble"
  | "clock"
  | "cold-circle"
  | "crystal"
  | "droplet"
  | "dove"
  | "eye-off"
  | "group"
  | "heart"
  | "hourglass"
  | "info-circle"
  | "leaf-sprig"
  | "location-pin"
  | "lock"
  | "moon"
  | "mountain-sun"
  | "question-circle"
  | "rain-cloud"
  | "snowflake"
  | "sparkles"
  | "sun-face"
  | "waves";

type IntakeOption = {
  description?: string;
  icon: IconName;
  label: string;
  value: string;
};

export type BirthProfile = {
  birthDate: string;
  birthTime: string;
  birthPlace: string;
  gender: "" | "female" | "male" | "other";
  unknownTime: boolean;
};

export type IntakeAnswers = {
  relationshipStage: string;
  mainQuestion: string;
  contactStatus: string;
  user: BirthProfile;
  partner: BirthProfile;
};

type IntakeStep = "opening" | "user" | "partner" | "stage" | "question" | "contact" | "confirm";
type FlowStepId = Exclude<IntakeStep, "opening">;

type FlowStep = {
  eyebrow: string;
  id: FlowStepId;
  label: string;
  note: string;
  subtitle: string;
  title: string;
};

const flowSteps: FlowStep[] = [
  {
    eyebrow: "01 你的星盤",
    id: "user",
    label: "你的出生資料",
    note: "填寫自己的出生資訊",
    subtitle: "先從你的星盤開始。出生時間如果不確定，可以直接選擇不知道。",
    title: "你的出生資料",
  },
  {
    eyebrow: "02 對方星盤",
    id: "partner",
    label: "對方的出生資料",
    note: "填寫你知道的資料",
    subtitle: "對方資料不知道沒關係，先填你目前知道的部分。",
    title: "對方的出生資料",
  },
  {
    eyebrow: "03 關係狀態",
    id: "stage",
    label: "關係狀態",
    note: "選出目前最接近的狀況",
    subtitle: "選最像你們現在狀態的一項，後面的問題會依照這裡調整。",
    title: "你們現在是什麼狀態？",
  },
  {
    eyebrow: "04 主要問題",
    id: "question",
    label: "主要問題",
    note: "聚焦這次最想知道的事",
    subtitle: "先選出你最想被解讀的那一題，結果頁會以這個方向做主軸。",
    title: "你現在最想知道什麼？",
  },
  {
    eyebrow: "05 最近互動",
    id: "contact",
    label: "最近互動",
    note: "補上現在的聯絡情境",
    subtitle: "最近的互動會影響聯絡時機、修復方式和下一步建議。",
    title: "你們最近有聯絡嗎？",
  },
  {
    eyebrow: "06 確認資料",
    id: "confirm",
    label: "確認資料",
    note: "檢查後產生解讀",
    subtitle: "確認後就會開始計算星盤、合盤相位與這次關係問題的解讀。",
    title: "確認你的解讀資料",
  },
];

const steps: Array<{ id: IntakeStep; label: string }> = [
  { id: "opening", label: "準備開始" },
  ...flowSteps.map(({ id, label }) => ({ id, label })),
];

const stageOptions: IntakeOption[] = [
  {
    description: "目前沒有正常互動，或彼此都在沉默。",
    icon: "snowflake",
    label: "冷戰 / 斷聯中",
    value: "cold-war",
  },
  {
    description: "分開不久，情緒還很近，也還沒有完全穩下來。",
    icon: "broken-heart",
    label: "剛分手",
    value: "broke-up-recent",
  },
  {
    description: "已經分開一陣子，但你還在意這段關係的可能性。",
    icon: "hourglass",
    label: "分手一段時間",
    value: "broke-up-long",
  },
  {
    description: "名義上還在一起，但互動反覆、緊張或容易吵架。",
    icon: "waves",
    label: "還在一起但很不穩",
    value: "crisis",
  },
  {
    description: "彼此有好感或持續互動，但還沒有清楚確認關係。",
    icon: "sparkles",
    label: "曖昧 / 不確定關係",
    value: "ambiguous",
  },
];

const questionOptions: IntakeOption[] = [
  {
    description: "想看對方心裡是否還有情感位置與互動餘溫。",
    icon: "heart",
    label: "他現在心裡還有我嗎？",
    value: "still-love-me",
  },
  {
    description: "想知道這段關係是否還有往前走的現實可能。",
    icon: "leaf-sprig",
    label: "我們還有機會嗎？",
    value: "any-chance",
  },
  {
    description: "想知道什麼時候比較適合重新打開互動。",
    icon: "crystal",
    label: "什麼時候適合聯絡？",
    value: "when-to-contact",
  },
  {
    description: "想看真正卡住的互動模式，而不是只怪某一個人。",
    icon: "question-circle",
    label: "是不是我做錯了什麼？",
    value: "what-did-i-do-wrong",
  },
  {
    description: "想判斷這段關係值得等待，還是該慢慢把自己收回來。",
    icon: "dove",
    label: "我該繼續等，還是放下？",
    value: "stay-or-let-go",
  },
];

const questionOptionsByStage: Record<string, IntakeOption[]> = {
  ambiguous: [
    {
      description: "想看對方的好感是否有機會變成更認真的投入。",
      icon: "heart",
      label: "他是不是有認真可能？",
      value: "still-love-me",
    },
    {
      description: "想知道這段曖昧是否可能慢慢走向正式關係。",
      icon: "leaf-sprig",
      label: "這段曖昧會不會往關係發展？",
      value: "any-chance",
    },
    {
      description: "想知道什麼時候適合讓互動更清楚，但不急著逼出關係名稱。",
      icon: "crystal",
      label: "什麼時候適合讓互動更清楚？",
      value: "when-to-contact",
    },
    {
      description: "想看忽冷忽熱背後重複的是什麼互動模式。",
      icon: "question-circle",
      label: "為什麼他會忽冷忽熱？",
      value: "what-did-i-do-wrong",
    },
    {
      description: "想判斷這段曖昧值得繼續觀察，還是該先把期待收回來。",
      icon: "dove",
      label: "這段曖昧值得繼續觀察嗎？",
      value: "stay-or-let-go",
    },
  ],
  "broke-up-recent": [
    {
      description: "剛分開時，先看對方心裡是否還留著情感反應。",
      icon: "heart",
      label: "他心裡還有我嗎？",
      value: "still-love-me",
    },
    {
      description: "想知道分手後是否還有重新靠近的可能。",
      icon: "leaf-sprig",
      label: "你們還有沒有復合機會？",
      value: "any-chance",
    },
    {
      description: "比起問確切日期，先看哪個時間點比較容易恢復互動。",
      icon: "crystal",
      label: "什麼時間點比較容易恢復互動？",
      value: "when-to-contact",
    },
    {
      description: "想看分手真正卡住的原因，而不是只停在表面事件。",
      icon: "question-circle",
      label: "分手真正卡住的原因是什麼？",
      value: "what-did-i-do-wrong",
    },
    {
      description: "想知道現在該等一等，還是先把自己穩住。",
      icon: "dove",
      label: "現在該等一等，還是先把自己穩住？",
      value: "stay-or-let-go",
    },
  ],
  "broke-up-long": [
    {
      description: "想看對方現在如何放置這段關係與你的存在。",
      icon: "heart",
      label: "他現在怎麼看待你？",
      value: "still-love-me",
    },
    {
      description: "想知道這段緣分還有沒有現實中的延續性。",
      icon: "leaf-sprig",
      label: "這段緣分是否還有現實延續性？",
      value: "any-chance",
    },
    {
      description: "如果要重新開口，先看怎麼做比較不會造成壓力。",
      icon: "crystal",
      label: "如果要重新開口，適合怎麼做？",
      value: "when-to-contact",
    },
    {
      description: "想回頭看過去真正卡住的是哪一種互動。",
      icon: "question-circle",
      label: "過去真正卡住的是哪一種互動？",
      value: "what-did-i-do-wrong",
    },
    {
      description: "想判斷繼續等待是否還有意義，或該慢慢放下。",
      icon: "dove",
      label: "你該繼續等，還是慢慢放下？",
      value: "stay-or-let-go",
    },
  ],
  "cold-war": [
    {
      description: "想知道對方是否還可能主動打開聯絡。",
      icon: "heart",
      label: "他會不會主動聯絡？",
      value: "still-love-me",
    },
    {
      description: "想看這段冷戰是否還有變軟、恢復互動的空間。",
      icon: "leaf-sprig",
      label: "冷戰還有沒有機會變軟？",
      value: "any-chance",
    },
    {
      description: "想知道現在開口比較像修復，還是容易增加壓力。",
      icon: "crystal",
      label: "現在開口會加分還是扣分？",
      value: "when-to-contact",
    },
    {
      description: "想看冷戰真正卡住的點，而不是只看誰先低頭。",
      icon: "question-circle",
      label: "冷戰真正卡住的點是什麼？",
      value: "what-did-i-do-wrong",
    },
    {
      description: "想知道要等他主動，還是先停在自己的界線內。",
      icon: "dove",
      label: "要等他主動，還是先停在界線內？",
      value: "stay-or-let-go",
    },
  ],
  crisis: [
    {
      description: "想看他是否還想繼續，也看關係本身是否還有力氣。",
      icon: "heart",
      label: "他現在是否還想繼續？",
      value: "still-love-me",
    },
    {
      description: "想知道這段關係還能不能被修回比較穩的位置。",
      icon: "leaf-sprig",
      label: "關係能不能修復？",
      value: "any-chance",
    },
    {
      description: "想知道下一步怎麼做，能先降低反覆受傷的循環。",
      icon: "crystal",
      label: "下一步怎麼降低惡性循環？",
      value: "when-to-contact",
    },
    {
      description: "想看你們反覆吵架背後真正重複的是什麼模式。",
      icon: "question-circle",
      label: "你們反覆吵架的核心模式是什麼？",
      value: "what-did-i-do-wrong",
    },
    {
      description: "想判斷這段關係還能修，還是已經太消耗。",
      icon: "dove",
      label: "這段關係還能修，還是已經太傷？",
      value: "stay-or-let-go",
    },
  ],
};

const questionSubtitlesByStage: Record<string, string> = {
  ambiguous: "關係還沒有被清楚定義時，先選出你最想確認的方向，不急著把火花直接當成承諾。",
  "broke-up-recent": "剛分開時最容易想立刻找答案，先選出你最想被解讀的那一題。",
  "broke-up-long": "如果這段關係已經停了一陣子，這一題會讓解讀更貼近現實延續性。",
  "cold-war": "你們現在的距離比較明顯，這一題會幫助後面的解讀聚焦在是否適合重新打開互動。",
  crisis: "如果你們還在關係裡，這一題會讓解讀聚焦在修復、循環和下一步怎麼降低壓力。",
};

const contactOptions: IntakeOption[] = [
  { description: "最近沒有訊息、通話或見面。", icon: "eye-off", label: "完全沒有", value: "none" },
  { description: "對方會回，但不一定穩定或主動。", icon: "chat-bubble", label: "偶爾回覆", value: "occasional" },
  { description: "還有互動，但語氣淡、距離感明顯。", icon: "cold-circle", label: "還會聊天但很冷", value: "cold-chat" },
  { description: "可能因工作、朋友、生活圈或安排而見到面。", icon: "group", label: "有見面但氣氛怪", value: "awkward-meeting" },
  { description: "目前很難直接聯絡到對方，或對方明顯退開。", icon: "lock", label: "對方封鎖 / 消失", value: "blocked" },
];

const defaultBirthProfile: BirthProfile = {
  birthDate: "",
  birthTime: "",
  birthPlace: "",
  gender: "",
  unknownTime: false,
};

const defaultPartnerProfile: BirthProfile = {
  birthDate: "",
  birthTime: "",
  birthPlace: "",
  gender: "",
  unknownTime: false,
};

const lockedTestingAnswers: IntakeAnswers = {
  relationshipStage: "broke-up-recent",
  mainQuestion: "stay-or-let-go",
  contactStatus: "occasional",
  user: {
    birthDate: "1982-02-03",
    birthTime: "00:30",
    birthPlace: "tainan",
    gender: "female",
    unknownTime: false,
  },
  partner: {
    birthDate: "1993-02-10",
    birthTime: "",
    birthPlace: "hong kong",
    gender: "male",
    unknownTime: true,
  },
};

const showTestingShortcut = process.env.NODE_ENV !== "production";

type BirthDateValidation = {
  isComplete: boolean;
  isValid: boolean;
  message: string;
};

export function IntakeFlow({
  brand,
  initialAnswers,
  isSubmitting = false,
  onAnswersChange,
  onComplete,
  requireConsent = false,
  submitLabel = "開始完整解讀",
}: {
  brand: { title: string; subtitle: string };
  initialAnswers?: Partial<IntakeAnswers>;
  isSubmitting?: boolean;
  onAnswersChange?: (answers: IntakeAnswers) => void;
  onComplete: (answers: IntakeAnswers) => void;
  requireConsent?: boolean;
  submitLabel?: string;
}) {
  const [stepIndex, setStepIndex] = useState(0);
  const [answers, setAnswers] = useState<IntakeAnswers>(() =>
    mergeInitialAnswers(initialAnswers)
  );
  const [consentAccepted, setConsentAccepted] = useState(false);
  const step = steps[stepIndex];
  const activeFlowIndex = flowSteps.findIndex((item) => item.id === step.id);
  const currentFlowStep = activeFlowIndex >= 0 ? activeFlowIndex + 1 : 0;
  const isOpening = step.id === "opening";

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [stepIndex]);

  useEffect(() => {
    onAnswersChange?.(answers);
  }, [answers, onAnswersChange]);

  function nextStep() {
    setStepIndex((current) => Math.min(current + 1, steps.length - 1));
  }

  function previousStep() {
    setStepIndex((current) => Math.max(current - 1, 0));
  }

  function goToStep(stepId: FlowStepId) {
    const nextIndex = steps.findIndex((item) => item.id === stepId);
    if (nextIndex >= 0) setStepIndex(nextIndex);
  }

  return (
    <main className={`intake-design-shell ${isOpening ? "intro-mode" : ""}`}>
      <div className="intake-design-app">
        <header className="intake-design-topbar" aria-label="頁首">
          <div className="intake-design-brand">
            <BrandLogo className="intake-design-brand-logo" variant="wordmark" />
          </div>
          <div className="intake-design-top-actions" aria-hidden="true">
            <div className="intake-design-ghost-pill">關係解讀填寫流程</div>
            <div className="intake-design-ghost-pill">
              {isOpening ? "準備開始" : `步驟 ${currentFlowStep} / ${flowSteps.length}`}
            </div>
          </div>
        </header>

        <div className="intake-design-layout">
          {isOpening ? null : (
            <IntakeStepRail activeIndex={activeFlowIndex} currentFlowStep={currentFlowStep} total={flowSteps.length} />
          )}
          <section className="intake-design-content-shell">
            {isOpening ? null : <ProgressCard current={currentFlowStep} total={flowSteps.length} />}
            <article className="intake-design-panel">
              <div className="intake-design-panel-inner">
                {step.id === "opening" ? (
                  <OpeningStep
                    brand={brand}
                    onNext={nextStep}
                    onUseTestingData={showTestingShortcut ? () => onComplete(lockedTestingAnswers) : undefined}
                  />
                ) : step.id === "user" ? (
                  <BirthDataStep
                    decorativeIcon="moon"
                    eyebrow={flowStepMeta("user").eyebrow}
                    onBack={previousStep}
                    onChange={(profile) => setAnswers((current) => ({ ...current, user: profile }))}
                    onNext={nextStep}
                    profile={answers.user}
                    requireComplete
                    subtitle={flowStepMeta("user").subtitle}
                    title={flowStepMeta("user").title}
                  />
                ) : step.id === "partner" ? (
                  <BirthDataStep
                    decorativeIcon="sun-face"
                    eyebrow={flowStepMeta("partner").eyebrow}
                    onBack={previousStep}
                    onChange={(profile) => setAnswers((current) => ({ ...current, partner: profile }))}
                    onNext={nextStep}
                    profile={answers.partner}
                    requireComplete
                    subtitle={flowStepMeta("partner").subtitle}
                    title={flowStepMeta("partner").title}
                  />
                ) : step.id === "stage" ? (
                  <ChoiceStep
                    eyebrow={flowStepMeta("stage").eyebrow}
                    onBack={previousStep}
                    onNext={nextStep}
                    onSelect={(value) => setAnswers((current) => ({ ...current, relationshipStage: value }))}
                    options={stageOptions}
                    selectedValue={answers.relationshipStage}
                    subtitle={flowStepMeta("stage").subtitle}
                    title={flowStepMeta("stage").title}
                  />
                ) : step.id === "question" ? (
                  <ChoiceStep
                    eyebrow={flowStepMeta("question").eyebrow}
                    onBack={previousStep}
                    onNext={nextStep}
                    onSelect={(value) => setAnswers((current) => ({ ...current, mainQuestion: value }))}
                    options={currentQuestionOptions(answers.relationshipStage)}
                    selectedValue={answers.mainQuestion}
                    subtitle={questionSubtitlesByStage[answers.relationshipStage] ?? flowStepMeta("question").subtitle}
                    title={flowStepMeta("question").title}
                  />
                ) : step.id === "contact" ? (
                  <ChoiceStep
                    eyebrow={flowStepMeta("contact").eyebrow}
                    onBack={previousStep}
                    onNext={nextStep}
                    onSelect={(value) => setAnswers((current) => ({ ...current, contactStatus: value }))}
                    options={contactOptions}
                    selectedValue={answers.contactStatus}
                    subtitle={flowStepMeta("contact").subtitle}
                    title={flowStepMeta("contact").title}
                  />
                ) : (
                  <ConfirmStep
                    answers={answers}
                    consentAccepted={consentAccepted}
                    eyebrow={flowStepMeta("confirm").eyebrow}
                    isSubmitting={isSubmitting}
                    onBack={previousStep}
                    onComplete={() => onComplete(answers)}
                    onConsentChange={setConsentAccepted}
                    onEdit={goToStep}
                    requireConsent={requireConsent}
                    submitLabel={submitLabel}
                    subtitle={flowStepMeta("confirm").subtitle}
                    title={flowStepMeta("confirm").title}
                  />
                )}
              </div>
            </article>
          </section>
        </div>
      </div>
    </main>
  );
}

function flowStepMeta(stepId: FlowStepId) {
  return flowSteps.find((step) => step.id === stepId) ?? flowSteps[0];
}

function mergeInitialAnswers(initialAnswers?: Partial<IntakeAnswers>): IntakeAnswers {
  return {
    contactStatus: initialAnswers?.contactStatus ?? "",
    mainQuestion: initialAnswers?.mainQuestion ?? "",
    partner: {
      ...defaultPartnerProfile,
      ...(initialAnswers?.partner ?? {}),
    },
    relationshipStage: initialAnswers?.relationshipStage ?? "",
    user: {
      ...defaultBirthProfile,
      ...(initialAnswers?.user ?? {}),
    },
  };
}

function IntakeStepRail({
  activeIndex,
  currentFlowStep,
  total,
}: {
  activeIndex: number;
  currentFlowStep: number;
  total: number;
}) {
  return (
    <aside className="intake-design-rail" aria-label="填寫步驟">
      <div className="intake-design-rail-title">
        <strong>填寫流程</strong>
        <span>
          {currentFlowStep} / {total}
        </span>
      </div>
      <div className="intake-design-steps">
        {flowSteps.map((item, index) => (
          <div
            className={`intake-design-step-item ${index === activeIndex ? "is-active" : ""} ${index < activeIndex ? "is-done" : ""}`}
            key={item.id}
          >
            <div className="intake-design-step-dot">{index < activeIndex ? "✓" : String(index + 1).padStart(2, "0")}</div>
            <div>
              <div className="intake-design-step-name">{item.label}</div>
              <div className="intake-design-step-note">{item.note}</div>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}

function ProgressCard({ current, total }: { current: number; total: number }) {
  return (
    <div className="intake-design-progress-card" aria-label="進度">
      <span className="intake-design-progress-text">
        步驟 {current} / {total}
      </span>
      <div className="intake-design-progress-track">
        <div className="intake-design-progress-bar" style={{ width: `${(current / total) * 100}%` }} />
      </div>
    </div>
  );
}

function OpeningStep({
  brand,
  onNext,
  onUseTestingData,
}: {
  brand: { title: string; subtitle: string };
  onNext: () => void;
  onUseTestingData?: () => void;
}) {
  return (
    <div className="origin-hero">
      <div className="origin-step-pill">準備開始</div>
      <div className="origin-cover">
        <div className="origin-brand" aria-label={`${brand.title} ${brand.subtitle}`}>
          <BrandLogo className="origin-brand-logo" variant="wordmark" />
        </div>

        <div className="origin-copy">
          <h1 className="origin-title">關係合盤解讀</h1>
          <p className="origin-subtitle">看懂你們之間真正卡住的地方</p>
        </div>

        <div className="origin-orbs" aria-hidden="true">
          <div className="origin-icon-card moon">
            <img alt="" src="/cosmic/my-chart-emblem.webp" />
          </div>
          <div className="origin-join" />
          <div className="origin-icon-card sun">
            <img alt="" src="/cosmic/partner-chart-emblem.webp" />
          </div>
        </div>

        <div className="origin-cta-row">
          <button className="origin-cta" onClick={onNext} type="button">
            開始填寫
          </button>
          {onUseTestingData ? (
            <button className="intake-design-test-shortcut" onClick={onUseTestingData} type="button">
              使用固定測試資料
            </button>
          ) : null}
          <div className="origin-safe-note">資料只用於本次關係解讀</div>
        </div>
      </div>
    </div>
  );
}

function ChoiceStep({
  eyebrow,
  onBack,
  onNext,
  onSelect,
  options,
  selectedValue,
  subtitle,
  title,
}: {
  eyebrow: string;
  onBack: () => void;
  onNext: () => void;
  onSelect: (value: string) => void;
  options: IntakeOption[];
  selectedValue: string;
  subtitle: string;
  title: string;
}) {
  const canContinue = selectedValue.length > 0;

  return (
    <StepScaffold eyebrow={eyebrow} subtitle={subtitle} title={title}>
      <div className="intake-design-option-grid">
        {options.map((option) => (
          <button
            className={`intake-design-option-card ${selectedValue === option.value ? "is-selected" : ""}`}
            key={option.value}
            onClick={() => onSelect(option.value)}
            type="button"
          >
            <span className="intake-design-option-title">{option.label}</span>
            <span className="intake-design-option-desc">{option.description}</span>
          </button>
        ))}
      </div>
      <NavigationRow disabled={!canContinue} onBack={onBack} onNext={onNext} />
    </StepScaffold>
  );
}

function BirthDataStep({
  decorativeIcon,
  eyebrow,
  onBack,
  onChange,
  onNext,
  profile,
  requireComplete = false,
  subtitle,
  title,
}: {
  decorativeIcon: IconName;
  eyebrow: string;
  onBack: () => void;
  onChange: (profile: BirthProfile) => void;
  onNext: () => void;
  profile: BirthProfile;
  requireComplete?: boolean;
  subtitle: string;
  title: string;
}) {
  const birthDateValidation = validateBirthDate(profile.birthDate);

  function update(patch: Partial<BirthProfile>) {
    onChange({ ...profile, ...patch });
  }

  const canContinue =
    !requireComplete ||
    (birthDateValidation.isValid && profile.gender.length > 0 && (profile.unknownTime || profile.birthTime.length > 0));

  return (
    <StepScaffold eyebrow={eyebrow} subtitle={subtitle} title={title}>
      <div className="intake-design-birth-emblem" aria-hidden="true">
        <IconImg name={decorativeIcon} />
      </div>
      <div className="intake-design-form-grid">
        <div className="intake-design-field-row intake-design-birth-primary-row">
          <label className="intake-design-form-card intake-design-date-card">
            <span className="intake-design-field-label">出生日期</span>
            <SegmentedBirthDateInput
              invalid={birthDateValidation.isComplete && !birthDateValidation.isValid}
              onChange={(birthDate) => update({ birthDate })}
              title={title}
              value={profile.birthDate}
            />
            {birthDateValidation.message ? <small className="intake-design-error">{birthDateValidation.message}</small> : null}
          </label>

          <label className="intake-design-form-card">
            <span className="intake-design-field-label">出生時間</span>
            <input
              disabled={profile.unknownTime}
              onChange={(event) => update({ birthTime: event.target.value })}
              type="time"
              value={profile.unknownTime ? "" : profile.birthTime}
            />
          </label>
        </div>

        <div className="intake-design-field-row">
          <label className="intake-design-form-card">
            <span className="intake-design-field-label">出生城市（可略過）</span>
            <select
              aria-label={`${title}出生城市`}
              autoComplete="address-level2"
              onChange={(event) => update({ birthPlace: event.target.value })}
              value={profile.birthPlace}
            >
              <option value="">不知道／不在清單（不使用宮位）</option>
              {supportedBirthPlaces.map((place) => (
                <option key={place.value} value={place.value}>
                  {place.label}
                </option>
              ))}
            </select>
            <small className="intake-design-helper">
              請從清單選擇；若不在清單可留空，解讀會自動避開需要精準地點的宮位判斷。
            </small>
          </label>

          <div className="intake-design-form-card">
            <span className="intake-design-field-label">性別</span>
            <div className="gender-segments" role="group" aria-label={`${title}性別`}>
              <button className={profile.gender === "female" ? "selected" : ""} onClick={() => update({ gender: "female" })} type="button">
                女
              </button>
              <button className={profile.gender === "male" ? "selected" : ""} onClick={() => update({ gender: "male" })} type="button">
                男
              </button>
              <button className={profile.gender === "other" ? "selected" : ""} onClick={() => update({ gender: "other" })} type="button">
                其他
              </button>
            </div>
          </div>
        </div>

        <button
          className={`intake-design-toggle-card ${profile.unknownTime ? "is-active" : ""}`}
          onClick={() => update({ birthTime: profile.unknownTime ? profile.birthTime : "", unknownTime: !profile.unknownTime })}
          type="button"
        >
          <span className="intake-design-toggle-box" aria-hidden="true" />
          <span>
            <strong>不知道出生時間</strong>
            <small>不知道也可以繼續，結果會避開需要精準時辰才適合判斷的部分。</small>
          </span>
        </button>
      </div>

      <NavigationRow disabled={!canContinue} microCopy="不知道出生時間也可以繼續；如果日期不完整，會先請你補齊。" onBack={onBack} onNext={onNext} />
    </StepScaffold>
  );
}

function StepScaffold({
  children,
  eyebrow,
  subtitle,
  title,
}: {
  children: React.ReactNode;
  eyebrow: string;
  subtitle: string;
  title: string;
}) {
  return (
    <div className="intake-design-step-page">
      <div>
        <div className="intake-design-eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p className="intake-design-subtitle">{subtitle}</p>
      </div>
      {children}
    </div>
  );
}

function NavigationRow({
  disabled = false,
  microCopy = "先選最接近的一項，後面仍然可以返回修改。",
  nextLabel = "下一步",
  onBack,
  onNext,
}: {
  disabled?: boolean;
  microCopy?: string;
  nextLabel?: string;
  onBack: () => void;
  onNext: () => void;
}) {
  return (
    <div className="intake-design-nav-row">
      <button className="intake-design-btn" onClick={onBack} type="button">
        上一步
      </button>
      <p className="intake-design-micro-copy">{microCopy}</p>
      <button className="intake-design-btn primary" disabled={disabled} onClick={onNext} type="button">
        {nextLabel}
      </button>
    </div>
  );
}

function SegmentedBirthDateInput({
  invalid = false,
  onChange,
  title,
  value,
}: {
  invalid?: boolean;
  onChange: (birthDate: string) => void;
  title: string;
  value: string;
}) {
  const monthRef = useRef<HTMLInputElement>(null);
  const dayRef = useRef<HTMLInputElement>(null);
  const [year = "", month = "", day = ""] = value.split("-");

  function nextValue(patch: { year?: string; month?: string; day?: string }) {
    const nextYear = patch.year ?? year;
    const nextMonth = patch.month ?? month;
    const nextDay = patch.day ?? day;
    onChange([nextYear, nextMonth, nextDay].join("-"));
  }

  function cleanDigits(input: string, maxLength: number) {
    return input.replace(/\D/g, "").slice(0, maxLength);
  }

  return (
    <div className="date-segments" aria-label={`${title}出生日期`}>
      <input
        aria-label={`${title}出生年份`}
        aria-invalid={invalid}
        inputMode="numeric"
        maxLength={4}
        onChange={(event) => {
          const nextYear = cleanDigits(event.target.value, 4);
          nextValue({ year: nextYear });
          if (nextYear.length === 4) monthRef.current?.focus();
        }}
        placeholder="YYYY"
        value={year}
      />
      <i>/</i>
      <input
        aria-label={`${title}出生月份`}
        aria-invalid={invalid}
        inputMode="numeric"
        maxLength={2}
        onChange={(event) => {
          const nextMonth = cleanDigits(event.target.value, 2);
          nextValue({ month: nextMonth });
          if (nextMonth.length === 2) dayRef.current?.focus();
        }}
        placeholder="MM"
        ref={monthRef}
        value={month}
      />
      <i>/</i>
      <input
        aria-label={`${title}出生日期日`}
        aria-invalid={invalid}
        inputMode="numeric"
        maxLength={2}
        onChange={(event) => nextValue({ day: cleanDigits(event.target.value, 2) })}
        placeholder="DD"
        ref={dayRef}
        value={day}
      />
    </div>
  );
}

function validateBirthDate(value: string): BirthDateValidation {
  const isComplete = /^\d{4}-\d{2}-\d{2}$/.test(value);
  if (!isComplete) return { isComplete, isValid: false, message: "" };
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return { isComplete, isValid: false, message: "請輸入完整出生日期。" };
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const isValid =
    Number.isInteger(year) &&
    Number.isInteger(month) &&
    Number.isInteger(day) &&
    year >= 1 &&
    month >= 1 &&
    month <= 12 &&
    day >= 1 &&
    day <= daysInMonth(year, month);
  return {
    isComplete,
    isValid,
    message: isValid ? "" : "請確認出生日期，這個月份沒有這一天。",
  };
}

function daysInMonth(year: number, month: number) {
  const lengths = [31, isLeapYear(year) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return lengths[month - 1] ?? 0;
}

function isLeapYear(year: number) {
  return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
}

function ConfirmStep({
  answers,
  consentAccepted,
  eyebrow,
  isSubmitting,
  onBack,
  onComplete,
  onConsentChange,
  onEdit,
  requireConsent,
  submitLabel,
  subtitle,
  title,
}: {
  answers: IntakeAnswers;
  consentAccepted: boolean;
  eyebrow: string;
  isSubmitting: boolean;
  onBack: () => void;
  onComplete: () => void;
  onConsentChange: (accepted: boolean) => void;
  onEdit: (stepId: FlowStepId) => void;
  requireConsent: boolean;
  submitLabel: string;
  subtitle: string;
  title: string;
}) {
  return (
    <StepScaffold eyebrow={eyebrow} subtitle={subtitle} title={title}>
      <div className="intake-design-review-grid">
        <ReviewCard label="你的出生資料" onEdit={() => onEdit("user")} value={birthSummary(answers.user)} />
        <ReviewCard label="對方出生資料" onEdit={() => onEdit("partner")} value={birthSummary(answers.partner)} />
        <ReviewCard label="目前狀態" onEdit={() => onEdit("stage")} value={labelFor(stageOptions, answers.relationshipStage)} />
        <ReviewCard
          label="最想知道的問題"
          onEdit={() => onEdit("question")}
          value={labelFor(currentQuestionOptions(answers.relationshipStage), answers.mainQuestion)}
        />
        <ReviewCard label="最近互動" onEdit={() => onEdit("contact")} value={labelFor(contactOptions, answers.contactStatus)} />
      </div>
      {requireConsent ? (
        <label className="intake-design-consent">
          <input
            checked={consentAccepted}
            onChange={(event) => onConsentChange(event.target.checked)}
            type="checkbox"
          />
          <span>
            我已確認上述資料，並同意使用這些資料建立本次個人化關係解讀。送出後資料會鎖定；如需更正，請聯絡客服協助。
          </span>
        </label>
      ) : null}
      <NavigationRow
        disabled={isSubmitting || (requireConsent && !consentAccepted)}
        microCopy={requireConsent ? "送出後會進入處理頁，同一連結之後會顯示完成結果。" : "你的資料僅用於本次合盤解析，不會外洩。"}
        nextLabel={isSubmitting ? "送出中…" : submitLabel}
        onBack={onBack}
        onNext={onComplete}
      />
    </StepScaffold>
  );
}

function ReviewCard({ label, onEdit, value }: { label: string; onEdit: () => void; value: string }) {
  return (
    <article className="intake-design-summary-card">
      <div>
        <div className="intake-design-summary-title">{label}</div>
        <div className="intake-design-summary-lines">
          <span>{value}</span>
        </div>
      </div>
      <button className="intake-design-edit-btn" onClick={onEdit} type="button">
        編輯
      </button>
    </article>
  );
}

function IconImg({ name }: { name: IconName }) {
  return <img alt="" aria-hidden="true" src={`/celestial-icons/${name}.svg`} />;
}

function currentQuestionOptions(stage: string) {
  return questionOptionsByStage[stage] ?? questionOptions;
}

function labelFor(options: IntakeOption[], value: string) {
  return options.find((option) => option.value === value)?.label ?? "尚未選擇";
}

function birthSummary(profile: BirthProfile) {
  const date = profile.birthDate ? profile.birthDate.split("-").join(" / ") : "日期未填";
  const time = profile.unknownTime ? "時辰未知" : profile.birthTime || "時間未填";
  const place = profile.birthPlace || "地點未填";
  const gender = profile.gender === "female" ? "女" : profile.gender === "male" ? "男" : profile.gender === "other" ? "其他" : "性別未選";
  return `${date}　${time}　${place}　${gender}`;
}
