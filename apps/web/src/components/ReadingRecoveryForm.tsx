"use client";

import { FormEvent, useState } from "react";
import { BrandLogo } from "@/components/BrandLogo";

type RecoveryState = "idle" | "sending" | "accepted" | "rate_limited" | "error";

export function ReadingRecoveryForm() {
  const [billingEmail, setBillingEmail] = useState("");
  const [orderNumber, setOrderNumber] = useState("");
  const [state, setState] = useState<RecoveryState>("idle");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (state === "sending") return;
    setState("sending");
    try {
      const response = await fetch("/api/reading-access/recover", {
        body: JSON.stringify({ billingEmail, orderNumber }),
        headers: { "Content-Type": "application/json" },
        method: "POST",
      });
      if (response.status === 429) {
        setState("rate_limited");
        return;
      }
      setState(response.ok ? "accepted" : "error");
    } catch {
      setState("error");
    }
  }

  return (
    <main className="paid-reading-state-shell">
      <section className="paid-reading-state-card paid-reading-recovery-card">
        <BrandLogo className="paid-reading-state-logo" variant="wordmark" />
        <span className="paid-reading-state-kicker">安全連結協助</span>
        <h1>重新取得你的解讀連結</h1>
        {state === "accepted" ? (
          <>
            <p role="status">
              如果資料與可使用的訂單相符，安全連結會寄到付款信箱。請也檢查垃圾郵件匣。
            </p>
            <a className="paid-reading-recovery-link" href="/reading">
              回到解讀頁
            </a>
          </>
        ) : (
          <form onSubmit={submit}>
            <p>
              請填寫結帳時使用的電子郵件與 WooCommerce 訂單編號。我們不會在畫面上顯示訂單是否存在。
            </p>
            <label>
              <span>付款電子郵件</span>
              <input
                autoComplete="email"
                onChange={(event) => setBillingEmail(event.target.value)}
                required
                type="email"
                value={billingEmail}
              />
            </label>
            <label>
              <span>訂單編號</span>
              <input
                autoComplete="off"
                inputMode="numeric"
                onChange={(event) => setOrderNumber(event.target.value)}
                required
                value={orderNumber}
              />
            </label>
            <button disabled={state === "sending"} type="submit">
              {state === "sending" ? "正在確認…" : "寄送新的安全連結"}
            </button>
            {state === "rate_limited" ? (
              <p className="paid-reading-recovery-error" role="alert">
                嘗試次數較多，請稍後再試。
              </p>
            ) : state === "error" ? (
              <p className="paid-reading-recovery-error" role="alert">
                目前暫時無法送出，請稍後再試。
              </p>
            ) : null}
          </form>
        )}
      </section>
    </main>
  );
}
