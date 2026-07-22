import { AlertCircle, ChevronRight, CircleAlert, Info, ShieldAlert } from "lucide-react";
import type { Diagnostic } from "../api";

type Props = {
  items: Diagnostic[];
  total: number;
  severity: string;
  onSeverity: (value: string) => void;
  onOpenSource: (file: string, line: number) => void;
};

const icon = (severity: string) => {
  if (severity === "error") return <ShieldAlert size={15} />;
  if (severity === "warning") return <CircleAlert size={15} />;
  return <Info size={15} />;
};

export function DiagnosticsPanel({ items, total, severity, onSeverity, onOpenSource }: Props) {
  return (
    <section className="diagnostics-panel">
      <div className="diagnostics-head">
        <div><AlertCircle size={16} /><strong>Diagnostics</strong><span>{items.length} / {total}</span></div>
        <div className="severity-tabs">
          {["", "warning", "info", "error"].map((value) => (
            <button key={value || "all"} className={severity === value ? "active" : ""} onClick={() => onSeverity(value)}>
              {value || "all"}
            </button>
          ))}
        </div>
      </div>
      <div className="diagnostic-list">
        {items.length === 0 && <div className="diagnostic-empty">No diagnostics match this filter.</div>}
        {items.slice(0, 120).map((item, index) => (
          <button
            key={`${item.code}-${item.location?.file}-${item.location?.line}-${index}`}
            disabled={!item.location}
            onClick={() => item.location && onOpenSource(item.location.file, item.location.line)}
          >
            <span className={`severity-icon severity-${item.severity}`}>{icon(item.severity)}</span>
            <code>{item.code}</code>
            <span className="diagnostic-message">{item.message}</span>
            <span className="diagnostic-location">{item.location ? `${item.location.file}:${item.location.line}` : "global"}</span>
            {item.location && <ChevronRight size={14} />}
          </button>
        ))}
      </div>
    </section>
  );
}
