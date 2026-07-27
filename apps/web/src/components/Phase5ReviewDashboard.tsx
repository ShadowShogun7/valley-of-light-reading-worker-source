"use client";

import { Check, ChevronLeft, ChevronRight, Download, RotateCcw, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { BrandLogo } from "@/components/BrandLogo";

const sectionOrder = [
  "relationship-fit",
  "core-answer",
  "timing-reading",
  "action-direction"
] as const;

const sectionLabels: Record<(typeof sectionOrder)[number], string> = {
  "relationship-fit": "關係型態",
  "core-answer": "核心問題",
  "timing-reading": "時機判讀",
  "action-direction": "行動方向"
};

const dimensionLabels: Record<string, string> = {
  readability: "易讀程度",
  chartSpecificity: "星盤具體度",
  pageTopicOwnership: "頁面主題聚焦"
};

type ReviewStatus = "pending" | "accepted" | "rejected";
type ReviewState = {
  status: ReviewStatus;
  scores: Record<string, number>;
  notes: string;
};

type ReviewSection = {
  headline: string;
  meaning: string;
  body: string;
  nextMove: string;
  caution: string;
};

type ReviewCase = {
  id: string;
  context: {
    relationship_stage: string;
    main_question: string;
    contact_status: string;
    emotional_risk: string;
  };
  calibrationAxes: { inputPrecision: string };
  hiddenModel: {
    archetypeTitle: string;
    primaryDynamicKey: string;
    secondaryDynamics: Array<{ key: string; role: string }>;
  };
  sections: Record<(typeof sectionOrder)[number], ReviewSection>;
};

type ReviewCorpus = {
  version: string;
  corpusVersion: string;
  corpusFingerprint: string;
  dimensions: string[];
  requiredAcceptedCount: number;
  cases: ReviewCase[];
};

function emptyReview(): ReviewState {
  return { status: "pending", scores: {}, notes: "" };
}

export function ReadingReviewDashboard({ corpus }: { corpus: ReviewCorpus }) {
  const [reviews, setReviews] = useState<Record<string, ReviewState>>({});
  const [activeId, setActiveId] = useState(corpus.cases[0]?.id ?? "");
  const [activeSection, setActiveSection] = useState<(typeof sectionOrder)[number]>("relationship-fit");
  const [stageFilter, setStageFilter] = useState("all");
  const [questionFilter, setQuestionFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [hydratedFingerprint, setHydratedFingerprint] = useState("");
  const storageKey = `valley-phase7-human-review-v1-${corpus.corpusFingerprint}`;

  useEffect(() => {
    const saved = window.localStorage.getItem(storageKey);
    let nextReviews: Record<string, ReviewState> = {};
    try {
      const parsed = saved
        ? JSON.parse(saved) as { corpusFingerprint?: string; reviews?: Record<string, ReviewState> }
        : undefined;
      if (parsed?.corpusFingerprint === corpus.corpusFingerprint && parsed.reviews) nextReviews = parsed.reviews;
    } catch {
      window.localStorage.removeItem(storageKey);
    }
    setReviews(nextReviews);
    setActiveId(corpus.cases[0]?.id ?? "");
    setHydratedFingerprint(corpus.corpusFingerprint);
  }, [corpus.corpusFingerprint, storageKey]);

  useEffect(() => {
    if (hydratedFingerprint !== corpus.corpusFingerprint) return;
    window.localStorage.setItem(storageKey, JSON.stringify({ corpusFingerprint: corpus.corpusFingerprint, reviews }));
  }, [corpus.corpusFingerprint, hydratedFingerprint, reviews, storageKey]);

  const filteredCases = useMemo(
    () =>
      corpus.cases.filter((item) => {
        const review = reviews[item.id] ?? emptyReview();
        return (
          (stageFilter === "all" || item.context.relationship_stage === stageFilter) &&
          (questionFilter === "all" || item.context.main_question === questionFilter) &&
          (riskFilter === "all" || item.context.emotional_risk === riskFilter) &&
          (statusFilter === "all" || review.status === statusFilter)
        );
      }),
    [corpus.cases, questionFilter, reviews, riskFilter, stageFilter, statusFilter]
  );

  useEffect(() => {
    if (filteredCases.length && !filteredCases.some((item) => item.id === activeId)) setActiveId(filteredCases[0].id);
  }, [activeId, filteredCases]);

  const activeCase = filteredCases.find((item) => item.id === activeId) ?? filteredCases[0] ?? corpus.cases[0];
  const activeReview = reviews[activeCase?.id] ?? emptyReview();
  const activeIndex = Math.max(0, filteredCases.findIndex((item) => item.id === activeCase?.id));
  const completedCount = Object.values(reviews).filter((item) => item.status !== "pending").length;
  const eligibleAcceptedCount = Object.values(reviews).filter(
    (item) =>
      item.status === "accepted" &&
      !item.notes.trim() &&
      corpus.dimensions.every((dimension) => (item.scores[dimension] ?? 0) >= 4)
  ).length;

  function updateReview(caseId: string, updater: (current: ReviewState) => ReviewState) {
    setReviews((current) => ({ ...current, [caseId]: updater(current[caseId] ?? emptyReview()) }));
  }

  function move(offset: number) {
    if (!filteredCases.length) return;
    const nextIndex = Math.min(filteredCases.length - 1, Math.max(0, activeIndex + offset));
    setActiveId(filteredCases[nextIndex].id);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function exportReviews() {
    const payload = {
      version: corpus.version,
      corpusVersion: corpus.corpusVersion,
      corpusFingerprint: corpus.corpusFingerprint,
      reviews: corpus.cases.map((item) => ({ caseId: item.id, ...(reviews[item.id] ?? emptyReview()) }))
    };
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "phase7-human-reviews.json";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  if (!activeCase) return null;
  const section = activeCase.sections[activeSection];

  return (
    <main className="phase5-review-shell">
      <header className="phase5-review-header">
        <div className="phase5-review-brand">
          <BrandLogo className="phase5-review-brand-mark" variant="mark" />
          <div>
            <span>Phase 7 · Production calibration</span>
            <h1>解讀品質人工審核</h1>
          </div>
        </div>
        <div className="phase5-review-progress" aria-label="審核進度">
          <strong>{completedCount} / {corpus.cases.length}</strong>
          <span>可納入 {eligibleAcceptedCount} / {corpus.requiredAcceptedCount}</span>
        </div>
        <button className="phase5-icon-command" onClick={exportReviews} title="匯出審核結果" type="button">
          <Download aria-hidden="true" size={18} />
          匯出
        </button>
      </header>

      <section className="phase5-review-filters" aria-label="審核篩選">
        <label>
          關係狀態
          <select onChange={(event) => setStageFilter(event.target.value)} value={stageFilter}>
            <option value="all">全部</option>
            {[...new Set(corpus.cases.map((item) => item.context.relationship_stage))].map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
        <label>
          核心問題
          <select onChange={(event) => setQuestionFilter(event.target.value)} value={questionFilter}>
            <option value="all">全部</option>
            {[...new Set(corpus.cases.map((item) => item.context.main_question))].map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
        <label>
          情緒狀態
          <select onChange={(event) => setRiskFilter(event.target.value)} value={riskFilter}>
            <option value="all">全部</option>
            {[...new Set(corpus.cases.map((item) => item.context.emotional_risk))].map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
        <label>
          審核狀態
          <select onChange={(event) => setStatusFilter(event.target.value)} value={statusFilter}>
            <option value="all">全部</option>
            <option value="pending">待審核</option>
            <option value="accepted">接受</option>
            <option value="rejected">退回</option>
          </select>
        </label>
      </section>

      <div className="phase5-review-layout">
        <aside className="phase5-case-list" aria-label="待審核案例">
          {filteredCases.map((item, index) => {
            const review = reviews[item.id] ?? emptyReview();
            return (
              <button aria-pressed={item.id === activeCase.id} key={item.id} onClick={() => setActiveId(item.id)} type="button">
                <span>{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <strong>{item.sections["relationship-fit"].headline}</strong>
                  <small>{item.context.relationship_stage} · {item.context.main_question}</small>
                </div>
                {review.status === "accepted" ? <Check aria-label="已接受" size={16} /> : review.status === "rejected" ? <X aria-label="已退回" size={16} /> : null}
              </button>
            );
          })}
        </aside>

        <article className="phase5-reading-review">
          <div className="phase5-case-meta">
            <div>
              <span>{activeCase.context.relationship_stage} · {activeCase.context.main_question} · {activeCase.context.contact_status} · {activeCase.context.emotional_risk}</span>
              <h2>{activeCase.sections["relationship-fit"].headline}</h2>
            </div>
            <code>{activeCase.hiddenModel.primaryDynamicKey} · {activeCase.calibrationAxes.inputPrecision}</code>
          </div>

          <nav className="phase5-section-tabs" aria-label="結果頁面">
            {sectionOrder.map((sectionId) => (
              <button aria-pressed={activeSection === sectionId} key={sectionId} onClick={() => setActiveSection(sectionId)} type="button">
                {sectionLabels[sectionId]}
              </button>
            ))}
          </nav>

          <section className="phase5-copy-preview">
            <span>{sectionLabels[activeSection]}</span>
            <h3>{section.headline}</h3>
            <strong>{section.meaning}</strong>
            <p>{section.body}</p>
            <p>{section.nextMove}</p>
            <small>{section.caution}</small>
          </section>

          <section className="phase5-score-grid" aria-label="品質評分">
            {corpus.dimensions.map((dimension) => (
              <div className="phase5-score-row" key={dimension}>
                <span>{dimensionLabels[dimension] ?? dimension}</span>
                <div role="group" aria-label={dimensionLabels[dimension] ?? dimension}>
                  {[1, 2, 3, 4, 5].map((score) => (
                    <button
                      aria-pressed={activeReview.scores[dimension] === score}
                      key={score}
                      onClick={() => updateReview(activeCase.id, (current) => ({ ...current, scores: { ...current.scores, [dimension]: score } }))}
                      type="button"
                    >
                      {score}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </section>

          <label className="phase5-review-notes">
            審核備註
            <textarea
              onChange={(event) => updateReview(activeCase.id, (current) => ({ ...current, notes: event.target.value }))}
              rows={4}
              value={activeReview.notes}
            />
          </label>

          <div className="phase5-review-actions">
            <button className="is-reject" onClick={() => updateReview(activeCase.id, (current) => ({ ...current, status: "rejected" }))} type="button">
              <X aria-hidden="true" size={18} />
              退回
            </button>
            <button onClick={() => updateReview(activeCase.id, () => emptyReview())} title="重設此案例" type="button">
              <RotateCcw aria-hidden="true" size={18} />
            </button>
            <button className="is-accept" onClick={() => updateReview(activeCase.id, (current) => ({ ...current, status: "accepted" }))} type="button">
              <Check aria-hidden="true" size={18} />
              接受
            </button>
          </div>

          <footer className="phase5-review-nav">
            <button disabled={activeIndex <= 0} onClick={() => move(-1)} title="上一個案例" type="button"><ChevronLeft size={20} /></button>
            <span>{activeIndex + 1} / {filteredCases.length}</span>
            <button disabled={activeIndex >= filteredCases.length - 1} onClick={() => move(1)} title="下一個案例" type="button"><ChevronRight size={20} /></button>
          </footer>
        </article>
      </div>
    </main>
  );
}
