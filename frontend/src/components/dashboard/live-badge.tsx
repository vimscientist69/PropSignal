export function LiveBadge({ label = "Live ranking environment" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-slate-800/80 bg-slate-900/80 px-3 py-1 text-xs text-slate-400">
      <span
        aria-hidden
        className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(74,222,128,0.8)]"
      />
      {label}
    </span>
  );
}
