import * as React from "react";

import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  compact?: boolean;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, compact, ...props }, ref) => (
    <input
      type={type}
      className={cn(
        "w-full rounded-lg border border-slate-800 bg-slate-900/80 text-slate-100 outline-none placeholder:text-slate-600 focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500/40 disabled:cursor-not-allowed disabled:opacity-50",
        compact ? "px-2 py-1 text-[11px]" : "px-3 py-2 text-sm",
        className,
      )}
      ref={ref}
      {...props}
    />
  ),
);
Input.displayName = "Input";

export { Input };
