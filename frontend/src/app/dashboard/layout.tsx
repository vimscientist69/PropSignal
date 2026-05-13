import type { Metadata } from "next";

import { DashboardChrome } from "./components/DashboardChrome";

export const metadata: Metadata = {
  title: "PropSignal Dashboard",
  description: "Ranking workbench, sources, runs, and diagnostics",
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return <DashboardChrome>{children}</DashboardChrome>;
}
