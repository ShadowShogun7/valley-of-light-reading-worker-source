import type { Metadata } from "next";
import { AccessLinkExchange } from "@/components/AccessLinkExchange";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  robots: {
    follow: false,
    index: false,
    noarchive: true,
    nocache: true,
  },
  title: "正在安全開啟解讀 | 光之谷",
};

export default function ReadingAccessPage() {
  return <AccessLinkExchange />;
}
