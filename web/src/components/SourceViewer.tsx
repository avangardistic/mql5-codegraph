import { FileCode2, X } from "lucide-react";
import { useEffect, useMemo, useRef } from "react";

type Props = {
  source: { file: string; content: string; highlight_line: number } | null;
  onClose: () => void;
};

export function SourceViewer({ source, onClose }: Props) {
  const highlightRef = useRef<HTMLDivElement>(null);
  const lines = useMemo(() => source?.content.split(/\r?\n/) ?? [], [source]);
  useEffect(() => { highlightRef.current?.scrollIntoView({ block: "center" }); }, [source]);
  useEffect(() => {
    if (!source) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [source, onClose]);
  if (!source) return null;
  return (
    <div className="source-overlay" role="dialog" aria-modal="true" aria-label={`Source ${source.file}`}>
      <div className="source-viewer">
        <header>
          <FileCode2 size={18} />
          <div><strong>{source.file.split("/").at(-1)}</strong><span>{source.file}</span></div>
          <em>line {source.highlight_line}</em>
          <button onClick={onClose} aria-label="Close source viewer"><X size={18} /></button>
        </header>
        <div className="source-code">
          {lines.map((line, index) => {
            const lineNumber = index + 1;
            return (
              <div key={lineNumber} ref={lineNumber === source.highlight_line ? highlightRef : undefined}
                   className={lineNumber === source.highlight_line ? "highlight" : ""}>
                <span>{lineNumber}</span><code>{line || " "}</code>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
