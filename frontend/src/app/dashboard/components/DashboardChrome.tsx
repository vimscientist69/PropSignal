"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import styles from "../dashboard.module.css";

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
  { href: "/dashboard/control", label: "Control Panel" },
  { href: "/dashboard/sources", label: "Source Library" },
  { href: "/dashboard/runs", label: "Runs" },
  { href: "/dashboard/diagnostics", label: "Diagnostics" },
];

export function DashboardChrome({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [toast, setToast] = useState<ToastState | null>(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [paletteQuery, setPaletteQuery] = useState("");

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

  return (
    <ToastContext.Provider value={toastValue}>
      <div className={styles.page}>
        <aside className={styles.sidebarShell}>
          <div className={styles.brand}>PropSignal</div>
          <p className={styles.brandSub}>Scoring Control Center</p>
          <nav className={styles.navStack} aria-label="Primary">
            {NAV.map((item) => {
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={active ? `${styles.navLink} ${styles.navLinkActive}` : styles.navLink}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <p className={styles.kbdHint}>Quick nav: ⌘/Ctrl + K</p>
        </aside>
        {children}
      </div>

      {toast ? (
        <div className={styles.toastHost} role={toast.tone === "error" ? "alert" : "status"}>
          <div
            className={toast.tone === "error" ? `${styles.toast} ${styles.toastError}` : styles.toast}
          >
            {toast.message}
          </div>
        </div>
      ) : null}

      {paletteOpen ? (
        <div
          className={styles.paletteOverlay}
          role="dialog"
          aria-modal="true"
          aria-label="Command palette"
        >
          <div className={styles.palette}>
            <input
              autoFocus
              placeholder="Jump to tab…"
              value={paletteQuery}
              onChange={(e) => setPaletteQuery(e.target.value)}
            />
            <div className={styles.paletteList}>
              {filteredNav.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={styles.paletteItem}
                  onClick={() => setPaletteOpen(false)}
                >
                  {item.label}
                </Link>
              ))}
            </div>
            <button type="button" className={styles.ghostButton} onClick={() => setPaletteOpen(false)}>
              Close
            </button>
          </div>
        </div>
      ) : null}
    </ToastContext.Provider>
  );
}
