import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { FrameBadge } from "./Badges";
import { relativeTime } from "../lib/api";
import { Users, Sparkles, ArrowUpRight } from "lucide-react";

export default function StoryCard({ story, index = 0 }) {
  const total = (story.sentiment_distribution?.positive || 0) + (story.sentiment_distribution?.neutral || 0) + (story.sentiment_distribution?.negative || 0);
  const p = total ? Math.round(((story.sentiment_distribution?.positive || 0) / total) * 100) : 0;
  const n = total ? Math.round(((story.sentiment_distribution?.neutral || 0) / total) * 100) : 0;
  const ng = total ? 100 - p - n : 0;
  const divided = Math.round((story.frame_diversity_score || 0) * 100);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.35 }}
    >
      <Link
        to={`/story/${story.id}`}
        data-testid={`story-card-${story.id}`}
        className="group block bg-slate-950 border border-slate-800 hover:border-slate-600 transition-colors duration-200 h-full"
      >
        <div className="p-5 flex flex-col h-full">
          <div className="flex items-center justify-between mb-3">
            <span className="overline">{story.topic || "Story"}</span>
            <span className="font-mono text-[10px] text-slate-600">{relativeTime(story.last_updated_at)}</span>
          </div>

          <h3 className="font-display text-[17px] font-semibold text-slate-100 leading-snug tracking-tight mb-4 group-hover:text-white transition-colors duration-200">
            {story.event_label}
          </h3>

          {/* Sentiment mini-bar */}
          <div className="mb-3">
            <div className="flex h-1.5 w-full overflow-hidden">
              <div style={{ width: `${p}%`, background: "#10b981" }} />
              <div style={{ width: `${n}%`, background: "#60a5fa" }} />
              <div style={{ width: `${ng}%`, background: "#f43f5e" }} />
            </div>
            <div className="flex justify-between mt-1.5 font-mono text-[10px] text-slate-500">
              <span>+{p}%</span>
              <span>·{n}%</span>
              <span>−{ng}%</span>
            </div>
          </div>

          {/* Publishers */}
          <div className="flex flex-wrap gap-1.5 mb-4">
            {(story.publisher_list || []).slice(0, 5).map((s) => (
              <span key={s} className="font-mono text-[10px] text-slate-400 bg-slate-900 border border-slate-800 px-1.5 py-0.5 uppercase tracking-wider">
                {s}
              </span>
            ))}
            {story.publisher_list?.length > 5 && (
              <span className="font-mono text-[10px] text-slate-500 px-1.5 py-0.5">+{story.publisher_list.length - 5}</span>
            )}
          </div>

          {/* Frames */}
          <div className="flex flex-wrap gap-1.5 mb-5">
            {(story.primary_frames || []).slice(0, 2).map(([frame]) => (
              <FrameBadge key={frame} frame={frame} />
            ))}
          </div>

          <div className="mt-auto flex items-center justify-between pt-4 border-t border-slate-900">
            <div className="flex items-center gap-4 font-mono text-[11px] text-slate-500">
              <span className="flex items-center gap-1.5"><Users className="w-3 h-3" />{story.article_count} sources</span>
              <span className="flex items-center gap-1.5"><Sparkles className="w-3 h-3" />{divided}% divided</span>
            </div>
            <ArrowUpRight className="w-4 h-4 text-slate-600 group-hover:text-emerald-400 transition-colors duration-200" />
          </div>
        </div>
      </Link>
    </motion.div>
  );
}
