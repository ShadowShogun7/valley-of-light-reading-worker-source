import type { ReadableInterpretation } from "@/data/complete-relationship-result";
import { readerChapter, READER_DISPLAY_VERSION, type ReaderSectionId } from "@/lib/paid-reading/reader-chapter";

export function ReaderChapter({ sectionId, section }: { sectionId: ReaderSectionId; section?: Partial<ReadableInterpretation> }) {
  const chapter = readerChapter(sectionId, section);
  if (!chapter) return <p role="alert">解讀內容尚未完整，請重新載入；若仍無法顯示，請聯絡客服。</p>;
  return (
    <section className="reader-chapter" data-reader-display={READER_DISPLAY_VERSION} data-reviewed-summary={sectionId}>
      <h3 data-reader-field="headline">{chapter.headline}</h3>
      {chapter.paragraphs.map((paragraph) => <p data-reader-fields={paragraph.fields.join(",")} key={paragraph.fields.join(",")}>{paragraph.text}</p>)}
      <small className="reviewed-summary-caution" data-reader-field="caution">{chapter.caution}</small>
    </section>
  );
}
