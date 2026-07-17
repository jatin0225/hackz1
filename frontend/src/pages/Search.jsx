import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Search as SearchIcon } from "lucide-react";
import { searchStories } from "../lib/api";
import StoryCard from "../components/StoryCard";

export default function Search() {
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState(params.get("q") || "");
  useEffect(() => { document.title = q ? `${q} · PRISM Search` : "Search · PRISM"; }, [q]);

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["search", params.get("q")],
    queryFn: () => searchStories(params.get("q") || ""),
    enabled: !!params.get("q"),
  });

  const submit = (e) => {
    e.preventDefault();
    setParams({ q });
  };

  return (
    <div className="max-w-7xl mx-auto px-6 lg:px-10 py-12">
      <div className="overline mb-3">Semantic search</div>
      <h1 className="font-display text-3xl lg:text-4xl font-bold text-slate-50 tracking-tight mb-8">Find stories across sources</h1>

      <form onSubmit={submit} className="max-w-2xl relative mb-10">
        <SearchIcon className="w-4 h-4 text-slate-500 absolute left-4 top-1/2 -translate-y-1/2" />
        <input
          data-testid="search-input"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Tesla, Fed, climate, AI regulation..."
          autoFocus
          className="w-full bg-slate-950 border border-slate-800 focus:border-emerald-500/50 outline-none pl-11 pr-24 py-3.5 font-mono text-sm text-slate-100 placeholder-slate-600 transition-colors duration-200"
        />
        <button
          data-testid="search-btn"
          type="submit"
          className="absolute right-2 top-1/2 -translate-y-1/2 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-mono uppercase tracking-wider text-[11px] px-4 py-2 transition-colors duration-200"
        >
          Search
        </button>
      </form>

      {(isLoading || isFetching) && params.get("q") && <div className="text-slate-500 font-mono text-xs">Searching...</div>}

      {data && (
        <>
          <div className="overline mb-6">{data.count} matches for &ldquo;{params.get("q")}&rdquo;</div>
          {data.items.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {data.items.map((s, i) => (
                <StoryCard key={s.id} story={s} index={i} />
              ))}
            </div>
          ) : (
            <div className="border border-slate-800 bg-slate-950 p-12 text-center">
              <div className="overline mb-2">No results</div>
              <div className="text-slate-500 text-sm">Try &ldquo;Tesla&rdquo;, &ldquo;Federal Reserve&rdquo;, &ldquo;climate&rdquo; or &ldquo;AI&rdquo;.</div>
            </div>
          )}
        </>
      )}

      {!params.get("q") && (
        <div className="text-slate-500 text-sm">Type a topic, person, or event to see matching coverage.</div>
      )}
    </div>
  );
}
