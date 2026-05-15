import { ChevronDown } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

/** Inner select — use the Select wrapper so the chevron is inset from the border. */
export const selectClass =
  "w-full appearance-none rounded-lg border border-slate-800 bg-slate-900/80 py-2 pl-3 pr-10 text-sm text-slate-100 outline-none focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500/40";

export type SelectProps = React.SelectHTMLAttributes<HTMLSelectElement>;

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, ...props }, ref) => (
    <div className="relative w-full">
      <select ref={ref} className={cn(selectClass, className)} {...props}>
        {children}
      </select>
      <ChevronDown
        aria-hidden
        className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
      />
    </div>
  ),
);
Select.displayName = "Select";
