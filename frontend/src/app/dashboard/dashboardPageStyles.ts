/** PropFlux-style Tailwind classes shared across dashboard tabs. */
export const styles = {
  main: "mx-auto w-full max-w-[1600px] space-y-4 px-3 py-4 md:space-y-6 md:px-4 md:py-6",
  topHeader: "flex flex-col gap-4 md:flex-row md:items-start md:justify-between",
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
  rowBetween: "flex flex-wrap items-center justify-between gap-2",
  sectionTitle: "text-sm font-semibold text-slate-50",
  sectionHint: "text-xs text-slate-500",
  blockTitle: "text-[11px] font-semibold uppercase tracking-wide text-slate-500",
  filterBar: "flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end",
  filterField: "flex min-w-0 flex-col gap-1.5 sm:w-44",
  filterFieldGrow: "flex min-w-0 flex-1 flex-col gap-1.5 sm:min-w-[14rem]",
  filterLabel: "text-[11px] font-semibold uppercase tracking-wide text-slate-500",
  bottomGrid: "grid min-w-0 gap-4 lg:grid-cols-[1.65fr_1fr]",
  resultsPanel:
    "min-w-0 rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900/80 p-4 shadow-[0_18px_60px_rgba(15,23,42,0.9)] space-y-3",
  sourcesTableWrap:
    "custom-scroll max-h-[min(52vh,520px)] overflow-x-auto overflow-y-auto overscroll-x-contain rounded-xl border border-slate-800/80 bg-slate-950/30",
  detailPanel:
    "min-w-0 overflow-hidden rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900/80 p-4 shadow-[0_18px_60px_rgba(15,23,42,0.9)] space-y-3",
  rowCountBadge:
    "inline-flex items-center rounded-full border border-slate-800/80 bg-slate-900/80 px-2 py-0.5 font-mono text-[10px] text-slate-400",
  dataTableWrap: "custom-scroll max-h-[min(52vh,520px)] overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/30",
  dataTable:
    "w-full border-collapse text-xs [&_th]:sticky [&_th]:top-0 [&_th]:z-10 [&_th]:whitespace-nowrap [&_th]:border-b [&_th]:border-slate-800/80 [&_th]:bg-slate-950/95 [&_th]:px-2 [&_th]:py-2 [&_th]:text-left [&_th]:text-[11px] [&_th]:font-semibold [&_th]:uppercase [&_th]:tracking-wide [&_th]:text-slate-500 [&_td]:border-b [&_td]:border-slate-800/50 [&_td]:px-2 [&_td]:py-2 [&_td]:align-middle [&_td]:text-slate-300 [&_tr:hover_td]:bg-slate-900/40",
  sourcesDataTable: "w-max min-w-full",
  tableRow: "cursor-pointer transition-colors",
  selectedRow: "bg-slate-900/90 shadow-sm shadow-indigo-500/10 [&>td]:bg-transparent",
  cellMono: "whitespace-nowrap font-mono text-[11px] text-slate-400",
  cellPath: "min-w-[18rem] max-w-none whitespace-nowrap font-mono text-[11px] text-slate-500",
  pathPanel:
    "rounded-xl border border-slate-800/80 bg-slate-950/30 p-3 [&>p]:mt-1.5 [&>p]:break-all [&>p]:font-mono [&>p]:text-[11px] [&>p]:leading-relaxed [&>p]:text-slate-300",
  cellHighlight: "font-semibold text-indigo-400",
  sourceLink:
    "text-left text-sm font-medium text-indigo-300 transition-colors hover:text-indigo-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
  chip: "inline-flex rounded-full border border-slate-700 bg-slate-900/80 px-2 py-0.5 font-mono text-[10px] text-slate-400",
  detailBlock:
    "rounded-xl border border-slate-800/80 bg-black/40 p-3 [&>h4]:mb-2 [&>h4]:text-[11px] [&>h4]:font-semibold [&>h4]:uppercase [&>h4]:tracking-wide [&>h4]:text-slate-500",
  detailSections: "custom-scroll max-h-[min(56vh,560px)] space-y-3 overflow-auto",
  // Control panel–specific (kept for re-export compatibility)
  mainGrid: "grid min-w-0 gap-4 lg:grid-cols-[1.55fr_1fr]",
  controlPanel:
    "overflow-hidden rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900/80 shadow-[0_18px_60px_rgba(15,23,42,0.9)]",
  actions: "flex flex-wrap items-center gap-2",
  card: "rounded-xl border border-slate-800/80 bg-slate-950/30 p-3 space-y-3",
  sourceList: "grid grid-cols-1 gap-2 md:grid-cols-2",
  error: "rounded-xl border border-red-900/40 bg-red-950/30 px-3 py-2 text-xs text-red-200",
  sourceItem:
    "flex min-w-0 cursor-pointer items-center gap-3 overflow-hidden rounded-xl border border-slate-800/80 bg-slate-950/60 px-3 py-2.5 transition-colors hover:bg-slate-900/80 has-[:checked]:border-indigo-500/40 has-[:checked]:bg-slate-900/90 has-[:checked]:shadow-sm has-[:checked]:shadow-indigo-500/10",
  sourceItemBody:
    "flex min-w-0 flex-1 flex-col gap-1 md:flex-row md:items-center md:justify-between md:gap-3",
  sourceItemTitle: "min-w-0 break-words text-sm font-medium leading-snug text-slate-200 md:truncate",
  sourceItemMeta:
    "min-w-0 break-words text-[11px] leading-snug text-slate-500 md:max-w-[58%] md:truncate md:text-right",
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
  sidePanel:
    "min-w-0 overflow-hidden rounded-2xl border border-slate-800/80 bg-gradient-to-br from-slate-950 via-slate-950 to-slate-900/80 p-4 shadow-[0_18px_60px_rgba(15,23,42,0.9)]",
  sidePanelHeader: "space-y-1",
  sidePanelContent: "mt-4 min-w-0 space-y-4",
  sidePanelBody: "min-w-0 space-y-4",
  metaGrid:
    "grid min-w-0 grid-cols-1 gap-3 text-xs text-slate-400 md:grid-cols-2 [&_strong]:text-slate-200 [&_code]:break-all [&_code]:font-mono [&_code]:text-[11px] [&_code]:text-indigo-300/90",
  metaField: "min-w-0 overflow-hidden rounded-lg border border-slate-800/60 bg-slate-950/40 px-2.5 py-2",
  metaFieldValue: "mt-1 break-words font-medium text-slate-200",
  exportSection: "space-y-4 sm:col-span-2",
  exportGroup: "space-y-2",
  exportStack: "flex flex-col gap-1.5",
  exportBtn: "h-auto min-h-8 w-full justify-start whitespace-normal px-3 py-1.5 text-left text-[11px] leading-snug",
  columnToggles:
    "flex flex-wrap gap-3 text-[11px] text-slate-500 [&_label]:inline-flex [&_label]:cursor-pointer [&_label]:items-center [&_label]:gap-1.5",
  listingsDataTable: "min-w-[1100px]",
  tableCellWrap:
    "!whitespace-normal max-w-[220px] text-[11px] leading-snug text-slate-400 [&_span]:line-clamp-2",
  tableActionsCol: "w-[1%] whitespace-nowrap",
  sortBtn:
    "inline-flex items-center gap-0.5 bg-transparent p-0 text-[11px] font-semibold uppercase tracking-wide text-slate-500 transition-colors hover:text-indigo-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
  chipWarn: "border-amber-900/50 text-amber-200/90",
  rowActions: "flex flex-nowrap items-center gap-1",
  rowActionBtn: "h-7 shrink-0 px-2 text-[10px]",
  skeleton: "h-4 animate-pulse rounded-md bg-slate-800/80",
  urlRow: "mb-2 flex flex-wrap items-center gap-2 text-xs [&_a]:text-indigo-400 [&_a]:underline",
  comparePicker: "flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-end",
  comparePickerField: "flex min-w-0 flex-1 flex-col gap-1.5 sm:min-w-[14rem] sm:max-w-md",
  compareDiff: "space-y-4",
  compareSummary: "grid grid-cols-2 gap-3 sm:grid-cols-4",
  compareSection: "space-y-2",
  diffAdded: "font-mono text-[11px] text-emerald-400",
  diffRemoved: "font-mono text-[11px] text-rose-300",
  runsTableWrap:
    "custom-scroll max-h-[min(52vh,520px)] overflow-x-auto overflow-y-auto overscroll-x-contain rounded-xl border border-slate-800/80 bg-slate-950/30",
  runsDataTable: "w-max min-w-full",
  runIdCell: "font-mono text-[11px] text-indigo-300/90",
  metaInline: "text-xs text-slate-400 [&_code]:font-mono [&_code]:text-[11px] [&_code]:text-indigo-300/90",
  exportLinkGrid: "flex max-w-lg flex-col gap-1.5 sm:max-w-xl",
} as const;

export const jsonTreeStyles = {
  tree: "font-mono text-[11px] leading-relaxed text-slate-200",
  key: "text-slate-500",
  toggle:
    "mr-1 rounded border border-slate-700 bg-slate-900/80 px-1.5 py-0.5 text-[10px] text-slate-300 transition-colors hover:border-indigo-500/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
  row: "border-l border-slate-800/80 pl-2",
  empty: "italic text-slate-600",
} as const;

export const inputClass =
  "w-full rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500/40";

export {
  selectClass,
  Select,
  type SelectProps,
  /** @deprecated Use Select */
  selectClass as selectFilterClass,
} from "@/components/ui/select";

export const checkboxClass =
  "h-3.5 w-3.5 rounded border-slate-700 bg-slate-900 text-indigo-400 accent-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500";
