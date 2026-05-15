"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Database,
  LayoutDashboard,
  Menu,
  Search,
  X,
} from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { API_BASE } from "@/app/dashboard/lib/api";
import { cn } from "@/lib/utils";

type ToastTone = "default" | "error";

type ToastState = {
  message: string;
  tone: ToastTone;
};

type ToastContextValue = {
  pushToast: (message: string, tone?: ToastTone) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within DashboardChrome");
  }
  return ctx;
}

const NAV = [
  { href: "/dashboard/control", label: "Control Panel", icon: LayoutDashboard },
  { href: "/dashboard/sources", label: "Source Library", icon: Database },
  { href: "/dashboard/runs", label: "Runs", icon: Activity },
  { href: "/dashboard/diagnostics", label: "Diagnostics", icon: Search },
] as const;

export function DashboardChrome({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [toast, setToast] = useState<ToastState | null>(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [paletteQuery, setPaletteQuery] = useState("");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const pushToast = useCallback((message: string, tone: ToastTone = "default") => {
    setToast({ message, tone });
    window.setTimeout(() => setToast(null), 4200);
  }, []);

  const toastValue = useMemo(() => ({ pushToast }), [pushToast]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen(true);
        setPaletteQuery("");
      }
      if (e.key === "Escape") {
        setPaletteOpen(false);
        setMobileNavOpen(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const filteredNav = NAV.filter(
    (item) =>
      paletteQuery.trim().length === 0 ||
      item.label.toLowerCase().includes(paletteQuery.toLowerCase()) ||
      item.href.toLowerCase().includes(paletteQuery.toLowerCase()),
  );

  const sidebar = (
    <>
      <div className="flex items-center gap-3 px-2 pb-4">
        <div className="flex h-9 w-9 items-center justify-center rounded-2xl border border-indigo-500/40 bg-indigo-500/20 shadow-lg shadow-indigo-500/30">
          <LayoutDashboard className="h-4 w-4 text-indigo-300" aria-hidden />
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-50">PropSignal</p>
          <p className="text-[11px] text-slate-500">Scoring Control Center</p>
        </div>
      </div>

      <p className="px-2 pb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        Overview
      </p>
      <nav className="flex flex-col gap-1" aria-label="Primary">
        {NAV.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMobileNavOpen(false)}
              className={cn(
                "flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm transition-colors",
                active
                  ? "border border-indigo-500/20 bg-slate-800/90 text-slate-50 shadow-sm shadow-slate-900/40"
                  : "border border-transparent text-slate-400 hover:bg-slate-900/80 hover:text-slate-100",
              )}
            >
              <Icon className={cn("h-3.5 w-3.5", active && "text-indigo-300")} aria-hidden />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <p className="mt-auto px-2 pt-6 font-mono text-[10px] text-slate-600">
        FastAPI @ {API_BASE}
      </p>
    </>
  );

  return (
    <ToastContext.Provider value={toastValue}>
      <div className="min-h-screen bg-slate-950 text-slate-200">
        {mobileNavOpen ? (
          <button
            type="button"
            aria-label="Close navigation"
            className="fixed inset-0 z-40 bg-slate-950/80 backdrop-blur-sm md:hidden"
            onClick={() => setMobileNavOpen(false)}
          />
        ) : null}

        <aside
          className={cn(
            "fixed inset-y-0 left-0 z-50 flex min-h-screen w-64 flex-col border-r border-slate-800/80 bg-gradient-to-b from-slate-950 to-slate-900/60 p-4 transition-transform duration-200 md:translate-x-0",
            mobileNavOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0",
          )}
        >
          <div className="mb-3 flex justify-end md:hidden">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label="Close menu"
              onClick={() => setMobileNavOpen(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          {sidebar}
        </aside>

        <div className="md:ml-64">
          <div className="sticky top-0 z-30 flex items-center gap-2 border-b border-slate-800/80 bg-slate-950/70 px-3 py-2 backdrop-blur-md md:hidden">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label="Open menu"
              onClick={() => setMobileNavOpen(true)}
            >
              <Menu className="h-4 w-4" />
            </Button>
            <span className="text-sm font-medium text-slate-200">PropSignal</span>
          </div>
          {children}
        </div>
      </div>

      {toast ? (
        <div className="fixed bottom-5 right-5 z-[2000] max-w-[min(420px,92vw)]" role={toast.tone === "error" ? "alert" : "status"}>
          <div
            className={cn(
              "rounded-xl border px-3 py-2 text-xs shadow-lg",
              toast.tone === "error"
                ? "border-red-900/60 bg-red-950/90 text-red-100"
                : "border-slate-800/80 bg-slate-900/95 text-slate-200",
            )}
          >
            {toast.message}
          </div>
        </div>
      ) : null}

      {paletteOpen ? (
        <div
          className="fixed inset-0 z-[3000] flex items-start justify-center bg-slate-950/80 px-4 pt-[12vh] backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          aria-label="Command palette"
        >
          <div className="w-full max-w-md space-y-3 rounded-2xl border border-slate-800/80 bg-slate-950 p-4 shadow-[0_18px_60px_rgba(15,23,42,0.9)]">
            <Input
              autoFocus
              placeholder="Jump to tab…"
              value={paletteQuery}
              onChange={(e) => setPaletteQuery(e.target.value)}
            />
            <div className="custom-scroll max-h-[40vh] space-y-1 overflow-auto">
              {filteredNav.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="block rounded-lg border border-transparent bg-slate-900/50 px-3 py-2 text-sm text-slate-200 transition-colors hover:border-indigo-500/30 hover:bg-slate-900/80"
                  onClick={() => setPaletteOpen(false)}
                >
                  {item.label}
                </Link>
              ))}
            </div>
            <Button type="button" variant="ghost" size="sm" onClick={() => setPaletteOpen(false)}>
              Close
            </Button>
          </div>
        </div>
      ) : null}
    </ToastContext.Provider>
  );
}
