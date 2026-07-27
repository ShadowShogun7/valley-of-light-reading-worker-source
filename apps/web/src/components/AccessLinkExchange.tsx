"use client";

import { useEffect, useRef, useState } from "react";

type ExchangeState = "opening" | "unavailable";

export function AccessLinkExchange() {
  const [state, setState] = useState<ExchangeState>("opening");
  const exchangeStarted = useRef(false);

  useEffect(() => {
    if (exchangeStarted.current) return;
    exchangeStarted.current = true;
    let token = "";
    try {
      token = decodeURIComponent(window.location.hash.slice(1));
    } catch {
      token = "";
    }
    window.history.replaceState(null, "", "/r");
    if (!token || token.length > 256) {
      setState("unavailable");
      return;
    }

    void fetch("/api/reading-access/exchange", {
      body: JSON.stringify({ token }),
      cache: "no-store",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      method: "POST",
    })
      .then((response) => {
        if (!response.ok) throw new Error("READING_LINK_UNAVAILABLE");
        window.location.replace("/reading");
      })
      .catch(() => setState("unavailable"));

  }, []);

  return (
    <main className="paid-reading-shell">
      <section className="journey-card" aria-live="polite">
        {state === "opening" ? (
          <>
            <p className="eyebrow">光之谷 VALLEY OF LIGHT</p>
            <h1>正在安全開啟你的關係解讀</h1>
            <p>請稍候，不需要登入或建立帳號。</p>
          </>
        ) : (
          <>
            <p className="eyebrow">光之谷 VALLEY OF LIGHT</p>
            <h1>這個安全連結目前無法使用</h1>
            <p>
              請確認連結是否完整；若連結已過期，可使用訂單編號與付款信箱重新寄送。
            </p>
            <a className="primary-link" href="/recover">
              重新寄送安全連結
            </a>
          </>
        )}
      </section>
    </main>
  );
}
