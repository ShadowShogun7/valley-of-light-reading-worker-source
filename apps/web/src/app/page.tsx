import { BrandLogo } from "@/components/BrandLogo";

export default function Home() {
  return (
    <main className="paid-reading-state-shell">
      <section className="paid-reading-state-card">
        <BrandLogo className="paid-reading-state-logo" variant="wordmark" />
        <span className="paid-reading-state-kicker">完整關係解讀</span>
        <h1>請從付款後收到的安全郵件開啟</h1>
        <p>
          付款確認後，我們會把專屬填寫連結寄到結帳信箱。完成資料後，同一個連結會顯示處理進度與完成結果。
        </p>
        <a href="https://valeoflight.com">回到光之谷官網</a>
      </section>
    </main>
  );
}
