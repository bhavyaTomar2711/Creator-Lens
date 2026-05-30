"use client";

import { Aperture } from "./icons";

export default function Logo({ onClick }: { onClick?: () => void }) {
  const Tag = onClick ? "button" : "div";
  return (
    <Tag onClick={onClick} className="group flex items-center gap-3">
      <span className="relative grid h-11 w-11 place-items-center rounded-2xl bg-gradient-to-br from-violet-500 via-fuchsia-500 to-indigo-500 shadow-lg shadow-violet-500/30 ring-1 ring-white/10 transition group-hover:shadow-violet-500/50">
        <Aperture className="h-[22px] w-[22px] text-white" />
      </span>
      <span className="text-[19px] font-bold tracking-tight text-white">
        Creator<span className="gradient-text">Lens</span>
      </span>
    </Tag>
  );
}
