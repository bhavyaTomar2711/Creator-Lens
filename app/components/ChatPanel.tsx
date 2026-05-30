"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { ChatMessage, Source } from "../lib/types";
import { streamChat } from "../lib/api";
import { timestamp } from "../lib/format";
import { Aperture, Send, Arrow } from "./icons";

const SUGGESTED = [
  "What's the engagement rate of each?",
  "Compare the hooks in the first 5 seconds.",
  "Who's the creator of Video B?",
  "Suggest improvements for B based on A.",
];

export default function ChatPanel({
  sessionId,
  onCite,
}: {
  sessionId: string | null;
  onCite: (videoId: "A" | "B", sec: number) => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // reset when a new analysis starts
  useEffect(() => {
    setMessages([]);
    setBusy(false);
    abortRef.current?.abort();
  }, [sessionId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = useCallback(
    async (text: string) => {
      const q = text.trim();
      if (!q || !sessionId || busy) return;
      setInput("");
      setBusy(true);
      setMessages((m) => [
        ...m,
        { role: "user", content: q },
        { role: "assistant", content: "", streaming: true },
      ]);

      const patchLast = (fn: (m: ChatMessage) => ChatMessage) =>
        setMessages((msgs) => {
          const copy = msgs.slice();
          copy[copy.length - 1] = fn(copy[copy.length - 1]);
          return copy;
        });

      const ac = new AbortController();
      abortRef.current = ac;
      await streamChat(
        sessionId,
        q,
        {
          onSources: (s: Source[]) => patchLast((m) => ({ ...m, sources: s })),
          onToken: (t) => patchLast((m) => ({ ...m, content: m.content + t })),
          onDone: (answer, sources) =>
            patchLast((m) => ({ ...m, content: answer || m.content, sources, streaming: false })),
          onError: (e) =>
            patchLast((m) => ({ ...m, content: `⚠️ ${e.message}`, streaming: false })),
        },
        ac.signal,
      );
      setBusy(false);
    },
    [sessionId, busy],
  );

  return (
    <div className="panel flex h-full flex-col rounded-2xl">
      {/* header */}
      <div className="flex items-center gap-2.5 px-4 py-3.5">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-violet-500 via-fuchsia-500 to-indigo-500">
          <Aperture className="h-4 w-4 text-white" />
        </span>
        <div>
          <div className="text-sm font-semibold text-white/95">AI Chat Assistant</div>
          <div className="text-xs text-muted">Ask anything about your videos</div>
        </div>
      </div>
      {/* purple→pink hairline divider (not the old bluish border) */}
      <div className="h-px w-full bg-gradient-to-r from-transparent via-violet-500/60 to-fuchsia-500/40" />

      {/* messages */}
      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-4 py-5 sm:px-5">
        {messages.length === 0 ? (
          <div className="mt-6 sm:mt-8">
            <div className="text-center">
              <span className="floaty mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br from-violet-500/20 to-fuchsia-500/10 ring-1 ring-violet-500/20">
                <Aperture className="h-6 w-6 text-violet-300" />
              </span>
              <p className="text-sm font-medium text-white/85">Chat with both videos</p>
              <p className="mx-auto mt-1 max-w-[18rem] text-xs text-muted">
                Ask about engagement, hooks, creators, or how to improve — answers cite the exact moment.
              </p>
            </div>
            {/* suggested prompts live IN the chat, not pinned above the input */}
            <div className="mt-6 space-y-2">
              {SUGGESTED.map((s) => (
                <button
                  key={s}
                  disabled={busy}
                  onClick={() => send(s)}
                  className="group flex w-full items-center justify-between gap-2 rounded-xl border border-[var(--border)] bg-white/[0.02] px-4 py-3 text-left text-sm text-white/75 transition hover:border-[var(--border-strong)] hover:bg-white/[0.04] hover:text-white disabled:opacity-40"
                >
                  {s}
                  <Arrow className="h-3.5 w-3.5 shrink-0 text-violet-400 transition group-hover:translate-x-0.5" />
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((m, i) => (
              <Message key={i} m={m} onCite={onCite} />
            ))}
            {/* suggested questions stay available as an in-chat section (not pinned to input) */}
            {!busy && (
              <div className="pt-1">
                <div className="mb-2 text-[11px] font-medium uppercase tracking-wide text-muted">Suggested</div>
                <div className="flex flex-wrap gap-2">
                  {SUGGESTED.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="group flex items-center gap-1.5 rounded-full border border-[var(--border)] bg-white/[0.02] px-3 py-1.5 text-xs text-white/70 transition hover:border-[var(--border-strong)] hover:text-white"
                    >
                      {s}
                      <Arrow className="h-3 w-3 text-violet-400 transition group-hover:translate-x-0.5" />
                    </button>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* input */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="flex items-center gap-2 border-t border-[var(--border)] p-3 sm:p-3.5"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={!sessionId || busy}
          placeholder={sessionId ? "Ask a question…" : "Run an analysis first"}
          className="flex-1 rounded-xl border border-[var(--border)] bg-white/[0.03] px-3.5 py-2.5 text-sm text-white placeholder:text-muted focus:border-violet-500/50 focus:outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!sessionId || busy || !input.trim()}
          className="btn-accent grid h-10 w-10 shrink-0 place-items-center rounded-xl text-white disabled:opacity-40"
          aria-label="Send"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}

function Message({ m, onCite }: { m: ChatMessage; onCite: (v: "A" | "B", s: number) => void }) {
  if (m.role === "user") {
    return (
      <div className="flex justify-end fade-up">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-gradient-to-br from-violet-600 to-indigo-600 px-3.5 py-2.5 text-sm text-white">
          {m.content}
        </div>
      </div>
    );
  }
  // Only surface sources the answer actually cited inline (e.g. "[A · chunk 0]").
  // Metadata-only answers cite nothing -> no Sources row; keeps citations meaningful.
  const refs = referencedChunks(m.content);
  const cites = dedupeCites(m.sources ?? []).filter((c) => refs.has(`${c.video_id}-${c.chunk_index}`));
  return (
    <div className="flex justify-start gap-2.5 fade-up">
      <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-violet-500 via-fuchsia-500 to-indigo-500">
        <Aperture className="h-3.5 w-3.5 text-white" />
      </span>
      <div className="max-w-[88%] rounded-2xl rounded-tl-md bg-white/[0.04] px-3.5 py-2.5 text-sm leading-relaxed text-white/90">
        <div className="whitespace-pre-wrap">
          {renderRich(m.content)}
          {m.streaming && m.content === "" ? (
            <span className="inline-flex items-center gap-1">
              <span className="dot" /><span className="dot" /><span className="dot" />
            </span>
          ) : m.streaming ? (
            <span className="caret" />
          ) : null}
        </div>
        {cites.length > 0 && (
          <div className="mt-2.5 flex flex-wrap gap-1.5 border-t border-[var(--border)] pt-2.5">
            <span className="text-[11px] text-muted">Sources:</span>
            {cites.map((c) => (
              <button
                key={`${c.video_id}-${c.chunk_index}`}
                onClick={() => onCite(c.video_id, c.start)}
                title={`Jump to ${c.video_id} at ${timestamp(c.start)}`}
                className="rounded-md border border-violet-500/25 bg-violet-500/10 px-1.5 py-0.5 text-[11px] font-medium text-violet-200 transition hover:bg-violet-500/20"
              >
                {c.video_id} · {timestamp(c.start)}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Parse inline citations like "[A · chunk 0]", "[B chunk 1]" -> {"A-0","B-1"}.
function referencedChunks(text: string): Set<string> {
  const re = /\[\s*([AB])\s*[·.\-]?\s*chunk\s*(\d+)\s*\]/gi;
  const out = new Set<string>();
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) out.add(`${m[1].toUpperCase()}-${m[2]}`);
  return out;
}

function dedupeCites(sources: Source[]): Source[] {
  const seen = new Set<string>();
  const out: Source[] = [];
  for (const s of sources) {
    const k = `${s.video_id}-${s.chunk_index}`;
    if (!seen.has(k)) {
      seen.add(k);
      out.push(s);
    }
  }
  return out;
}

/** Tiny, dependency-free rich text: **bold** -> <strong>. */
function renderRich(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith("**") && p.endsWith("**") ? (
      <strong key={i} className="font-semibold text-white">
        {p.slice(2, -2)}
      </strong>
    ) : (
      <span key={i}>{p}</span>
    ),
  );
}
