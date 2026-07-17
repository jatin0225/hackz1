import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, Check, AlertTriangle, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { api } from "../lib/api";

const STEP_LABELS = {
  ingest: "Fetching RSS feeds",
  enrich: "Enriching with LLM (sentiment · frame · entities)",
  cluster: "Clustering articles",
  aggregate: "Building story clusters",
  summarize: "Generating neutral summaries",
  publisher_stats: "Recomputing publisher bias",
};

const stepBase = (name) => {
  const key = name.split(" ")[0];
  return STEP_LABELS[key] || name;
};

export default function IngestProgress({ taskId, onComplete }) {
  const [task, setTask] = useState(null);
  const [dismissed, setDismissed] = useState(false);
  const qc = useQueryClient();

  useEffect(() => {
    if (!taskId || dismissed) return;
    let alive = true;
    let notified = false;
    const poll = async () => {
      try {
        const { data } = await api.get(`/ingest/status/${taskId}`);
        if (!alive) return;
        setTask(data);
        if ((data.status === "completed" || data.status === "failed") && !notified) {
          notified = true;
          if (data.status === "completed") {
            toast.success(`Ingest complete · ${data.new_articles || 0} new article${data.new_articles === 1 ? "" : "s"} · ${data.clusters || 0} clusters`);
          } else {
            toast.error("Ingest failed. Check logs.");
          }
          qc.invalidateQueries({ queryKey: ["stories"] });
          qc.invalidateQueries({ queryKey: ["stats"] });
          qc.invalidateQueries({ queryKey: ["trending"] });
          qc.invalidateQueries({ queryKey: ["sources"] });
          onComplete?.(data);
        }
      } catch (e) {
        // ignore transient errors
      }
    };
    poll();
    const iv = setInterval(poll, 900);
    return () => {
      alive = false;
      clearInterval(iv);
    };
  }, [taskId, dismissed, qc, onComplete]);

  if (!taskId || dismissed || !task) return null;
  const isDone = task.status === "completed";
  const isFailed = task.status === "failed";
  const running = !isDone && !isFailed;

  return (
    <AnimatePresence>
      <motion.div
        data-testid="ingest-progress"
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -12 }}
        className="border border-emerald-500/30 bg-slate-950 mb-6"
      >
        <div className="p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              {running && <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" strokeWidth={1.5} />}
              {isDone && <Check className="w-4 h-4 text-emerald-400" strokeWidth={2} />}
              {isFailed && <AlertTriangle className="w-4 h-4 text-rose-400" strokeWidth={2} />}
              <div>
                <div className="overline text-emerald-400">
                  {running ? "Ingestion in progress" : isDone ? "Ingestion complete" : "Ingestion failed"}
                </div>
                <div className="font-mono text-[10px] text-slate-500 mt-0.5">task {taskId.slice(0, 8)}…</div>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <Counter label="new articles" value={task.new_articles ?? 0} highlight={isDone && (task.new_articles || 0) > 0} />
              <Counter label="clusters" value={task.clusters ?? 0} />
              {(isDone || isFailed) && (
                <button
                  data-testid="dismiss-progress-btn"
                  onClick={() => setDismissed(true)}
                  className="font-mono text-[10px] uppercase tracking-wider text-slate-500 hover:text-slate-200 transition-colors duration-200"
                >
                  dismiss
                </button>
              )}
            </div>
          </div>

          <ol className="space-y-1.5">
            {(task.steps || []).map((s, i) => {
              const label = stepBase(s.name);
              const running = s.status === "running";
              const done = s.status === "done";
              const error = s.status === "error";
              return (
                <li key={i} className="flex items-center gap-3 font-mono text-[11px]">
                  <span
                    className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                      done ? "bg-emerald-400" : running ? "bg-emerald-400 animate-pulse" : error ? "bg-rose-400" : "bg-slate-700"
                    }`}
                  />
                  <span className={done ? "text-slate-300" : running ? "text-slate-100" : error ? "text-rose-300" : "text-slate-500"}>
                    {label}
                    {s.name.includes("(") ? <span className="text-slate-500"> {s.name.slice(s.name.indexOf("("))}</span> : null}
                  </span>
                  <span className="ml-auto text-[10px] text-slate-600">
                    {running ? "running…" : done ? "done" : error ? "error" : "queued"}
                  </span>
                </li>
              );
            })}
            {task.steps?.length === 0 && (
              <li className="font-mono text-[11px] text-slate-500">Warming up pipeline…</li>
            )}
          </ol>

          {isDone && (task.new_articles || 0) === 0 && (
            <div className="mt-4 flex items-start gap-2 text-xs text-slate-400 border-t border-slate-900 pt-3">
              <Sparkles className="w-3.5 h-3.5 text-slate-500 mt-0.5 flex-shrink-0" />
              <span>
                Feeds already fully indexed since the last run. Wait a few minutes for publishers to publish new items, or trigger again.
              </span>
            </div>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

const Counter = ({ label, value, highlight }) => (
  <div className="text-right">
    <div className={`font-display text-xl font-bold leading-none ${highlight ? "text-emerald-400" : "text-slate-100"}`}>{value}</div>
    <div className="overline mt-0.5">{label}</div>
  </div>
);
