"use client";

import Logo from "./Logo";
import { Plus, Layers, Mic, Bolt, Quote } from "./icons";

const FEATURES = [
  { icon: Layers, title: "Any two videos", body: "YouTube or Instagram, in any mix — the platform is detected automatically per URL." },
  { icon: Mic, title: "Real transcripts", body: "Free YouTube captions and Whisper for Reels, timestamped to the second." },
  { icon: Bolt, title: "Engagement, computed", body: "(likes + comments) ÷ views, calculated in code — never guessed by the model." },
  { icon: Quote, title: "Cited RAG chat", body: "Streamed, sourced answers with memory — every claim cites the exact moment." },
];

export default function Landing({ onStart }: { onStart: () => void }) {
  return (
    <div className="h-full overflow-y-auto overflow-x-hidden scroll-smooth">
      {/* nav — transparent, blends with page, no divider line */}
      <nav className="flex items-center justify-between px-5 py-4 sm:px-10">
        <Logo />
        <div className="flex items-center gap-7">
          <a href="#features" className="hidden text-sm text-muted transition hover:text-white sm:block">
            Features
          </a>
          <button onClick={onStart} className="btn-accent rounded-xl px-4 py-2 text-sm font-semibold text-white">
            Get Started
          </button>
        </div>
      </nav>

      {/* hero (no overflow-hidden so the top glow bleeds up behind the nav and blends) */}
      <section className="relative px-5 pb-24 pt-16 text-center sm:pt-24">
        <div className="glow-blob pulse-glow" style={{ width: 620, height: 620, top: -180, left: "50%", transform: "translateX(-50%)", background: "radial-gradient(circle, rgba(139,92,246,0.42), transparent 68%)" }} />
        <div className="glow-blob" style={{ width: 420, height: 420, top: 0, right: "2%", background: "radial-gradient(circle, rgba(232,121,249,0.22), transparent 68%)" }} />

        <div className="relative mx-auto max-w-3xl">
          <span className="fade-up inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-white/[0.03] px-3.5 py-1.5 text-xs text-white/75">
            <span className="h-1.5 w-1.5 rounded-full bg-good" /> Your AI video-analysis assistant
          </span>

          <h1 className="fade-up d1 mt-6 text-5xl font-bold leading-[1.05] tracking-tight text-white sm:text-[3.75rem]">
            Compare any two videos
            <br />
            with <span className="gradient-text">AI-powered precision</span>
          </h1>

          <p className="fade-up d2 mx-auto mt-6 max-w-xl text-base leading-relaxed text-muted">
            Drop two YouTube or Instagram links. CreatorLens pulls transcripts, metadata and engagement —
            then lets you chat with both videos and get answers cited to the exact moment.
          </p>

          <div className="fade-up d3 mt-9">
            <button onClick={onStart} className="btn-accent inline-flex items-center gap-2.5 rounded-2xl px-8 py-4 text-base font-semibold text-white">
              <Plus className="h-5 w-5" /> New Analysis
            </button>
          </div>
        </div>
      </section>

      {/* features */}
      <section id="features" className="relative px-5 pb-24 sm:px-8">
        <div className="glow-blob" style={{ width: 480, height: 480, top: 40, left: "-10%", background: "radial-gradient(circle, rgba(99,102,241,0.16), transparent 68%)" }} />
        <div className="relative mx-auto max-w-5xl">
          <div className="mb-12 text-center">
            <span className="text-xs font-semibold uppercase tracking-widest text-violet-300">Features</span>
            <h2 className="mt-3 text-3xl font-bold tracking-tight text-white sm:text-4xl">
              Everything you need to <span className="gradient-text">understand what wins</span>
            </h2>
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            {FEATURES.map((f) => (
              <div key={f.title} className="group card-glow panel lift rounded-2xl p-6">
                <span className="mb-4 grid h-12 w-12 place-items-center rounded-xl bg-gradient-to-br from-violet-500/20 to-fuchsia-500/10 ring-1 ring-violet-500/25 transition duration-300 group-hover:scale-110 group-hover:ring-violet-400/70 group-hover:shadow-[0_0_28px_-4px_rgba(139,92,246,0.85)]">
                  <f.icon className="h-[22px] w-[22px] text-violet-200 transition group-hover:text-white" />
                </span>
                <h3 className="text-base font-semibold text-white">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{f.body}</p>
              </div>
            ))}
          </div>

          <p className="mt-14 text-center text-xs text-muted">
            Built with LangGraph · Groq · Qdrant · fastembed — a fully free, dynamic RAG stack.
          </p>
        </div>
      </section>
    </div>
  );
}
