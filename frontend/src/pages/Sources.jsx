import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip, PieChart, Pie, Cell, Legend } from "recharts";
import { fetchSources, fetchSource, FRAME_META, relativeTime } from "../lib/api";
import { FrameBadge, SentimentBadge } from "../components/Badges";
import { ArrowLeft, ExternalLink } from "lucide-react";

export function Sources() {
  const { data, isLoading } = useQuery({ queryKey: ["sources"], queryFn: fetchSources });

  return (
    <div className="max-w-7xl mx-auto px-6 lg:px-10 py-12">
      <div className="overline mb-3">Publisher intelligence</div>
      <h1 className="font-display text-3xl lg:text-4xl font-bold text-slate-50 tracking-tight mb-3">Sources</h1>
      <p className="text-slate-400 max-w-2xl mb-10">Publisher bias profiles across every article we&rsquo;ve indexed. Click any card to see how a source&rsquo;s sentiment and framing evolve.</p>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[0, 1, 2, 3, 4, 5].map((i) => <div key={i} className="h-56 bg-slate-900 border border-slate-800 animate-pulse" />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {(data?.items || []).map((s, i) => <SourceCard key={s.source_name} s={s} i={i} />)}
        </div>
      )}
    </div>
  );
}

const SourceCard = ({ s, i }) => {
  const dist = s.sentiment_distribution || { positive: 0, neutral: 0, negative: 0 };
  const total = dist.positive + dist.neutral + dist.negative || 1;
  const p = (dist.positive / total) * 100;
  const n = (dist.neutral / total) * 100;
  const ng = 100 - p - n;
  const sentColor = s.avg_sentiment > 0.15 ? "#10b981" : s.avg_sentiment < -0.15 ? "#f43f5e" : "#60a5fa";
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}>
      <Link to={`/sources/${encodeURIComponent(s.source_name)}`} data-testid={`source-card-${s.source_name}`} className="block border border-slate-800 hover:border-slate-600 bg-slate-950 p-5 transition-colors duration-200 h-full">
        <div className="flex items-center justify-between mb-4">
          <div className="font-display text-lg font-semibold text-slate-100 tracking-tight">{s.source_name}</div>
          <div className="font-mono text-[10px] text-slate-500">{s.total_articles} arts</div>
        </div>
        <div className="mb-4">
          <div className="overline mb-1.5">Avg sentiment</div>
          <div className="flex items-baseline gap-2">
            <span className="font-display text-2xl font-bold" style={{ color: sentColor }}>{s.avg_sentiment > 0 ? "+" : ""}{Number(s.avg_sentiment).toFixed(2)}</span>
            <span className="font-mono text-[10px] text-slate-500">on VADER polarity</span>
          </div>
        </div>
        <div className="mb-4">
          <div className="flex h-1.5 w-full overflow-hidden">
            <div style={{ width: `${p}%`, background: "#10b981" }} />
            <div style={{ width: `${n}%`, background: "#60a5fa" }} />
            <div style={{ width: `${ng}%`, background: "#f43f5e" }} />
          </div>
          <div className="flex justify-between mt-1 font-mono text-[10px] text-slate-500">
            <span>+{dist.positive}</span><span>·{dist.neutral}</span><span>−{dist.negative}</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {(s.top_frames || []).slice(0, 3).map(([f]) => <FrameBadge key={f} frame={f} />)}
        </div>
      </Link>
    </motion.div>
  );
};

