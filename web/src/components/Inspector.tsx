import { ArrowDownLeft, ArrowUpRight, Braces, FileCode2, GitBranch, Route, ShieldCheck } from "lucide-react";
import { useMemo, useState } from "react";
import { api, type GraphEdge, type GraphNode, type Projection } from "../api";

type Props = {
  node: GraphNode | null;
  projection: Projection | null;
  onFocusGraph: (nodes: GraphNode[], edges: GraphEdge[]) => void;
  onOpenSource: (file: string, line: number) => void;
};

export function Inspector({ node, projection, onFocusGraph, onOpenSource }: Props) {
  const [impact, setImpact] = useState<Array<{ node: GraphNode; distance: number }> | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const edges = useMemo(() => {
    if (!node || !projection) return { incoming: [], outgoing: [] };
    return {
      incoming: projection.edges.filter((edge) => edge.target === node.id),
      outgoing: projection.edges.filter((edge) => edge.source === node.id),
    };
  }, [node, projection]);

  if (!node) {
    return (
      <aside className="inspector panel-empty">
        <Braces size={32} />
        <strong>Evidence inspector</strong>
        <p>Select a node to inspect its source, relationships, context, and upstream blast radius.</p>
      </aside>
    );
  }

  const loadContext = async () => {
    setBusy(true); setError(null); setImpact(null);
    try {
      const context = await api.context(node.id, 1);
      onFocusGraph(context.nodes, context.edges);
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { setBusy(false); }
  };

  const loadImpact = async () => {
    setBusy(true); setError(null);
    try {
      const result = await api.impact(node.id, 3);
      setImpact(result.results);
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
    finally { setBusy(false); }
  };

  const attributes = Object.entries(node.attributes).filter(([, value]) => value !== null);
  return (
    <aside className="inspector">
      <div className="eyebrow">Selected evidence</div>
      <div className="node-heading">
        <span className={`node-icon kind-${node.kind}`}><Braces size={17} /></span>
        <div><h2>{node.name}</h2><span>{node.kind.replaceAll("_", " ")}</span></div>
      </div>
      <code className="qualified-name">{node.qualified_name}</code>

      {node.location && (
        <button className="source-link" onClick={() => onOpenSource(node.location!.file, node.location!.line)}>
          <FileCode2 size={15} />
          <span>{node.location.file}<small>line {node.location.line}:{node.location.column}</small></span>
          <ArrowUpRight size={14} />
        </button>
      )}

      <div className="inspector-actions">
        <button onClick={loadContext} disabled={busy}><GitBranch size={15} /> Focus context</button>
        <button onClick={loadImpact} disabled={busy}><Route size={15} /> Trace impact</button>
      </div>
      {error && <div className="inline-error">{error}</div>}

      <section className="relation-summary">
        <div><ArrowDownLeft size={14} /><strong>{edges.incoming.length}</strong><span>incoming</span></div>
        <div><ArrowUpRight size={14} /><strong>{edges.outgoing.length}</strong><span>outgoing</span></div>
        <div><ShieldCheck size={14} /><strong>{Math.round(Math.min(...[...edges.incoming, ...edges.outgoing].map((e) => e.confidence), 1) * 100)}%</strong><span>min confidence</span></div>
      </section>

      {impact && (
        <section className="impact-results">
          <div className="section-title"><Route size={14} /> Upstream impact <span>{impact.length}</span></div>
          {impact.length === 0 && <p>No upstream dependencies found within depth 3.</p>}
          {impact.slice(0, 24).map((item) => (
            <button key={item.node.id} onClick={() => onFocusGraph([item.node], [])}>
              <span className={`kind-dot kind-${item.node.kind}`} />
              <span><strong>{item.node.name}</strong><small>{item.node.qualified_name}</small></span>
              <em>d{item.distance}</em>
            </button>
          ))}
        </section>
      )}

      <section className="property-list">
        <div className="section-title">Properties <span>{attributes.length}</span></div>
        {attributes.map(([key, value]) => (
          <div key={key}><span>{key.replaceAll("_", " ")}</span><code>{String(value)}</code></div>
        ))}
      </section>

      <section className="edge-list">
        <div className="section-title">Visible relationships <span>{edges.incoming.length + edges.outgoing.length}</span></div>
        {[...edges.incoming, ...edges.outgoing].slice(0, 16).map((edge) => (
          <div key={edge.id}>
            <span className={`edge-origin origin-${edge.origin}`}>{edge.origin}</span>
            <code>{edge.relationship}</code>
            <em>{Math.round(edge.confidence * 100)}%</em>
          </div>
        ))}
      </section>
    </aside>
  );
}
