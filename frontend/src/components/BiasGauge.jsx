import { motion } from "framer-motion";

export default function BiasGauge({ score = 0 }) {
  // score: 0 (consensus) -> 1 (divided)
  const pct = Math.max(0, Math.min(1, score));
  const angle = -90 + pct * 180;
  const color = pct > 0.6 ? "#f43f5e" : pct > 0.3 ? "#facc15" : "#10b981";

  return (
    <div className="flex flex-col items-center">
      <svg viewBox="0 0 200 120" className="w-full max-w-[220px]">
        <defs>
          <linearGradient id="gauge" x1="0" x2="1">
            <stop offset="0" stopColor="#10b981" />
            <stop offset="0.5" stopColor="#facc15" />
            <stop offset="1" stopColor="#f43f5e" />
          </linearGradient>
        </defs>
        <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="#1e293b" strokeWidth="14" strokeLinecap="butt" />
        <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="url(#gauge)" strokeWidth="14" strokeDasharray={`${pct * 251.3} 300`} strokeLinecap="butt" />
        <motion.g initial={{ rotate: -90 }} animate={{ rotate: angle }} style={{ originX: "100px", originY: "100px" }} transition={{ duration: 0.9, ease: "easeOut" }}>
          <line x1="100" y1="100" x2="100" y2="34" stroke={color} strokeWidth="3" />
          <circle cx="100" cy="100" r="6" fill={color} />
        </motion.g>
        <text x="100" y="118" textAnchor="middle" fill="#64748b" fontFamily="JetBrains Mono" fontSize="9">CONSENSUS ← → DIVIDED</text>
      </svg>
      <div className="text-center mt-2">
        <div className="font-display text-3xl font-bold text-slate-100">{Math.round(pct * 100)}%</div>
        <div className="overline">frame divergence</div>
      </div>
    </div>
  );
}
