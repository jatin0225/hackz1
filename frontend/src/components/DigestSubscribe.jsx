import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { Mail, ArrowRight, Check } from "lucide-react";
import { subscribeEmail } from "../lib/api";

export default function DigestSubscribe() {
  const [email, setEmail] = useState("");
  const [done, setDone] = useState(false);

  const mut = useMutation({
    mutationFn: subscribeEmail,
    onSuccess: (r) => {
      setDone(true);
      toast.success(r.already_subscribed ? "You're already subscribed." : "You're in. Digest lands daily at 13:00 UTC.");
    },
    onError: () => toast.error("Something went wrong. Try again in a moment."),
  });

  const submit = (e) => {
    e.preventDefault();
    if (!email) return;
    mut.mutate(email);
  };

  return (
    <section data-testid="digest-subscribe" className="border border-slate-800 bg-slate-950 p-6 lg:p-8">
      <div className="flex items-start gap-4 mb-4">
        <div className="w-9 h-9 border border-emerald-500/40 bg-emerald-500/10 grid place-items-center flex-shrink-0">
          <Mail className="w-4 h-4 text-emerald-400" strokeWidth={1.5} />
        </div>
        <div>
          <div className="overline mb-1 text-emerald-400">Daily digest</div>
          <h3 className="font-display text-lg font-semibold text-slate-100 tracking-tight leading-tight">
            One email a day. The single most divided story.
          </h3>
          <p className="text-slate-500 text-sm leading-relaxed mt-1">
            We find the story with the widest editorial split and send you the neutral summary + every publisher&rsquo;s angle. That&rsquo;s it.
          </p>
        </div>
      </div>
      {done ? (
        <div data-testid="subscribe-success" className="flex items-center gap-2 font-mono text-xs text-emerald-400 border border-emerald-500/30 bg-emerald-500/5 px-4 py-3">
          <Check className="w-4 h-4" /> You&rsquo;re on the list. Next digest goes out at 13:00 UTC.
        </div>
      ) : (
        <form onSubmit={submit} className="relative">
          <input
            data-testid="subscribe-email-input"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full bg-slate-900 border border-slate-800 focus:border-emerald-500/50 outline-none px-4 pr-32 py-3 font-mono text-sm text-slate-100 placeholder-slate-600 transition-colors duration-200"
          />
          <button
            data-testid="subscribe-btn"
            type="submit"
            disabled={mut.isPending}
            className="absolute right-1.5 top-1/2 -translate-y-1/2 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-mono uppercase tracking-wider text-[11px] px-4 py-2 flex items-center gap-1.5 transition-colors duration-200"
          >
            {mut.isPending ? "..." : <>Subscribe <ArrowRight className="w-3 h-3" /></>}
          </button>
        </form>
      )}
    </section>
  );
}
