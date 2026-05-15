import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function InnerPanel({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div className={cn("rounded-xl border border-slate-800/80 bg-slate-950/30 p-3", className)}>
      {children}
    </div>
  );
}
