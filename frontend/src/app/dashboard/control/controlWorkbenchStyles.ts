/** PropFlux-style Tailwind classes for the control panel (control tab only). */
export const styles = {
  main: "mx-auto w-full max-w-[1600px] space-y-4 px-3 py-4 md:space-y-6 md:px-4 md:py-6",
  topHeader: "flex flex-col gap-4 md:flex-row md:items-start md:justify-between",
  envBadge: "", // use LiveBadge component instead
  title: "text-lg font-semibold tracking-tight text-slate-50 md:text-xl",
  subTitle: "max-w-prose text-xs text-slate-400 md:text-sm",
  topStats: "grid grid-cols-2 gap-3 sm:min-w-[200px]",
  statTile:
    "rounded-xl border border-slate-800/80 bg-slate-950/30 px-3 py-2 grid gap-0.5 [&>span]:text-[11px] [&>span]:text-slate-500 [&>strong]:font-mono [&>strong]:text-sm [&>strong]:text-slate-100",
  errorBanner:
    "sticky top-0 z-10 space-y-3 rounded-xl border border-red-900/50 bg-red-950/40 px-4 py-3 text-xs text-red-100 shadow-lg",
  errorBannerTitle: "text-xs font-semibold text-red-50",
  errorMultiline: "mt-1 whitespace-pre-wrap break-words font-mono text-[11px] font-medium text-red-100/90",
  mutedLabel: "text-xs text-slate-500",
  mainGrid: "grid gap-4 lg:grid-cols-[1.55fr_1fr]",
  controlPanel:
    "overflow-hidden rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900/80 shadow-[0_18px_60px_rgba(15,23,42,0.9)]",
  rowBetween: "flex flex-wrap items-center justify-between gap-2",
  sectionTitle: "text-sm font-semibold text-slate-50",
  actions: "flex flex-wrap items-center gap-2",
  ghostButton: "", // use Button variant ghost
  sectionHint: "text-xs text-slate-500",
  card: "rounded-xl border border-slate-800/80 bg-slate-950/30 p-3 space-y-3",
  blockTitle: "text-[11px] font-semibold uppercase tracking-wide text-slate-500",
  sourceList: "grid gap-2 sm:grid-cols-2",
  error: "rounded-xl border border-red-900/40 bg-red-950/30 px-3 py-2 text-xs text-red-200",
  sourceItem:
    "flex cursor-pointer items-center gap-3 rounded-xl border border-slate-800/80 bg-slate-950/60 px-3 py-2.5 transition-colors hover:bg-slate-900/80 has-[:checked]:border-indigo-500/40 has-[:checked]:bg-slate-900/90 has-[:checked]:shadow-sm has-[:checked]:shadow-indigo-500/10",
  sourceItemBody: "flex min-w-0 flex-1 items-center justify-between gap-4",
  sourceItemTitle: "truncate text-sm font-medium text-slate-200",
  sourceItemMeta: "shrink-0 text-right text-[11px] text-slate-500",
  statusGrid: "grid gap-2 sm:grid-cols-2 lg:grid-cols-3",
  statusCell:
    "rounded-xl border border-slate-800/80 bg-slate-950/60 p-3 [&>strong]:text-sm [&>strong]:text-slate-200 [&>p]:mt-1 [&>p]:text-[11px] [&>p]:text-slate-500",
  grid: "grid gap-2 sm:grid-cols-2 lg:grid-cols-3",
  overrideGrid: "grid gap-3 sm:grid-cols-2",
  overrideItem: "grid gap-1.5 text-xs text-slate-400 [&>span]:text-[11px]",
  inline: "flex flex-wrap items-center gap-4",
  radio: "flex items-center gap-2 text-xs text-slate-300",
  stickyActions:
    "sticky bottom-0 -mx-4 border-t border-slate-800/80 bg-gradient-to-t from-slate-950 via-slate-950/95 to-transparent px-4 pb-1 pt-3",
  primaryButton: "", // use Button variant primary
  sidePanel:
    "overflow-hidden rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900/80 shadow-[0_18px_60px_rgba(15,23,42,0.9)] p-4",
  sidePanelBody: "space-y-4",
  metaGrid:
    "grid gap-3 sm:grid-cols-2 text-xs text-slate-400 [&_strong]:text-slate-200 [&_code]:break-all [&_code]:font-mono [&_code]:text-[11px] [&_code]:text-indigo-300/90",
  metaField: "rounded-lg border border-slate-800/60 bg-slate-950/40 px-2.5 py-2",
  exportSection: "space-y-4 sm:col-span-2",
  exportGroup: "space-y-2",
  exportStack: "flex flex-col gap-1.5",
  exportBtn: "h-auto min-h-8 w-full justify-start whitespace-normal px-3 py-1.5 text-left text-[11px] leading-snug",
  exportGrid: "flex flex-col gap-1.5 sm:col-span-2",
  secondaryButton: "", // use Button variant outline size sm
  bottomGrid: "grid gap-4 lg:grid-cols-[1.65fr_1fr]",
  resultsPanel:
    "overflow-hidden rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900/80 shadow-[0_18px_60px_rgba(15,23,42,0.9)] p-4 space-y-3",
  columnToggles:
    "flex flex-wrap gap-3 text-[11px] text-slate-500 [&_label]:inline-flex [&_label]:cursor-pointer [&_label]:items-center [&_label]:gap-1.5",
  dataTableWrap: "custom-scroll max-h-[min(52vh,520px)] overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/30",
  dataTable:
    "w-full min-w-[1100px] border-collapse text-xs [&_th]:sticky [&_th]:top-0 [&_th]:z-10 [&_th]:whitespace-nowrap [&_th]:border-b [&_th]:border-slate-800/80 [&_th]:bg-slate-950/95 [&_th]:px-2 [&_th]:py-2 [&_th]:text-left [&_th]:text-[11px] [&_th]:font-semibold [&_th]:uppercase [&_th]:tracking-wide [&_th]:text-slate-500 [&_td]:whitespace-nowrap [&_td]:border-b [&_td]:border-slate-800/50 [&_td]:px-2 [&_td]:py-2 [&_td]:align-middle [&_td]:text-slate-300 [&_tr:hover_td]:bg-slate-900/40",
  tableCellWrap:
    "!whitespace-normal max-w-[220px] text-[11px] leading-snug text-slate-400 [&_span]:line-clamp-2",
  tableRow: "transition-colors",
  tableActionsCol: "w-[1%] whitespace-nowrap",
  sortBtn:
    "inline-flex items-center gap-0.5 bg-transparent p-0 text-[11px] font-semibold uppercase tracking-wide text-slate-500 transition-colors hover:text-indigo-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
  selectedRow: "bg-slate-900/90 [&>td]:bg-transparent",
  chip: "inline-flex rounded-full border border-slate-700 bg-slate-900/80 px-2 py-0.5 font-mono text-[10px] text-slate-400",
  chipWarn: "border-amber-900/50 text-amber-200/90",
  rowActions: "flex flex-nowrap items-center gap-1",
  rowActionBtn: "h-7 shrink-0 px-2 text-[10px]",
  detailPanel:
    "overflow-hidden rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900/80 shadow-[0_18px_60px_rgba(15,23,42,0.9)] p-4 space-y-3",
  skeleton: "h-4 animate-pulse rounded-md bg-slate-800/80",
  urlRow: "mb-2 flex flex-wrap items-center gap-2 text-xs [&_a]:text-indigo-400 [&_a]:underline",
  detailSections: "custom-scroll max-h-[min(56vh,560px)] space-y-3 overflow-auto",
  detailBlock:
    "rounded-xl border border-slate-800/80 bg-black/40 p-3 [&>h4]:mb-2 [&>h4]:text-[11px] [&>h4]:font-semibold [&>h4]:uppercase [&>h4]:tracking-wide [&>h4]:text-slate-500",
} as const;

export const inputClass =
  "w-full rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500/40";

export const selectClass =
  "w-full rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm text-slate-100 outline-none focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500/40";

export const checkboxClass =
  "h-3.5 w-3.5 rounded border-slate-700 bg-slate-900 text-indigo-400 accent-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500";