export function SourceDetail() {
  const { name } = useParams();
  const { data, isLoading } = useQuery({ queryKey: ["source", name], queryFn: () => fetchSource(name) });

  if (isLoading) return <div className="max-w-6xl mx-auto px-6 py-16"><div className="h-8 bg-slate-900 animate-pulse w-1/3 mb-4" /><div className="h-64 bg-slate-900 animate-pulse" /></div>;
  if (!data) return <div className="max-w-6xl mx-auto px-6 py-16 text-slate-400">Source not found.</div>;

  const { stats, recent_articles = [], sentiment_timeline = [] } = data;
  const framesData = (stats.top_frames || []).map(([frame, count]) => ({ name: (FRAME_META[frame] || {}).label || frame, value: count, color: (FRAME_META[frame] || {}).color || "#94a3b8" }));

  return (
    <div className="max-w-6xl mx-auto px-6 lg:px-10 py-10">
      <Link to="/sources" className="inline-flex items-center gap-1.5 overline hover:text-slate-200 transition-colors duration-200 mb-6">
        <ArrowLeft className="w-3 h-3" /> Back to sources
      </Link>
      <div className="overline mb-3">Publisher deep-dive</div>
      <h1 className="font-display text-4xl lg:text-5xl font-bold tracking-tight text-slate-50 mb-10">{stats.source_name}</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 border border-slate-800 divide-x lg:divide-y-0 divide-y divide-slate-800 mb-12">
        <Stat label="Articles indexed" value={stats.total_articles} />
        <Stat label="Avg sentiment" value={`${stats.avg_sentiment > 0 ? "+" : ""}${stats.avg_sentiment}`} />
        <Stat label="Top frame" value={(FRAME_META[(stats.top_frames || [])[0]?.[0]] || {}).label || "—"} />
        <Stat label="Last update" value={relativeTime(stats.last_updated)} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-12">
        <div className="border border-slate-800 bg-slate-950 p-6">
          <div className="overline mb-3">Sentiment over time (last 30 days)</div>
          {sentiment_timeline.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={sentiment_timeline}>
                <XAxis dataKey="date" stroke="#334155" tick={{ fill: "#64748b", fontSize: 10, fontFamily: "JetBrains Mono" }} />
                <YAxis domain={[-1, 1]} stroke="#334155" tick={{ fill: "#64748b", fontSize: 10, fontFamily: "JetBrains Mono" }} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", fontFamily: "JetBrains Mono", fontSize: 11, color: "#e2e8f0" }} />
                <Line type="monotone" dataKey="avg_sentiment" stroke="#10b981" strokeWidth={2} dot={{ fill: "#10b981", r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          ) : <div className="text-slate-500 text-sm h-[220px] grid place-items-center">Not enough recent data.</div>}
        </div>
        <div className="border border-slate-800 bg-slate-950 p-6">
          <div className="overline mb-3">Frame distribution</div>
          {framesData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={framesData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={40} outerRadius={80} paddingAngle={2}>
                  {framesData.map((d, i) => <Cell key={i} fill={d.color} />)}
                </Pie>
                <Legend wrapperStyle={{ fontFamily: "JetBrains Mono", fontSize: 10, color: "#94a3b8" }} />
                <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", fontFamily: "JetBrains Mono", fontSize: 11, color: "#e2e8f0" }} />
              </PieChart>
            </ResponsiveContainer>
          ) : <div className="text-slate-500 text-sm h-[220px] grid place-items-center">No frame data.</div>}
        </div>
      </div>

      <div className="overline mb-4">Recent articles</div>
      <div className="border border-slate-800 bg-slate-950 divide-y divide-slate-900">
        {recent_articles.map((a) => (
          <div key={a.id} className="p-4 flex items-start gap-4">
            <div className="flex-1 min-w-0">
              <a href={a.url} target="_blank" rel="noopener noreferrer" className="font-display text-slate-100 font-medium leading-snug tracking-tight hover:text-emerald-300 flex items-start gap-1 transition-colors duration-200">
                <span className="line-clamp-2">{a.title}</span>
                <ExternalLink className="w-3 h-3 mt-1 text-slate-600 flex-shrink-0" />
              </a>
              <div className="mt-2 flex flex-wrap gap-1.5 items-center">
                <SentimentBadge label={a.sentiment_label} score={a.sentiment_score} />
                {a.primary_frame && <FrameBadge frame={a.primary_frame} />}
                <span className="font-mono text-[10px] text-slate-600">{relativeTime(a.published_at)}</span>
                {a.cluster_id && <Link to={`/story/${a.cluster_id}`} className="font-mono text-[10px] text-emerald-400 hover:text-emerald-300 transition-colors duration-200">→ in cluster</Link>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const Stat = ({ label, value }) => (
  <div className="p-5 bg-slate-950">
    <div className="overline mb-2">{label}</div>
    <div className="font-display text-xl font-bold text-slate-100">{value}</div>
  </div>
);
