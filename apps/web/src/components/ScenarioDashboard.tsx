"use client";

import {
  AlertTriangle,
  Check,
  HeartPulse,
  LoaderCircle,
  Orbit,
  RefreshCw,
  Sparkles,
  Sun,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { AstrologyResultPage } from "@/components/AstrologyResultPage";
import { BrandLogo } from "@/components/BrandLogo";
import { IntakeFlow, type IntakeAnswers } from "@/components/IntakeFlow";
import type { CalculationStep, CompleteRelationshipResultViewModel } from "@/data/complete-relationship-result";

type FlowStage = "intake" | "loading" | "result";

const defaultBrand = { title: "光之谷", subtitle: "Valley of Light" };
const isResultScenarioPreviewEnabled =
  process.env.NODE_ENV !== "production" || process.env.NEXT_PUBLIC_ENABLE_RESULT_SCENARIO_PREVIEWS === "1";

const runtimeCalculationSteps: CalculationStep[] = [
  { label: "星體定位", result: "兩人的個人星盤" },
  { label: "相位計算", result: "合盤相位與互動影響" },
  { label: "關係能量分析", result: "親密、壓力與安全感" },
  { label: "靈合解讀", result: "核心問題與行動方向" },
];

const calculationStageIcons = [Sun, Orbit, HeartPulse, Sparkles];

export function ScenarioDashboard({ scenarios }: { scenarios: CompleteRelationshipResultViewModel[] }) {
  const [activeId, setActiveId] = useState(scenarios[0]?.id ?? "");
  const [flowStage, setFlowStage] = useState<FlowStage>("intake");
  const [runtimeResult, setRuntimeResult] = useState<CompleteRelationshipResultViewModel | null>(null);
  const [loadingError, setLoadingError] = useState<string | null>(null);
  const [lastSubmittedAnswers, setLastSubmittedAnswers] = useState<IntakeAnswers | null>(null);
  const [loadingAttempt, setLoadingAttempt] = useState(0);
  const [previewScenarioId, setPreviewScenarioId] = useState<string | null>(null);
  const activeScenario = useMemo(
    () => scenarios.find((scenario) => scenario.id === activeId) ?? scenarios[0],
    [activeId, scenarios]
  );

  useEffect(() => {
    if (!isResultScenarioPreviewEnabled) return;
    const params = new URLSearchParams(window.location.search);
    const requestedScenario =
      params.get("resultScenario") ?? params.get("scenario") ?? params.get("question");
    if (!requestedScenario && params.get("devResult") !== "1") return;

    const resolvedId = resolvePreviewScenarioId(scenarios, requestedScenario);
    const scenario = scenarios.find((item) => item.id === resolvedId);
    if (!scenario) return;

    setActiveId(scenario.id);
    setRuntimeResult(scenario);
    setLoadingError(null);
    setPreviewScenarioId(scenario.id);
    setFlowStage("result");
  }, [scenarios]);

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [flowStage]);

  async function requestRelationshipResult(answers: IntakeAnswers) {
    setRuntimeResult(null);
    setLoadingError(null);
    setLoadingAttempt((current) => current + 1);

    try {
      const response = await fetch("/api/readings/relationship-result", {
        body: JSON.stringify(answers),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
      if (!response.ok) {
        const errorBody = (await response.json().catch(() => null)) as { message?: string } | null;
        throw new Error(errorBody?.message ?? `Calculation failed with ${response.status}`);
      }
      const result = (await response.json()) as CompleteRelationshipResultViewModel;
      setRuntimeResult(result);
    } catch (error) {
      console.error("Relationship reading calculation failed", error);
      setLoadingError("目前沒有成功完成解讀。請稍後再試，或返回確認出生資料是否完整。");
    }
  }

  function handleIntakeComplete(answers: IntakeAnswers) {
    const fallbackId = resolveScenarioId(scenarios, answers);
    setActiveId(fallbackId);
    setLastSubmittedAnswers(answers);
    setPreviewScenarioId(null);
    setFlowStage("loading");
    void requestRelationshipResult(answers);
  }

  function handleCalculationRetry() {
    if (!lastSubmittedAnswers) return;
    void requestRelationshipResult(lastSubmittedAnswers);
  }

  function handlePreviewScenarioChange(scenarioId: string) {
    const scenario = scenarios.find((item) => item.id === scenarioId);
    if (!scenario) return;

    setActiveId(scenario.id);
    setRuntimeResult(scenario);
    setPreviewScenarioId(scenario.id);
    setFlowStage("result");

    const nextUrl = new URL(window.location.href);
    nextUrl.searchParams.set("resultScenario", scenario.id);
    nextUrl.searchParams.delete("scenario");
    nextUrl.searchParams.delete("question");
    nextUrl.searchParams.delete("devResult");
    window.history.replaceState({}, "", `${nextUrl.pathname}${nextUrl.search}${nextUrl.hash}`);
  }

  function handlePreviewExit() {
    setRuntimeResult(null);
    setPreviewScenarioId(null);
    setFlowStage("intake");

    const nextUrl = new URL(window.location.href);
    nextUrl.searchParams.delete("resultScenario");
    nextUrl.searchParams.delete("scenario");
    nextUrl.searchParams.delete("question");
    nextUrl.searchParams.delete("devResult");
    window.history.replaceState({}, "", `${nextUrl.pathname}${nextUrl.search}${nextUrl.hash}`);
  }

  if (flowStage === "intake") {
    return <IntakeFlow brand={activeScenario?.brand ?? defaultBrand} onComplete={handleIntakeComplete} />;
  }

  if (flowStage === "loading") {
    return (
      <CalculationLoadingGate
        brand={activeScenario?.brand ?? defaultBrand}
        error={loadingError}
        isResultReady={Boolean(runtimeResult)}
        key={loadingAttempt}
        steps={runtimeCalculationSteps}
        onRetry={handleCalculationRetry}
        onShowResult={() => setFlowStage("result")}
      />
    );
  }

  if (!runtimeResult) {
    return <IntakeFlow brand={activeScenario?.brand ?? defaultBrand} onComplete={handleIntakeComplete} />;
  }

  const resultData = runtimeResult;

  return (
    <>
      {previewScenarioId ? (
        <DevResultScenarioSwitcher
          activeId={previewScenarioId}
          scenarios={scenarios}
          onExit={handlePreviewExit}
          onSelect={handlePreviewScenarioChange}
        />
      ) : null}
      <AstrologyResultPage data={resultData} />
    </>
  );
}

function resolveScenarioId(scenarios: CompleteRelationshipResultViewModel[], answers: IntakeAnswers) {
  const exactMatch = scenarios.find(
    (scenario) =>
      scenario.context.relationship_stage === answers.relationshipStage &&
      scenario.context.main_question === answers.mainQuestion
  );
  const questionMatch = scenarios.find((scenario) => scenario.context.main_question === answers.mainQuestion);
  const stageMatch = scenarios.find((scenario) => scenario.context.relationship_stage === answers.relationshipStage);
  return exactMatch?.id ?? questionMatch?.id ?? stageMatch?.id ?? scenarios[0]?.id ?? "";
}

function resolvePreviewScenarioId(
  scenarios: CompleteRelationshipResultViewModel[],
  requestedScenario?: string | null
) {
  if (!requestedScenario) return scenarios[0]?.id ?? "";
  const normalized = requestedScenario.trim();
  const match = scenarios.find(
    (scenario) =>
      scenario.id === normalized ||
      scenario.answerGuidance?.questionKey === normalized ||
      scenario.context.main_question === normalized
  );
  return match?.id ?? scenarios[0]?.id ?? "";
}

function DevResultScenarioSwitcher({
  activeId,
  onExit,
  onSelect,
  scenarios
}: {
  activeId: string;
  onExit: () => void;
  onSelect: (scenarioId: string) => void;
  scenarios: CompleteRelationshipResultViewModel[];
}) {
  const activeScenario = scenarios.find((scenario) => scenario.id === activeId) ?? scenarios[0];

  return (
    <aside className="dev-result-switcher" aria-label="結果情境測試">
      <div className="dev-result-switcher-head">
        <span>QA fixture</span>
        <strong>{activeScenario?.answerGuidance?.questionLabel ?? "結果情境"}</strong>
      </div>
      <div className="dev-result-switcher-list" aria-label="切換核心問題情境">
        {scenarios.map((scenario, index) => (
          <button
            aria-pressed={scenario.id === activeId}
            data-scenario-id={scenario.id}
            key={scenario.id}
            onClick={() => onSelect(scenario.id)}
            type="button"
          >
            <span>{String(index + 1).padStart(2, "0")}</span>
            {scenario.answerGuidance?.questionLabel ?? scenario.id}
          </button>
        ))}
      </div>
      <button className="dev-result-switcher-exit" onClick={onExit} type="button">
        回到填寫流程
      </button>
    </aside>
  );
}

function CalculationLoadingGate({
  brand,
  error,
  isResultReady,
  onRetry,
  onShowResult,
  steps
}: {
  brand: CompleteRelationshipResultViewModel["brand"];
  error: string | null;
  isResultReady: boolean;
  onRetry: () => void;
  onShowResult: () => void;
  steps: CalculationStep[];
}) {
  const [visibleStepCount, setVisibleStepCount] = useState(1);
  const isVisualSequenceComplete = visibleStepCount >= steps.length;
  const isComplete = isVisualSequenceComplete && isResultReady;
  const completedStepCount = isComplete ? steps.length : Math.max(0, visibleStepCount - 1);
  const progressPercent = steps.length > 0 ? (completedStepCount / steps.length) * 100 : 0;
  const pageState = error ? "failed" : isComplete ? "completed" : "processing";

  useEffect(() => {
    setVisibleStepCount(1);
  }, []);

  useEffect(() => {
    if (error || isVisualSequenceComplete) return;
    const timer = window.setTimeout(() => {
      setVisibleStepCount((current) => Math.min(current + 1, steps.length));
    }, 620);
    return () => window.clearTimeout(timer);
  }, [error, steps.length, isVisualSequenceComplete, visibleStepCount]);

  const title = error
    ? "這次解析暫時沒有完成"
    : "正在解析你們的宇宙軌跡";
  const eyebrow = error ? "解析暫時中斷" : isComplete ? "解讀已完成" : "星軌整理中";
  const description = error
    ? "你可以重新嘗試一次，或返回確認出生資料是否完整。"
    : isComplete
      ? "兩人的星盤、合盤相位與關係線索已經整理完成。"
      : "正在整理兩人的星盤、合盤相位與關係線索。";
  const progressCard = (
    <aside
      className="analysis-stage-card is-compact"
      aria-labelledby="analysis-progress-title"
    >
      <div className="analysis-stage-head">
        <h2 id="analysis-progress-title">分析進度</h2>
        <div
          aria-hidden="true"
          className="analysis-progress-ring"
          style={{ "--analysis-progress": progressPercent } as React.CSSProperties}
        >
          <span>{completedStepCount}/{steps.length}</span>
        </div>
        <progress
          className="analysis-sr-only"
          max={steps.length}
          value={completedStepCount}
        >
          {completedStepCount} / {steps.length}
        </progress>
      </div>

      <CalculationRitual
        error={Boolean(error)}
        isComplete={isComplete}
        steps={steps}
        visibleStepCount={visibleStepCount}
      />

      {error ? (
        <div className="analysis-error-box" role="alert">
          <AlertTriangle aria-hidden="true" size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="analysis-action-area">
        {error ? (
          <button className="analysis-secondary-button" onClick={onRetry} type="button">
            <RefreshCw aria-hidden="true" size={17} />
            重新嘗試
          </button>
        ) : (
          <button
            className="analysis-primary-button"
            disabled={!isComplete}
            onClick={onShowResult}
            type="button"
          >
            {isComplete ? (
              <Sparkles aria-hidden="true" size={18} />
            ) : (
              <LoaderCircle aria-hidden="true" className="analysis-button-spinner" size={18} />
            )}
            {isComplete ? "查看完整解讀" : "準備中"}
          </button>
        )}
      </div>
    </aside>
  );

  return (
    <main className={`analysis-loading-page is-${pageState}`}>
      <section className="analysis-loading-shell" aria-labelledby="analysis-status-title">
        <header className="analysis-loading-topbar">
          <div className="analysis-loading-brand" aria-label={`${brand.title} ${brand.subtitle}`}>
            <BrandLogo className="analysis-loading-brand-logo" variant="horizontal" />
          </div>
          <span className="analysis-loading-context">Relationship Reading</span>
        </header>

        <div className="analysis-loading-grid is-stable">
          <section className="analysis-loading-copy">
            <div className="analysis-loading-eyebrow">{eyebrow}</div>
            <h1 id="analysis-status-title">{title}</h1>
            <p>{description}</p>
            {progressCard}
          </section>

          <aside className="analysis-complete-zodiac" aria-hidden="true">
            <img alt="" src="/cosmic/analysis-complete-zodiac.webp" />
          </aside>
        </div>
      </section>
    </main>
  );
}

function CalculationRitual({
  error,
  isComplete,
  steps,
  visibleStepCount
}: {
  error: boolean;
  isComplete: boolean;
  steps: CalculationStep[];
  visibleStepCount: number;
}) {
  return (
    <section className="analysis-stage-list" aria-label="命盤計算進度" aria-live="polite">
        {steps.map((step, index) => (
          <CalculationStepRow
            hasError={error && index === visibleStepCount - 1}
            index={index}
            isActive={!error && !isComplete && index === visibleStepCount - 1}
            isComplete={isComplete || index < visibleStepCount - 1}
            key={`${step.label}-${index}`}
            step={step}
          />
        ))}
    </section>
  );
}

function CalculationStepRow({
  hasError,
  index,
  isActive,
  isComplete,
  step
}: {
  hasError: boolean;
  index: number;
  isActive: boolean;
  isComplete: boolean;
  step: CalculationStep;
}) {
  const stateClass = hasError ? "is-error" : isComplete ? "is-done" : isActive ? "is-active" : "is-pending";
  const StageIcon = calculationStageIcons[index] ?? Sparkles;
  const stateLabel = hasError ? "需要重試" : isComplete ? "完成" : isActive ? "處理中" : "等待中";

  return (
    <div aria-current={isActive || hasError ? "step" : undefined} className={`analysis-stage ${stateClass}`}>
      <span className="analysis-stage-icon" aria-hidden="true">
        {hasError ? <AlertTriangle size={18} /> : isComplete ? <Check size={19} /> : <StageIcon size={19} />}
      </span>
      <div>
        <strong className="analysis-stage-title">{step.label}</strong>
        <p className="analysis-stage-meta">{step.result}</p>
      </div>
      <span className="analysis-stage-state">{stateLabel}</span>
    </div>
  );
}
