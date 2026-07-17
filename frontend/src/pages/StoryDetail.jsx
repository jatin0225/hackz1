import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowLeft, ExternalLink, Sparkles, Users, Clock, Layers } from "lucide-react";
import { fetchStory, relativeTime, FRAME_META } from "../lib/api";
import { FrameBadge, SentimentBadge, EntityChip } from "../components/Badges";
import SentimentBarChart from "../components/SentimentBarChart";
import FrameRadar from "../components/FrameRadar";
import BiasGauge from "../components/BiasGauge";

export default function StoryDetail() {
  const { id } = useParams();
  const { data, isLoading, error } = useQuery({
    queryKey: ["story", id],
    queryFn: () => fetchStory(id),
  });

  if (isLoading) return <div className="max-w-7xl mx-auto px-6 lg:px-10 py-16"><div className="animate-pulse space-y-4"><div className="h-8 bg-slate-900 w-1/3" /><div className="h-16 bg-slate-900 w-2/3" /><div className="h-64 bg-slate-900" /></div></div>;
  if (error || !data) return <div className="max-w-7xl mx-auto px-6 lg:px-10 py-16"><div className="text-slate-400">Story not found.</div></div>;

  const { cluster, articles, sentiment_distribution, entities_by_type, timeline } = data;
  const dist = sentiment_distribution;
  const total = dist.positive + dist.neutral + dist.negative;
  const spanHours = Math.max(1, Math.round((new Date(cluster.last_updated_at) - new Date(cluster.first_seen_at)) / 3600000));

  return (
    <div className="max-w-7xl mx-auto px-6 lg:px-10 py-10">
      {/* Breadcrumb */}
      <Link to="/" data-testid="back-to-feed" className="inline-flex items-center gap-1.5 overline hover:text-slate-200 transition-colors duration-200 mb-6">
        <ArrowLeft className="w-3 h-3" /> Back to feed
      </Link>

      {/* Section 1 — Header */}
      <motion.section initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="mb-10">
        <div className="overline mb-3">{cluster.topic}</div>
        <h1 data-testid="story-title" className="font-display text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-slate-50 leading-[1.05] max-w-4xl mb-6">
          {cluster.event_label}
        </h1>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 font-mono text-xs text-slate-500 mb-8">
          <span className="flex items-center gap-1.5"><Clock className="w-3 h-3" />First reported {relativeTime(cluster.first_seen_at)}</span>
          <span className="flex items-center gap-1.5"><Users className="w-3 h-3" />{cluster.article_count} publishers</span>
          <span className="flex items-center gap-1.5"><Layers className="w-3 h-3" />Updated {relativeTime(cluster.last_updated_at)}</span>
        </div>

        {/* Neutral summary card */}
        <div className="border border-emerald-500/30 bg-emerald-500/[0.03] p-6 lg:p-7 relative">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
            <span className="overline text-emerald-400">What actually happened · AI Neutral Synthesis</span>
          </div>
          <p data-testid="neutral-summary" className="text-slate-100 text-lg leading-relaxed font-light">
            {cluster.neutral_summary || "Generating a neutral summary from all sources..."}
          </p>
          <div className="mt-4 overline text-slate-600">Synthesized from {cluster.article_count} publisher reports</div>
        </div>
      </motion.section>

      {/* Section 2 — At a glance stats */}
      <section className="grid grid-cols-2 lg:grid-cols-4 border border-slate-800 divide-x divide-y lg:divide-y-0 divide-slate-800 mb-14">
        <StatBlock label="Sources covering" value={cluster.article_count} sub={cluster.publisher_list?.slice(0, 3).join(" · ")} />
        <StatBlock label="Overall sentiment" custom={
          <div className="mt-2">
            <div className="flex h-2 w-full overflow-hidden mb-2">
              {total > 0 && <>
                <div style={{ width: `${(dist.positive / total) * 100}%`, background: "#10b981" }} />
                <div style={{ width: `${(dist.neutral / total) * 100}%`, background: "#60a5fa" }} />
                <div style={{ width: `${(dist.negative / total) * 100}%`, background: "#f43f5e" }} />
              </>}
            </div>
            <div className="font-mono text-[10px] text-slate-500 flex justify-between">
              <span className="text-emerald-400">+{dist.positive}</span>
              <span className="text-blue-400">·{dist.neutral}</span>
              <span className="text-rose-400">−{dist.negative}</span>
            </div>
          </div>
        } />
        <StatBlock label="Frame divergence" value={`${Math.round((cluster.frame_diversity_score || 0) * 100)}%`} sub={cluster.frame_diversity_score > 0.5 ? "High disagreement" : "Broad consensus"} />
        <StatBlock label="Coverage window" value={`${spanHours}h`} sub={`${timeline?.length || 0} articles`} />
      </section>

      {/* Section 3 — Publisher perspectives */}
      <section className="mb-14">
        <SectionHeader kicker="Section 03" title="How each publisher covered it" subtitle="Same event, different angles" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {articles.map((a) => (
            <PublisherCard key={a.source} article={a} />
          ))}
        </div>
      </section>

      {/* Section 4 — Sentiment chart */}
      <section className="mb-14">
        <SectionHeader kicker="Section 04" title="Sentiment by publisher" subtitle="Scored on VADER polarity, −1 (negative) to +1 (positive)" />
        <div className="border border-slate-800 bg-slate-950 p-6">
          <SentimentBarChart data={articles} />
        </div>
      </section>

      {/* Section 5 — Frame analysis */}
      <section className="mb-14">
        <SectionHeader kicker="Section 05" title="How each publisher frames the story" subtitle="Framing = the angle a publisher emphasises. Same facts, different frames." />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 border border-slate-800 bg-slate-950 p-6">
          <div className="lg:col-span-2">
            <FrameRadar publishers={articles} />
          </div>
          <div className="space-y-3 lg:border-l lg:border-slate-800 lg:pl-6">
            <div className="overline mb-2">Divergence gauge</div>
            <BiasGauge score={cluster.frame_diversity_score || 0} />
          </div>
        </div>
      </section>

      {/* Section 6 — Entities */}
      <section className="mb-14">
        <SectionHeader kicker="Section 06" title="Key people, organizations & places" subtitle="Named entities mentioned across the coverage" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { type: "PERSON", label: "People", color: "text-blue-400" },
            { type: "ORG", label: "Organizations", color: "text-purple-400" },
            { type: "GPE", label: "Places", color: "text-emerald-400" },
          ].map((g) => (
            <div key={g.type} className="border border-slate-800 bg-slate-950 p-5">
              <div className={`overline mb-4 ${g.color}`}>{g.label}</div>
              <div className="flex flex-wrap gap-1.5">
                {(entities_by_type[g.type] || []).slice(0, 12).map((e) => (
                  <EntityChip key={e.name} type={g.type} name={e.name} mentions={e.mentions} />
                ))}
                {(!entities_by_type[g.type] || entities_by_type[g.type].length === 0) && (
                  <span className="font-mono text-xs text-slate-600">No {g.label.toLowerCase()} detected</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

const StatBlock = ({ label, value, sub, custom }) => (
  <div className="p-5 bg-slate-950">
    <div className="overline mb-3">{label}</div>
    {custom ? custom : <div className="font-display text-2xl font-bold text-slate-100 leading-none">{value}</div>}
    {sub && !custom && <div className="mt-2 font-mono text-[10px] text-slate-500 truncate">{sub}</div>}
  </div>
);

const SectionHeader = ({ kicker, title, subtitle }) => (
  <div className="mb-6">
    <div className="overline mb-2">{kicker}</div>
    <h2 className="font-display text-2xl font-semibold text-slate-100 tracking-tight">{title}</h2>
    {subtitle && <p className="text-slate-500 text-sm mt-1.5">{subtitle}</p>}
  </div>
);

const PublisherCard = ({ article }) => {
  const meta = FRAME_META[article.primary_frame] || {};
  return (
    <div data-testid={`publisher-card-${article.source}`} className="border border-slate-800 bg-slate-950 hover:border-slate-700 transition-colors duration-200">
      <div className="p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <img src={`https://www.google.com/s2/favicons?domain=${article.url.split("/")[2]}&sz=32`} alt="" className="w-4 h-4 opacity-80" />
            <span className="font-display text-sm font-semibold text-slate-100 tracking-tight">{article.source}</span>
          </div>
          <span className="font-mono text-[10px] text-slate-600">{relativeTime(article.published_at)}</span>
        </div>
        <h3 className="font-display text-lg font-semibold text-slate-100 leading-snug mb-3 tracking-tight">{article.headline}</h3>
        <div className="flex flex-wrap gap-1.5 mb-3">
          <SentimentBadge label={article.sentiment_label} score={article.sentiment_score} />
          <FrameBadge frame={article.primary_frame} />
        </div>
        <p className="text-slate-400 text-sm leading-relaxed mb-4">{article.excerpt}</p>
        <div className="flex items-center justify-between pt-3 border-t border-slate-900">
          <div className="flex flex-wrap gap-1">
            {article.entities?.slice(0, 3).map((e, i) => (
              <span key={i} className="font-mono text-[10px] text-slate-500 bg-slate-900 border border-slate-800 px-1.5 py-0.5">{e.name}</span>
            ))}
          </div>
          <a
            data-testid={`read-full-${article.source}`}
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-[11px] text-emerald-400 hover:text-emerald-300 uppercase tracking-wider flex items-center gap-1 transition-colors duration-200"
          >
            Source <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
      {/* accent stripe */}
      <div className="h-0.5" style={{ background: meta.color || "#334155" }} />
    </div>
  );
};
