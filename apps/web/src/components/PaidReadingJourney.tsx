"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AstrologyResultPage } from "@/components/AstrologyResultPage";
import { BrandLogo } from "@/components/BrandLogo";
import {
  IntakeFlow,
  type IntakeAnswers,
} from "@/components/IntakeFlow";
import type { CompleteRelationshipResultViewModel } from "@/data/complete-relationship-result";

type JourneyState = "loading" | "intake" | "processing" | "ready" | "error";

type LookupPayload = {
  consentVersion?: string;
  draft?: IntakeAnswers;
  error?: string;
  result?: Record<string, unknown>;
  state?: "intake" | "processing" | "ready";
};

const brand = { subtitle: "Valley of Light", title: "光之谷" };

export function PaidReadingJourney() {
  const [journeyState, setJourneyState] = useState<JourneyState>("loading");
  const [draft, setDraft] = useState<IntakeAnswers | undefined>();
  const [consentVersion, setConsentVersion] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [draftMessage, setDraftMessage] = useState("");
  const draftTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastPersistedDraft = useRef("");
  const endpoint = "/api/reading-access";

  const loadReading = useCallback(async () => {
    try {
      const response = await fetch(endpoint, {
        cache: "no-store",
        headers: { Accept: "application/json" },
      });
      const payload = (await response.json().catch(() => null)) as LookupPayload | null;
      if (!response.ok || !payload?.state) {
        setJourneyState("error");
        setErrorMessage(
          response.status === 404
            ? "這個閱讀連結已失效或無法使用。請回到付款信箱確認最新郵件，或聯絡客服協助。"
            : "目前暫時無法載入你的解讀。請稍後再試。"
        );
        return;
      }
      setErrorMessage("");
      if (payload.state === "intake" && payload.draft && payload.consentVersion) {
        setDraft(payload.draft);
        setConsentVersion(payload.consentVersion);
        lastPersistedDraft.current = JSON.stringify(payload.draft);
        setJourneyState("intake");
        return;
      }
      if (payload.state === "ready" && payload.result) {
        setResult(payload.result);
        setJourneyState("ready");
        return;
      }
      setJourneyState("processing");
    } catch {
      setJourneyState("error");
      setErrorMessage("目前暫時無法載入你的解讀。請稍後再試。");
    }
  }, [endpoint]);

  useEffect(() => {
    void loadReading();
  }, [loadReading]);

  useEffect(() => {
    if (journeyState !== "processing") return;
    const interval = window.setInterval(() => {
      void loadReading();
    }, 15000);
    return () => window.clearInterval(interval);
  }, [journeyState, loadReading]);

  useEffect(
    () => () => {
      if (draftTimer.current) clearTimeout(draftTimer.current);
    },
    []
  );

  const saveDraft = useCallback(
    (answers: IntakeAnswers) => {
      const serialized = JSON.stringify(answers);
      if (serialized === lastPersistedDraft.current) return;
      if (draftTimer.current) clearTimeout(draftTimer.current);
      setDraftMessage("正在儲存…");
      draftTimer.current = setTimeout(async () => {
        try {
          const response = await fetch(`${endpoint}/intake`, {
            body: serialized,
            headers: { "Content-Type": "application/json" },
            method: "PATCH",
          });
          if (response.status === 409) {
            void loadReading();
            return;
          }
          if (!response.ok) throw new Error("draft save failed");
          lastPersistedDraft.current = serialized;
          setDraftMessage("已安全儲存");
        } catch {
          setDraftMessage("尚未儲存，請保持此頁開啟後再試");
        }
      }, 800);
    },
    [endpoint, loadReading]
  );

  async function submitIntake(answers: IntakeAnswers) {
    if (!consentVersion || isSubmitting) return;
    if (draftTimer.current) clearTimeout(draftTimer.current);
    setIsSubmitting(true);
    setErrorMessage("");
    setDraftMessage("");
    try {
      const response = await fetch(`${endpoint}/submit`, {
        body: JSON.stringify({
          ...answers,
          generationConsentAccepted: true,
          generationConsentVersion: consentVersion,
        }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
      if (response.ok || response.status === 409) {
        setJourneyState("processing");
        return;
      }
      const payload = (await response.json().catch(() => null)) as
        | { error?: string }
        | null;
      setErrorMessage(
        payload?.error === "INVALID_FINAL_INTAKE"
          ? "請重新確認所有出生資料與同意欄位後再送出。"
          : "資料暫時無法送出，請稍後再試。"
      );
    } catch {
      setErrorMessage("資料暫時無法送出，請稍後再試。");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (journeyState === "intake" && draft) {
    return (
      <>
        {draftMessage || errorMessage ? (
          <div className="paid-reading-save-status" role="status">
            {errorMessage || draftMessage}
          </div>
        ) : null}
        <IntakeFlow
          brand={brand}
          initialAnswers={draft}
          isSubmitting={isSubmitting}
          onAnswersChange={saveDraft}
          onComplete={submitIntake}
          requireConsent
          submitLabel="送出並建立我的解讀"
        />
      </>
    );
  }

  if (journeyState === "ready" && result) {
    return (
      <AstrologyResultPage
        data={result as unknown as CompleteRelationshipResultViewModel}
      />
    );
  }

  return (
    <main className="paid-reading-state-shell">
      <section className="paid-reading-state-card" aria-live="polite">
        <BrandLogo className="paid-reading-state-logo" variant="wordmark" />
        {journeyState === "loading" ? (
          <>
            <div className="paid-reading-spinner" aria-hidden="true" />
            <h1>正在安全開啟你的解讀</h1>
            <p>請稍候，我們正在確認這個付款連結的目前狀態。</p>
          </>
        ) : journeyState === "processing" ? (
          <>
            <span className="paid-reading-state-kicker">資料已鎖定</span>
            <h1>你的完整關係解讀正在建立中</h1>
            <p>
              你不需要再次填寫資料。完成後，我們會寄信通知你；之後使用同一個連結，就會直接回到完成結果。
            </p>
            <button onClick={() => void loadReading()} type="button">
              重新確認進度
            </button>
          </>
        ) : (
          <>
            <span className="paid-reading-state-kicker">無法開啟</span>
            <h1>這個連結目前無法使用</h1>
            <p>{errorMessage}</p>
            <a className="paid-reading-recovery-link" href="/recover">
              重新取得安全連結
            </a>
            <button onClick={() => void loadReading()} type="button">
              再試一次
            </button>
          </>
        )}
      </section>
    </main>
  );
}
