"use client";

import type { Video } from "../lib/types";
import { compact } from "../lib/format";

const A_COLOR = "#a855f7"; // purple
const B_COLOR = "#22d3ee"; // cyan

type Row = {
  label: string;
  av: number;
  bv: number;
  fmt: (n: number) => string;
  deltaFmt: (n: number) => string;
  hint?: string;
};

export default function QuickComparison({ a, b }: { a: Video; b: Video }) {
  const rows: Row[] = [
    {
      label: "Engagement Rate",
      av: a.engagement_rate,
      bv: b.engagement_rate,
      fmt: (n) => `${n}%`,
      deltaFmt: (n) => `+${(Math.round(n * 100) / 100).toFixed(2)} pts`,
      hint: "(likes + comments) ÷ views",
    },
    { label: "Views", av: a.views, bv: b.views, fmt: compact, deltaFmt: (n) => `+${compact(n)}` },
    { label: "Likes", av: a.likes, bv: b.likes, fmt: compact, deltaFmt: (n) => `+${compact(n)}` },
    { label: "Comments", av: a.comments, bv: b.comments, fmt: compact, deltaFmt: (n) => `+${compact(n)}` },
  ];

  return (
    <div className="card-glow panel fade-up d3 rounded-2xl p-5 sm:p-6">
      <div className="mb-6 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white/90">Head-to-head</h3>
        <div className="flex items-center gap-4 text-xs">
          <Legend color={A_COLOR} name="A" creator={a.creator} />
          <Legend color={B_COLOR} name="B" creator={b.creator} />
        </div>
      </div>

      <div className="space-y-6">
        {rows.map((r) => (
          <CompareRow key={r.label} row={r} />
        ))}
      </div>
    </div>
  );
}

function CompareRow({ row }: { row: Row }) {
  const total = row.av + row.bv;
  const aPct = total > 0 ? (row.av / total) * 100 : 50;
  const winner = row.av === row.bv ? null : row.av > row.bv ? "A" : "B";
  const delta = Math.abs(row.av - row.bv);

  return (
    <div>
      <div className="mb-2.5 flex items-baseline justify-between">
        <div className="flex items-baseline gap-2">
          <span className="text-[13px] font-medium text-white/85">{row.label}</span>
          {row.hint && <span className="hidden text-[11px] text-muted sm:inline">{row.hint}</span>}
        </div>
        {winner && (
          <span
            className="rounded-full px-2.5 py-0.5 text-[11px] font-semibold"
            style={{
              color: winner === "A" ? A_COLOR : B_COLOR,
              background: winner === "A" ? "rgba(168,85,247,0.14)" : "rgba(34,211,238,0.14)",
            }}
          >
            {winner} leads · {row.deltaFmt(delta)}
          </span>
        )}
      </div>

      <div className="flex items-center gap-2 sm:gap-2.5">
        <Value side="A" color={A_COLOR} text={row.fmt(row.av)} />

        {/* split track — solid colors + a clear gap so A vs B is obvious */}
        <div className="flex h-2.5 flex-1 items-center gap-1.5 sm:h-3">
          <div className="h-full rounded-full transition-[width] duration-700 ease-out" style={{ width: `${aPct}%`, minWidth: 6, background: A_COLOR }} />
          <div className="h-full rounded-full transition-[width] duration-700 ease-out" style={{ width: `${100 - aPct}%`, minWidth: 6, background: B_COLOR }} />
        </div>

        <Value side="B" color={B_COLOR} text={row.fmt(row.bv)} right />
      </div>
    </div>
  );
}

function Value({ side, color, text, right }: { side: string; color: string; text: string; right?: boolean }) {
  const chip = (
    <span className="grid h-4 w-4 shrink-0 place-items-center rounded text-[10px] font-bold" style={{ color, background: `color-mix(in srgb, ${color} 18%, transparent)` }}>
      {side}
    </span>
  );
  const val = (
    <span className="text-sm font-bold tabular-nums" style={{ color }}>
      {text}
    </span>
  );
  return (
    <span className={`flex w-[4.25rem] shrink-0 items-center gap-1 sm:w-[5.5rem] sm:gap-1.5 ${right ? "justify-start" : "justify-end"}`}>
      {right ? (<>{chip}{val}</>) : (<>{val}{chip}</>)}
    </span>
  );
}

function Legend({ color, name, creator }: { color: string; name: string; creator: string | null }) {
  return (
    <span className="flex items-center gap-1.5 text-muted">
      <span className="h-2.5 w-2.5 rounded-sm" style={{ background: color }} />
      <span className="font-medium text-white/70">{name}</span>
      {creator && <span className="hidden max-w-[7rem] truncate sm:inline">· {creator}</span>}
    </span>
  );
}
