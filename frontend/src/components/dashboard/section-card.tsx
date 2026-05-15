import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type SectionCardProps = {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  light?: boolean;
};

export function SectionCard({
  title,
  subtitle,
  action,
  children,
  className,
  light = false,
}: SectionCardProps) {
  return (
    <section
      className={cn(
        "overflow-hidden rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900/80",
        light ? "" : "shadow-[0_18px_60px_rgba(15,23,42,0.9)]",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3 border-b border-slate-800/80 px-4 pb-3 pt-4">
        <div>
          <h2 className="text-sm font-semibold text-slate-50">{title}</h2>
          {subtitle ? <p className="mt-0.5 text-xs text-slate-400">{subtitle}</p> : null}
        </div>
        {action}
      </div>
      <div className="space-y-4 px-4 py-4">{children}</div>
    </section>
  );
}
