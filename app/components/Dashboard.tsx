"use client";

import { useCallback, useState } from "react";
import type { Video } from "../lib/types";
import { ingestPair } from "../lib/api";
import VideoCard from "./VideoCard";
import QuickComparison from "./QuickComparison";
import ChatPanel from "./ChatPanel";
import Landing from "./Landing";
import Logo from "./Logo";
import { Plus, Aperture, Link } from "./icons";

type Status = "idle" | "loading" | "ready" | "error";

export default function Dashboard() {
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [a, setA] = useState<Video | null>(null);
  const [b, setB] = useState<Video | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [ua, setUa] = useState("");
  const [ub, setUb] = useState("");

  const [playA, setPlayA] = useState<number | null>(null);
  const [playB, setPlayB] = useState<number | null>(null);
  const [tab, setTab] = useState<"videos" | "chat">("videos");

  const analyze = useCallback(async () => {
    if (!ua.trim() || !ub.trim()) return;
    setStatus("loading");
    setError("");
    setShowForm(false);
    setPlayA(null);
    setPlayB(null);
    try {
      const r = await ingestPair(ua.trim(), ub.trim());
      setSessionId(r.session_id);
      setA(r.video_a);
      setB(r.video_b);
      setStatus("ready");
    } catch (e) {
      setError((e as Error).message);
      setStatus("error");
    }
  }, [ua, ub]);

  const cite = useCallback((v: "A" | "B", sec: number) => {
    if (v === "A") setPlayA(sec);
    else setPlayB(sec);
    setTab("videos");
  }, []);

  const newAnalysis = () => {
    setUa("");
    setUb("");
    setShowForm(true);
  };

  if (status === "idle") {
    return (
      <>
        <Landing onStart={newAnalysis} />
        {showForm && <AnalysisForm ua={ua} ub={ub} setUa={setUa} setUb={setUb} onSubmit={analyze} onClose={() => setShowForm(false)} canClose />}
      </>
    );
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <header className="flex shrink-0 items-center justify-between px-4 py-3 sm:px-6">
        <Logo onClick={() => setStatus("idle")} />
        {status === "ready" && (
          <button onClick={newAnalysis} className="btn-accent flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-sm font-medium text-white">
            <Plus className="h-4 w-4" /> New Analysis
          </button>
        )}
      </header>

      {status === "ready" && (
        <div className="px-4 pb-1 pt-2 lg:hidden">
          <div className="flex gap-1 rounded-xl border border-[var(--border)] bg-white/[0.03] p-1">
            {(["videos", "chat"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`flex-1 rounded-lg py-2 text-sm font-medium transition ${
                  tab === t ? "bg-violet-500/20 text-violet-100 shadow-sm" : "text-muted hover:text-white/80"
                }`}
              >
                {t === "videos" ? "Videos" : "Chat"}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="min-h-0 flex-1">
        {status === "error" && <ErrorState msg={error} onRetry={newAnalysis} />}
        {status === "loading" && <Loading />}
        {status === "ready" && a && b && (
          <div className="grid h-full min-h-0 lg:grid-cols-[minmax(0,1fr)_440px] xl:grid-cols-[minmax(0,1fr)_520px]">
            <main className={`min-h-0 overflow-y-auto px-5 py-5 sm:p-6 ${tab === "videos" ? "block" : "hidden"} lg:block`}>
              <div className="mx-auto max-w-5xl space-y-6">
                <div className="grid gap-5 md:grid-cols-2">
                  <VideoCard video={a} playFrom={playA} onPlay={setPlayA} />
                  <VideoCard video={b} playFrom={playB} onPlay={setPlayB} />
                </div>
                <QuickComparison a={a} b={b} />
              </div>
            </main>
            <div className={`min-h-0 px-4 pb-4 pt-1 sm:p-4 lg:border-l lg:border-[var(--border)] lg:pt-4 ${tab === "chat" ? "block" : "hidden"} lg:block`}>
              <ChatPanel sessionId={sessionId} onCite={cite} />
            </div>
          </div>
        )}
      </div>

      {showForm && <AnalysisForm ua={ua} ub={ub} setUa={setUa} setUb={setUb} onSubmit={analyze} onClose={() => setShowForm(false)} canClose />}
    </div>
  );
}

/* ---------- Form modal ---------- */
function AnalysisForm(props: {
  ua: string;
  ub: string;
  setUa: (s: string) => void;
  setUb: (s: string) => void;
  onSubmit: () => void;
  onClose: () => void;
  canClose: boolean;
}) {
  const valid = props.ua.trim() && props.ub.trim();
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4 backdrop-blur-md">
      <div className="card-glow panel w-full max-w-lg rounded-2xl p-6 fade-up">
        <div className="mb-1 flex items-center gap-2">
          <Aperture className="h-5 w-5 text-violet-400" />
          <h2 className="text-lg font-semibold text-white">New Analysis</h2>
        </div>
        <p className="mb-5 text-sm text-muted">Paste any two videos — YouTube or Instagram, in any mix.</p>

        <Field label="First video" value={props.ua} onChange={props.setUa} />
        <div className="h-4" />
        <Field label="Second video" value={props.ub} onChange={props.setUb} />

        <div className="mt-6 flex gap-2">
          <button onClick={props.onSubmit} disabled={!valid} className="btn-accent flex-1 rounded-xl py-2.5 text-sm font-semibold text-white disabled:opacity-40">
            Analyze
          </button>
          {props.canClose && (
            <button onClick={props.onClose} className="btn-ghost rounded-xl px-4 text-sm text-muted hover:text-white">
              Cancel
            </button>
          )}
        </div>
        <p className="mt-3 text-center text-[11px] text-muted">
          First run downloads + transcribes (~20–30s). Repeats are cached & instant.
        </p>
      </div>
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (s: string) => void }) {
  return (
    <div>
      <label className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-muted">
        <Link className="h-3.5 w-3.5 text-violet-400" /> {label}
      </label>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Paste a YouTube or Instagram URL"
        className="w-full rounded-xl border border-[var(--border)] bg-white/[0.03] px-3.5 py-2.5 text-sm text-white placeholder:text-white/25 focus:border-violet-500/50 focus:outline-none focus:ring-2 focus:ring-violet-500/15"
      />
    </div>
  );
}

function ErrorState({ msg, onRetry }: { msg: string; onRetry: () => void }) {
  return (
    <div className="grid h-full place-items-center px-6">
      <div className="card-glow panel max-w-md rounded-2xl p-6 text-center fade-up">
        <p className="text-sm text-red-400">⚠️ {msg}</p>
        <button onClick={onRetry} className="btn-accent mt-4 rounded-xl px-5 py-2 text-sm font-medium text-white">
          Try again
        </button>
      </div>
    </div>
  );
}

function Loading() {
  return (
    <div className="grid h-full min-h-0 lg:grid-cols-[minmax(0,1fr)_440px] xl:grid-cols-[minmax(0,1fr)_520px]">
      <main className="min-h-0 overflow-y-auto p-4 sm:p-6">
        <div className="mx-auto max-w-5xl space-y-5">
          <div className="grid gap-4 md:grid-cols-2">
            {[0, 1].map((i) => (
              <div key={i} className="panel rounded-2xl p-5 sm:p-6">
                <div className="shimmer mb-4 h-5 w-24 rounded-md" />
                <div className="shimmer aspect-video w-full rounded-xl" />
                <div className="shimmer mt-4 h-5 w-3/4 rounded-md" />
                <div className="shimmer mt-2 h-3 w-1/2 rounded-md" />
                <div className="mt-5 grid grid-cols-4 gap-2.5">
                  {[0, 1, 2, 3].map((j) => (
                    <div key={j} className="shimmer h-14 rounded-xl" />
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="panel rounded-2xl p-5 sm:p-6">
            <div className="shimmer mb-5 h-5 w-32 rounded-md" />
            {[0, 1, 2, 3].map((i) => (
              <div key={i} className="shimmer mb-4 h-3 w-full rounded-md" />
            ))}
          </div>
        </div>
      </main>

      {/* analyzing panel (mirrors the chat column so the layout doesn't jump) */}
      <div className="hidden border-l border-[var(--border)] p-3 sm:p-4 lg:block">
        <div className="panel flex h-full flex-col items-center justify-center gap-4 rounded-2xl p-6 text-center">
          <span className="floaty grid h-16 w-16 place-items-center rounded-2xl bg-gradient-to-br from-violet-500/25 to-fuchsia-500/10 ring-1 ring-violet-500/30">
            <Aperture className="h-8 w-8 text-violet-200" />
          </span>
          <div>
            <p className="text-sm font-semibold text-white/90">Analyzing your videos</p>
            <p className="mt-1.5 flex items-center justify-center gap-1.5 text-xs text-muted">
              <span className="dot" /> <span className="dot" /> <span className="dot" />
              transcribing &amp; embedding
            </p>
          </div>
          <div className="mt-2 w-full max-w-[15rem] space-y-2 text-left text-xs text-muted">
            {["Fetching metadata", "Pulling transcripts", "Chunking & embedding", "Indexing in Qdrant"].map((s) => (
              <div key={s} className="flex items-center gap-2">
                <span className="h-1.5 w-1.5 rounded-full bg-violet-400/70" /> {s}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
