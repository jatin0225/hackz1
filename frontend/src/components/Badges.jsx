import { FRAME_META } from "../lib/api";

export function FrameBadge({ frame, size = "sm" }) {
  const meta = FRAME_META[frame] || { label: frame, bg: "bg-slate-800", text: "text-slate-300", border: "border-slate-700" };
  const sizeCls = size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs";
  return (
    <span
      data-testid={`frame-badge-${frame}`}
      className={`inline-flex items-center font-mono uppercase tracking-wider border ${meta.bg} ${meta.text} ${meta.border} ${sizeCls} rounded-sm`}
    >
      {meta.label}
    </span>
  );
}

export function SentimentBadge({ label, score, showScore = true }) {
  const config = {
    positive: { text: "text-emerald-300", bg: "bg-emerald-500/10", border: "border-emerald-500/30" },
    negative: { text: "text-rose-300", bg: "bg-rose-500/10", border: "border-rose-500/30" },
    neutral: { text: "text-blue-300", bg: "bg-blue-500/10", border: "border-blue-500/30" },
  }[label] || { text: "text-slate-300", bg: "bg-slate-800", border: "border-slate-700" };
  return (
    <span
      data-testid={`sentiment-badge-${label}`}
      className={`inline-flex items-center gap-1.5 font-mono uppercase tracking-wider text-[10px] border ${config.bg} ${config.text} ${config.border} px-2 py-0.5 rounded-sm`}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: label === "positive" ? "#10b981" : label === "negative" ? "#f43f5e" : "#60a5fa" }} />
      {label}
      {showScore && score !== undefined && (
        <span className="text-slate-500 font-medium">{score > 0 ? "+" : ""}{score.toFixed(2)}</span>
      )}
    </span>
  );
}

export function EntityChip({ type, name, mentions }) {
  const c = { PERSON: "text-blue-300", ORG: "text-purple-300", GPE: "text-emerald-300", MONEY: "text-yellow-300" }[type] || "text-slate-300";
  return (
    <span data-testid={`entity-chip-${name}`} className={`inline-flex items-center gap-1.5 font-mono text-xs bg-slate-900 border border-slate-800 px-2 py-1 ${c}`}>
      {name}
      {mentions && <span className="text-slate-600">×{mentions}</span>}
    </span>
  );
}
