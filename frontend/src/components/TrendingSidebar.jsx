import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchTrending } from "../lib/api";
import { TrendingUp, Users, Flame } from "lucide-react";

export default function TrendingSidebar() {
  const { data, isLoading } = useQuery({ queryKey: ["trending"], queryFn: fetchTrending });

  if (isLoading) return <aside className="space-y-4"><div className="h-40 bg-slate-900 border border-slate-800 animate-pulse" /><div className="h-40 bg-slate-900 border border-slate-800 animate-pulse" /></aside>;
  if (!data) return null;
  const { top_entities = [], most_divided = [], most_covered = [] } = data;
  const persons = top_entities.filter((e) => e.type === "PERSON").slice(0, 6);
  const orgs = top_entities.filter((e) => e.type === "ORG").slice(0, 6);
  const places = top_entities.filter((e) => e.type === "GPE").slice(0, 6);

  return (
    <aside data-testid="trending-sidebar" className="space-y-6">
      <Panel icon={<Flame className="w-3.5 h-3.5 text-rose-400" strokeWidth={1.5} />} title="Most divided today" kicker="Highest frame divergence">
        <ul className="divide-y divide-slate-900">
          {most_divided.slice(0, 4).map((s) => (
            <li key={s.id} className="py-2.5">
              <Link to={`/story/${s.id}`} data-testid={`trending-divided-${s.id}`} className="group block">
                <div className="font-display text-sm font-medium text-slate-200 group-hover:text-slate-50 leading-snug tracking-tight line-clamp-2 transition-colors duration-200">{s.event_label}</div>
                <div className="font-mono text-[10px] text-slate-500 mt-1">{Math.round((s.frame_diversity_score || 0) * 100)}% divergence &middot; {s.article_count} sources</div>
              </Link>
            </li>
          ))}
        </ul>
      </Panel>

      <Panel icon={<TrendingUp className="w-3.5 h-3.5 text-emerald-400" strokeWidth={1.5} />} title="Most covered" kicker="Most publishers today">
        <ul className="divide-y divide-slate-900">
          {most_covered.slice(0, 4).map((s) => (
            <li key={s.id} className="py-2.5">
              <Link to={`/story/${s.id}`} className="group block">
                <div className="font-display text-sm font-medium text-slate-200 group-hover:text-slate-50 leading-snug tracking-tight line-clamp-2 transition-colors duration-200">{s.event_label}</div>
                <div className="font-mono text-[10px] text-slate-500 mt-1">{s.article_count} publishers</div>
              </Link>
            </li>
          ))}
        </ul>
      </Panel>

      <Panel icon={<Users className="w-3.5 h-3.5 text-blue-400" strokeWidth={1.5} />} title="Trending entities" kicker="Last 48 hours">
        <EntityGroup label="People" color="text-blue-400" items={persons} />
        <EntityGroup label="Organizations" color="text-purple-400" items={orgs} />
        <EntityGroup label="Places" color="text-emerald-400" items={places} />
      </Panel>
    </aside>
  );
}

const Panel = ({ icon, title, kicker, children }) => (
  <div className="border border-slate-800 bg-slate-950 p-4">
    <div className="flex items-center gap-2 mb-2">
      {icon}
      <div className="overline">{title}</div>
    </div>
    <div className="font-mono text-[10px] text-slate-600 mb-3">{kicker}</div>
    {children}
  </div>
);

const EntityGroup = ({ label, color, items }) =>
  items.length ? (
    <div className="mb-3 last:mb-0">
      <div className={`font-mono text-[10px] uppercase tracking-wider mb-1.5 ${color}`}>{label}</div>
      <div className="flex flex-wrap gap-1">
        {items.map((e) => (
          <span key={e.name} className="font-mono text-[10px] bg-slate-900 border border-slate-800 px-1.5 py-0.5 text-slate-300">
            {e.name} <span className="text-slate-600">×{e.mentions}</span>
          </span>
        ))}
      </div>
    </div>
  ) : null;
