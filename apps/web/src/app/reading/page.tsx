import type { Metadata } from "next";
import { PaidReadingJourney } from "@/components/PaidReadingJourney";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  robots: {
    follow: false,
    index: false,
    noarchive: true,
    nocache: true,
  },
  title: "我的關係解讀 | 光之谷",
};

export default function PaidReadingPage() {
  return <PaidReadingJourney />;
}
