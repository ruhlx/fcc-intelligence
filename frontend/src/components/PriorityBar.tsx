/** Renders a 0–100 priority score as a small labelled meter. */
export function PriorityBar({ score }: { score: number }) {
  const pct = Math.max(0, Math.min(100, score));
  const tone = pct >= 70 ? "high" : pct >= 40 ? "mid" : "low";
  return (
    <div className="priority" title={`Priority ${pct}/100`}>
      <div className="priority__track">
        <div className={`priority__fill priority__fill--${tone}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="priority__value">{pct}</span>
    </div>
  );
}
