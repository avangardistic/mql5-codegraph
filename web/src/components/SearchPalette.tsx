import { Search, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type GraphNode } from "../api";

type Props = { ready: boolean; onFocus: (node: GraphNode) => void };

export function SearchPalette({ ready, onFocus }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<GraphNode[]>([]);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!ready || query.trim().length < 2) {
      setResults([]);
      return;
    }
    const timer = window.setTimeout(() => {
      api.query(query.trim()).then(({ results }) => {
        setResults(results);
        setOpen(true);
      }).catch(() => setResults([]));
    }, 180);
    return () => window.clearTimeout(timer);
  }, [query, ready]);

  return (
    <div className="search-palette">
      <Search size={17} />
      <input
        value={query}
        disabled={!ready}
        onChange={(event) => setQuery(event.target.value)}
        onFocus={() => results.length && setOpen(true)}
        onKeyDown={(event) => {
          if (event.key === "Escape") setOpen(false);
          if (event.key === "Enter" && results[0]) {
            onFocus(results[0]);
            setOpen(false);
          }
        }}
        placeholder={ready ? "Search symbols, methods, files…" : "Analyze a repository to search"}
        aria-label="Search code graph"
      />
      {query && <button onClick={() => { setQuery(""); setOpen(false); }} aria-label="Clear search"><X size={15} /></button>}
      {open && results.length > 0 && (
        <div className="search-results">
          <div className="search-result-meta">{results.length} matches · Enter selects first</div>
          {results.slice(0, 12).map((node) => (
            <button key={node.id} onClick={() => { onFocus(node); setOpen(false); }}>
              <span className={`kind-dot kind-${node.kind}`} />
              <span><strong>{node.name}</strong><small>{node.qualified_name}</small></span>
              <em>{node.kind.replaceAll("_", " ")}</em>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
