import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { Search, ArrowRight, TrendingUp, Activity, Newspaper, Zap } from "lucide-react";
import { fetchStories, fetchStats, triggerIngest } from "../lib/api";
import StoryCard from "../components/StoryCard";
import DigestSubscribe from "../components/DigestSubscribe";
import TrendingSidebar from "../components/TrendingSidebar";

const SENTIMENTS = [
  { key: "all", label: "All" },
  { key: "positive", label: "Positive" },
  { key: "neutral", label: "Neutral" },
  { key: "negative", label: "Negative" },
];
const SORTS = [
  { key: "latest", label: "Latest" },
  { key: "coverage", label: "Most Coverage" },
  { key: "divided", label: "Most Divided" },
];

export default function Home() {
  const [sentiment, setSentiment] = useState("all");
  const [sort, setSort] = useState("divided");
  const [minSources, setMinSources] = useState(2);
  const [q, setQ] = useState("");
  const nav = useNavigate();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["stories", sentiment, sort, minSources],
    queryFn: () => fetchStories({ sentiment: sentiment === "all" ? undefined : sentiment, sort, min_sources: minSources }),
  });
  const { data: stats } = useQuery({ queryKey: ["stats"], queryFn: fetchStats, refetchInterval: 60_000 });

  const ingest = useMutation({
    mutationFn: triggerIngest,
    onSuccess: (r) => toast.success(`Ingestion started (${r.task_id.slice(0, 8)}…). New stories in ~2 min.`),
    onError: () => toast.error("Could not trigger ingestion."),
  });

  useEffect(() => { document.title = "PRISM · News Bias Terminal"; }, []);

  const submit = (e) => { e.preventDefault(); if (q.trim()) nav(`/search?q=${encodeURIComponent(q)}`); };

  return (
    <div className="max-w-7xl mx-auto px-6 lg:px-10 py-10 lg:py-14">
      {/* Hero */}
      <section className="mb-14 lg:mb-16">
        <div className="overline mb-4">Multi-source news intelligence</div>
        <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-slate-50 mb-5 max-w-4xl leading-[1.02]">
          See the full story.<br />
          <span className="text-slate-400">Every perspective.</span>
        </h1>
        <p className="text-slate-400 text-lg max-w-2xl leading-relaxed mb-8">
          Live analysis of how <span className="text-slate-200">{stats?.sources || "10"} publishers</span> cover the same event —
          sentiment, framing, entities, agreement — so you can form your own opinion.
        </p>

        <form onSubmit={submit} className="max-w-2xl relative mb-6">
          <Search className="w-4 h-4 text-slate-500 absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            data-testid="hero-search-input"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search any topic, event, or person..."
            className="w-full bg-slate-950 border border-slate-800 focus:border-emerald-500/50 outline-none pl-11 pr-32 py-3.5 font-mono text-sm text-slate-100 placeholder-slate-600 transition-colors duration-200"
          />
          <button data-testid="hero-search-btn" type="submit" className="absolute right-2 top-1/2 -translate-y-1/2 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-mono uppercase tracking-wider text-[11px] px-4 py-2 flex items-center gap-1.5 transition-colors duration-200">
            Search <ArrowRight className="w-3 h-3" />
          </button>
        </form>

        {/* Live stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 border border-slate-800 divide-x divide-slate-800 max-w-3xl">
          {[
            { icon: Newspaper, label: "Stories tracked", value: stats?.clusters ?? "—" },
            { icon: Activity, label: "Articles indexed", value: stats?.articles ?? "—" },
            { icon: TrendingUp, label: "Publishers", value: stats?.sources ?? "—" },
            { icon: Zap, label: "Last ingest", value: stats?.last_ingest ? relativeMin(stats.last_ingest.started_at) : "—" },
          ].map((s) => (
            <div key={s.label} className="p-5 bg-slate-950">
              <s.icon className="w-4 h-4 text-emerald-400 mb-3" strokeWidth={1.5} />
              <div className="font-display text-2xl font-bold text-slate-100">{s.value}</div>
              <div className="overline mt-1">{s.label}</div>
            </div>
          ))}
        </div>
        <button
          data-testid="trigger-ingest-btn"
          onClick={() => { ingest.mutate(); }}
          disabled={ingest.isPending}
          className="mt-4 font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500 hover:text-emerald-400 disabled:opacity-40 transition-colors duration-200"
        >
          {ingest.isPending ? "queuing…" : "→ trigger fresh ingestion"}
        </button>
      </section>

      {/* Filters */}
      <section className="mb-8 border-y border-slate-800 py-5 flex flex-wrap items-center gap-x-8 gap-y-4">
        <FilterGroup label="Sentiment">
          {SENTIMENTS.map((s) => (
            <FilterPill key={s.key} active={sentiment === s.key} onClick={() => setSentiment(s.key)} testid={`filter-sentiment-${s.key}`}>{s.label}</FilterPill>
          ))}
        </FilterGroup>
        <FilterGroup label="Sort">
          {SORTS.map((s) => (
            <FilterPill key={s.key} active={sort === s.key} onClick={() => setSort(s.key)} testid={`filter-sort-${s.key}`}>{s.label}</FilterPill>
          ))}
        </FilterGroup>
        <FilterGroup label={`Min sources: ${minSources}`}>
          <input data-testid="filter-min-sources" type="range" min={2} max={8} value={minSources} onChange={(e) => setMinSources(Number(e.target.value))} className="w-28 accent-emerald-500" />
        </FilterGroup>
      </section>

      {/* Feed + Sidebar */}
      <section className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-8">
        <div>
          <div className="flex items-baseline justify-between mb-6">
            <h2 className="font-display text-xl font-semibold text-slate-100">Live story feed</h2>
            <span className="overline">{data?.count ?? 0} events</span>
          </div>
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {[0, 1, 2, 3, 4, 5].map((i) => <div key={i} className="h-72 bg-slate-900 border border-slate-800 animate-pulse" />)}
            </div>
          ) : data?.items?.length ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {data.items.map((s, i) => <StoryCard key={s.id} story={s} index={i} />)}
            </div>
          ) : (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="border border-slate-800 bg-slate-950 p-12 text-center">
              <div className="overline mb-2">No stories match</div>
              <div className="text-slate-500">Try adjusting your filters or trigger a fresh ingestion.</div>
            </motion.div>
          )}
          <div className="mt-8">
            <DigestSubscribe />
          </div>
        </div>
        <TrendingSidebar />
      </section>
    </div>
  );
}

const relativeMin = (iso) => {
  if (!iso) return "—";
  const m = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 60000));
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
};

const FilterGroup = ({ label, children }) => (
  <div className="flex items-center gap-3">
    <span className="overline min-w-[80px]">{label}</span>
    <div className="flex items-center gap-1.5 flex-wrap">{children}</div>
  </div>
);

const FilterPill = ({ active, onClick, children, testid }) => (
  <button
    data-testid={testid}
    onClick={onClick}
    className={`font-mono text-[11px] uppercase tracking-wider px-3 py-1.5 border transition-colors duration-200 ${
      active ? "bg-slate-100 text-slate-950 border-slate-100" : "bg-transparent text-slate-400 border-slate-800 hover:border-slate-600 hover:text-slate-200"
    }`}
  >
    {children}
  </button>
);
