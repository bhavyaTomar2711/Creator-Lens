"use client";

import { useState } from "react";
import type { Video } from "../lib/types";
import { compact, duration, prettyDate } from "../lib/format";
import { YouTube, Instagram, Play, Check } from "./icons";

function ytId(url: string): string | null {
  return url.match(/(?:v=|\/shorts\/|youtu\.be\/|\/embed\/)([A-Za-z0-9_-]{11})/)?.[1] ?? null;
}
function igShortcode(url: string): string | null {
  return url.match(/\/(?:reel|reels|p|tv)\/([A-Za-z0-9_-]+)/)?.[1] ?? null;
}

/** playFrom: seconds to start at (or null = show thumbnail). */
export default function VideoCard({
  video,
  playFrom,
  onPlay,
}: {
  video: Video;
  playFrom: number | null;
  onPlay: (sec: number) => void;
}) {
  const [thumbErr, setThumbErr] = useState(false);
  const isYT = video.platform === "youtube";
  const label = video.video_id;

  const embed = (() => {
    if (playFrom == null) return null;
    if (isYT) {
      const id = ytId(video.url);
      return id ? `https://www.youtube.com/embed/${id}?start=${Math.floor(playFrom)}&autoplay=1` : null;
    }
    const sc = igShortcode(video.url);
    return sc ? `https://www.instagram.com/reel/${sc}/embed` : null;
  })();

  const stats = [
    { label: "Views", value: compact(video.views) },
    { label: "Likes", value: compact(video.likes) },
    { label: "Comments", value: compact(video.comments) },
    { label: "Engagement", value: `${video.engagement_rate}%`, good: true },
  ];

  const accent = label === "A" ? "var(--a)" : "var(--b)";

  return (
    <div className="card-glow panel lift fade-up d1 flex flex-col rounded-2xl p-5 sm:p-6">
      {/* header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className="grid h-6 w-6 place-items-center rounded-md text-xs font-bold"
            style={{ color: accent, background: `color-mix(in srgb, ${accent} 16%, transparent)` }}
          >
            {label}
          </span>
          <span className="text-sm font-semibold text-white/90">Video {label}</span>
        </div>
        <span
          className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
            isYT ? "bg-red-500/10 text-red-400" : "bg-fuchsia-500/10 text-fuchsia-300"
          }`}
        >
          {isYT ? <YouTube className="h-3.5 w-3.5" /> : <Instagram className="h-3.5 w-3.5" />}
          {isYT ? "YouTube" : "Instagram Reels"}
        </span>
      </div>

      {/* media */}
      <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-panel-2">
        {embed ? (
          <iframe
            src={embed}
            className="absolute inset-0 h-full w-full"
            allow="autoplay; encrypted-media; clipboard-write; picture-in-picture"
            allowFullScreen
            title={`Video ${label}`}
          />
        ) : (
          <button
            onClick={() => onPlay(0)}
            className="group absolute inset-0 h-full w-full"
            aria-label="Play video"
          >
            {video.thumbnail && !thumbErr ? (
              // plain img (lazy) — avoids next/image remote config + optimization latency
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={video.thumbnail}
                alt={video.title ?? ""}
                loading="lazy"
                onError={() => setThumbErr(true)}
                className="h-full w-full object-cover"
              />
            ) : (
              <div className="h-full w-full bg-gradient-to-br from-violet-600/30 to-indigo-600/20" />
            )}
            <span className="absolute inset-0 grid place-items-center bg-black/20 transition group-hover:bg-black/30">
              <span className="grid h-12 w-12 place-items-center rounded-full bg-white/90 text-black shadow-lg transition group-hover:scale-105">
                <Play className="ml-0.5 h-5 w-5" />
              </span>
            </span>
            {video.duration_sec != null && (
              <span className="absolute bottom-2 right-2 rounded bg-black/75 px-1.5 py-0.5 text-xs font-medium tabular-nums">
                {duration(video.duration_sec)}
              </span>
            )}
          </button>
        )}
      </div>

      {/* title + creator */}
      <h3 className="mt-4 line-clamp-2 text-base font-semibold leading-snug text-white/95">
        {video.title ?? "Untitled"}
      </h3>
      <div className="mt-2 flex items-center gap-2 text-sm text-muted">
        <span className="font-medium text-white/80">{video.creator ?? "Unknown"}</span>
        {video.follower_count != null && (
          <span className="text-xs">· {compact(video.follower_count)} followers</span>
        )}
      </div>
      <div className="mt-1 text-xs text-muted">
        {prettyDate(video.upload_date)} · {duration(video.duration_sec)}
      </div>

      {/* stats */}
      <div className="mt-5 grid grid-cols-4 gap-2.5">
        {stats.map((s) => (
          <div
            key={s.label}
            className={`rounded-xl px-2 py-3 text-center ${
              s.good ? "border border-good/20 bg-good/[0.06]" : "tile"
            }`}
          >
            <div className={`text-lg font-bold tabular-nums ${s.good ? "text-good" : "text-white/90"}`}>
              {s.value}
            </div>
            <div className="mt-1 text-[10px] uppercase tracking-wide text-muted">{s.label}</div>
          </div>
        ))}
      </div>

      {/* hashtags */}
      {video.hashtags.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {video.hashtags.slice(0, 4).map((t) => (
            <span key={t} className="rounded-md bg-white/[0.04] px-2 py-1 text-xs text-white/60">
              {t}
            </span>
          ))}
          {video.hashtags.length > 4 && (
            <span className="rounded-md bg-white/[0.04] px-2 py-1 text-xs text-white/40">
              +{video.hashtags.length - 4}
            </span>
          )}
        </div>
      )}

      {/* spacer pushes the transcript strip to the bottom for equal-height cards */}
      <div className="flex-1" />

      {/* transcript status — slim strip (proof the transcript was pulled) */}
      <div className="tile mt-5 flex items-center gap-1.5 rounded-lg px-3 py-2.5 text-xs text-good">
        <Check className="h-3.5 w-3.5" /> Transcript ready · {video.transcript_source}
      </div>
    </div>
  );
}
