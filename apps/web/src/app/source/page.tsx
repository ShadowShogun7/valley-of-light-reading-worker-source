import type { Metadata } from "next";
import { BrandLogo } from "@/components/BrandLogo";

export const metadata: Metadata = {
  title: "AGPL 原始碼 | 光之谷",
  description: "光之谷付費解讀網路服務的對應原始碼",
};

export const dynamic = "force-dynamic";

export default function SourcePage() {
  const sourceUrl = process.env.VALLEY_AGPL_SOURCE_URL?.trim();
  const sourceSha256 = process.env.VALLEY_AGPL_SOURCE_SHA256?.trim();

  return (
    <main className="paid-reading-state-shell">
      <section className="paid-reading-state-card">
        <BrandLogo className="paid-reading-state-logo" variant="wordmark" />
        <span className="paid-reading-state-kicker">AGPL-3.0-or-later</span>
        <h1>對應原始碼</h1>
        <p>
          光之谷的付費解讀網路服務採用 GNU Affero General Public License。
          每個正式部署版本都會提供相符、可免費取得的原始碼封存檔。
        </p>
        {sourceUrl && sourceSha256 ? (
          <>
            <a href={sourceUrl} rel="external">
              下載此版本原始碼
            </a>
            <code className="agpl-source-digest">
              SHA-256: {sourceSha256}
            </code>
          </>
        ) : (
          <p>解讀服務尚未正式啟用，因此目前沒有已部署版本的原始碼封存檔。</p>
        )}
        <a href="/">返回解讀入口</a>
      </section>
    </main>
  );
}
