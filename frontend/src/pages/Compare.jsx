import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ExternalLink } from "lucide-react";
import { fetchCompare, relativeTime } from "../lib/api";
import { FrameBadge, SentimentBadge } from "../components/Badges";

export default function Compare() {
  const { id } = useParams();
  const { data, isLoading } = useQuery({ queryKey: ["compare", id], queryFn: () => fetchCompare(id) });

  if (isLoading) return <div className="max-w-7xl mx-auto px-6 py-16"><div className="h-8 bg-slate-900 animate-pulse w-1/3 mb-6" /><div className="h-96 bg-slate-900 animate-pulse" /></div>;
  if (!data) return <div className="max-w-7xl mx-auto px-6 py-16 text-slate-400">Story not found.</div>;

  const publishers = data.publishers || [];

  return (
    <div className="max-w-full mx-auto px-6 lg:px-10 py-10">
      <Link to={`/story/${id}`} className="inline-flex items-center gap-1.5 overline hover:text-slate-200 transition-colors duration-200 mb-4">
        <ArrowLeft className="w-3 h-3" /> Back to story
      </Link>
      <div className="overline mb-2">Full-text compare</div>
      <h1 className="font-display text-2xl lg:text-3xl font-bold tracking-tight text-slate-50 mb-8 max-w-4xl leading-tight">
        {data.event_label}
      </h1>

      {data.neutral_summary && (
        <div className="border border-emerald-500/30 bg-emerald-500/[0.03] p-5 mb-8 max-w-4xl">
          <div className="overline mb-2 text-emerald-400">Neutral synthesis</div>
          <p className="text-slate-100 leading-relaxed">{data.neutral_summary}</p>
        </div>
      )}

      <div className="overline mb-3">Shared facts across the coverage</div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-10 max-w-4xl">
        {["PERSON", "ORG", "GPE"].map((t) => (
          <div key={t} className="border border-slate-800 bg-slate-950 p-4">
            <div className="overline mb-2">{t === "PERSON" ? "People" : t === "ORG" ? "Orgs" : "Places"}</div>
            <div className="flex flex-wrap gap-1">
              {(data.shared_facts[t] || []).slice(0, 8).map((e) => (
                <span key={e.name} className="font-mono text-[11px] bg-slate-900 border border-slate-800 px-2 py-0.5 text-slate-300">
                  {e.name} <span className="text-slate-600">×{e.articles_mentioning}</span>
                </span>
              ))}
              {!(data.shared_facts[t] || []).length && <span className="font-mono text-[10px] text-slate-600">None</span>}
            </div>
          </div>
        ))}
      </div>

      <div className="overline mb-4">Full articles side-by-side</div>
      <div data-testid="compare-columns" className="overflow-x-auto pb-4">
        <div className="flex gap-4" style={{ minWidth: `${publishers.length * 380}px` }}>
          {publishers.map((p) => (
            <article key={p.source} data-testid={`compare-col-${p.source}`} className="w-[360px] flex-shrink-0 border border-slate-800 bg-slate-950">
              <header className="sticky top-16 z-10 bg-slate-950 border-b border-slate-800 p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="font-display text-base font-semibold text-slate-100">{p.source}</div>
                  <a href={p.url} target="_blank" rel="noopener noreferrer" className="text-slate-500 hover:text-emerald-400 transition-colors duration-200"><ExternalLink className="w-3.5 h-3.5" /></a>
                </div>
                <div className="font-mono text-[10px] text-slate-600 mb-2">{relativeTime(p.published_at)}</div>
                <h3 className="font-display text-sm font-semibold text-slate-100 leading-snug tracking-tight mb-2">{p.headline}</h3>
                <div className="flex flex-wrap gap-1.5">
                  <SentimentBadge label={p.sentiment_label} score={p.sentiment_score} />
                  <FrameBadge frame={p.primary_frame} />
                </div>
              </header>
              <div className="p-4 max-h-[600px] overflow-y-auto">
                <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">{p.full_content || p.excerpt}</p>
              </div>
            </article>
          ))}
        </div>
      </div>
    </div>
  );
}
