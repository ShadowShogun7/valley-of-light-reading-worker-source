import type { Metadata } from "next";
import { ReadingRecoveryForm } from "@/components/ReadingRecoveryForm";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  robots: {
    follow: false,
    index: false,
    noarchive: true,
    nocache: true,
  },
  title: "重新取得解讀連結 | 光之谷",
};

export default function ReadingRecoveryPage() {
  return <ReadingRecoveryForm />;
}
