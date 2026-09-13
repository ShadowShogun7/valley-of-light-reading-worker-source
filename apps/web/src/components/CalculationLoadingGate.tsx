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
import { useEffect, useState } from "react";
import { BrandLogo } from "@/components/BrandLogo";
import type { CalculationStep } from "@/data/complete-relationship-result";

export const relationshipCalculationSteps: CalculationStep[] = [
  { label: "星體定位", result: "兩人的個人星盤" },
  { label: "相位計算", result: "合盤相位與互動影響" },
  { label: "關係能量分析", result: "親密、壓力與安全感" },
  { label: "靈合解讀", result: "核心問題與行動方向" },
];

const calculationStageIcons = [Sun, Orbit, HeartPulse, Sparkles];

export function CalculationLoadingGate({
  brand,
  error,
  isResultReady,
  onRetry,
  onShowResult,
  processingDescription = "正在整理兩人的星盤、合盤相位與關係線索。",
  steps,
}: {
  brand: { subtitle: string; title: string };
  error: string | null;
  isResultReady: boolean;
  onRetry: () => void;
  onShowResult: () => void;
  processingDescription?: string;
  steps: CalculationStep[];
}) {
  const [visibleStepCount, setVisibleStepCount] = useState(1);
  const isVisualSequenceComplete = visibleStepCount >= steps.length;
  const isComplete = isVisualSequenceComplete && isResultReady;
  const completedStepCount = isComplete ? steps.length : Math.max(0, visibleStepCount - 1);
  const progressPercent = steps.length > 0 ? (completedStepCount / steps.length) * 100 : 0;
  const pageState = error ? "failed" : isComplete ? "completed" : "processing";

  useEffect(() => {
    if (error || isVisualSequenceComplete) return;
    const timer = window.setTimeout(() => {
      setVisibleStepCount((current) => Math.min(current + 1, steps.length));
    }, 620);
    return () => window.clearTimeout(timer);
  }, [error, steps.length, isVisualSequenceComplete, visibleStepCount]);

  const title = error
    ? "這次解析暫時沒有完成"
    : isComplete
      ? "你們的完整關係解讀已準備完成"
      : "正在解析你們的宇宙軌跡";
  const eyebrow = error ? "解析暫時中斷" : isComplete ? "解讀已完成" : "星軌整理中";
  const description = error
    ? "你可以重新嘗試一次，或返回確認出生資料是否完整。"
    : isComplete
      ? "兩人的星盤、合盤相位與關係線索已經整理完成。"
      : processingDescription;
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
  visibleStepCount,
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
  step,
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
