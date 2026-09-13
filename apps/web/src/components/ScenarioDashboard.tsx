"use client";

import { useEffect, useMemo, useState } from "react";
import { AstrologyResultPage } from "@/components/AstrologyResultPage";
import {
  CalculationLoadingGate,
  relationshipCalculationSteps,
} from "@/components/CalculationLoadingGate";
import { IntakeFlow, type IntakeAnswers } from "@/components/IntakeFlow";
import type { CompleteRelationshipResultViewModel } from "@/data/complete-relationship-result";

type FlowStage = "intake" | "loading" | "result";

const defaultBrand = { title: "光之谷", subtitle: "Valley of Light" };
const isResultScenarioPreviewEnabled =
  process.env.NODE_ENV !== "production" || process.env.NEXT_PUBLIC_ENABLE_RESULT_SCENARIO_PREVIEWS === "1";

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
        steps={relationshipCalculationSteps}
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
