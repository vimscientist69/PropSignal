export type ErrorField = {
  field: string;
  reason: string;
};

export type ErrorResponse = {
  code: string;
  message: string;
  field_errors: ErrorField[];
  request_id: string;
};

export type SourceSummary = {
  source: string;
  job_id: number;
  input_path: string;
  status: string;
  records_total: number;
  records_valid: number;
  records_invalid: number;
  started_at: string | null;
  finished_at: string | null;
  validation_status: string | null;
  validation_summary: Record<string, unknown> | null;
};

export type ProfileSummary = {
  preset: string;
  label: string;
  description: string;
};

export type ProfileDetail = {
  preset: string;
  profile_id: string;
  profile_version: string;
  default_weights: Record<string, number>;
  enabled_signals: string[];
  safe_override_bounds: Record<string, { min: number; max: number }>;
};

export type RankingResult = {
  listing_id: number;
  score: number;
  deal_reason: string;
  confidence: number;
  summary: Record<string, unknown>;
  detail_ref: string;
  listing_url?: string | null;
  bedrooms?: number | null;
  bathrooms?: number | null;
  province?: string | null;
  source_site?: string | null;
};

export type RankingResponse = {
  run_id: string;
  resolved_profile: {
    profile_id: string;
    profile_version: string;
  };
  dataset_context: {
    selected_sources: string[];
    records_considered: number;
    last_ingested_at: string | null;
    last_scored_at: string | null;
    model_version: string | null;
    profile_version: string | null;
  };
  results: RankingResult[];
  pagination?: {
    mode: "pagination";
    page: number;
    page_size: number;
    total_count: number;
  };
  top_n?: {
    mode: "top_n";
    top_n_requested: number;
    top_n_returned: number;
  };
};

export type ListingDetail = {
  listing_core: Record<string, unknown>;
  score_summary: Record<string, unknown>;
  diagnostics: Record<string, unknown>;
};

export type RunSummaryItem = {
  run_id: string;
  created_at: string;
  strategy_preset: string;
  profile_id: string;
  profile_row_id: number;
  source_count: number;
  records_considered: number;
  result_count: number;
  latency_ms: number | null;
};

export type RunsListResponse = {
  items: RunSummaryItem[];
  page: number;
  page_size: number;
  total: number;
};

export type RunDetailResponse = {
  run_id: string;
  created_at: string;
  query_fingerprint: string;
  strategy_preset: string;
  profile_id: string;
  profile_row_id: number;
  source_count: number;
  records_considered: number;
  result_count: number;
  request_snapshot: Record<string, unknown>;
  result_window: Record<string, unknown>;
  results: RankingResult[];
  latency_ms: number | null;
};

export type DiagnosticsSummary = {
  api_status: string;
  total_ranking_runs: number;
  total_listings: number;
  ingestion_jobs_by_status: Record<string, number>;
  latest_dataset_validations: Record<string, unknown>[];
};
