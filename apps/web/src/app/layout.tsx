import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "光之谷 | 完整關係星盤解讀",
  description: "Valley of Light relationship astrology reading",
  icons: {
    icon: "/brand/valley-of-light-mark.webp",
    apple: "/brand/valley-of-light-mark.webp",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#020612"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-Hant">
      <body>
        {children}
        <a className="agpl-source-link" href="/source">
          AGPL 原始碼
        </a>
      </body>
    </html>
  );
}
