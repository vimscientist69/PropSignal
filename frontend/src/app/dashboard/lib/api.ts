import type { ErrorResponse, ListingDetail } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function isErrorResponsePayload(value: unknown): value is ErrorResponse {
  if (!value || typeof value !== "object") {
    return false;
  }
  const o = value as Record<string, unknown>;
  return (
    typeof o.code === "string" &&
    typeof o.message === "string" &&
    typeof o.request_id === "string" &&
    Array.isArray(o.field_errors)
  );
}

/** Thrown when the API returns a JSON error envelope (Week 3 §4.4). */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly fieldErrors: ErrorResponse["field_errors"];
  readonly requestId: string;

  constructor(status: number, envelope: ErrorResponse) {
    super(envelope.message);
    this.name = "ApiError";
    this.status = status;
    this.code = envelope.code;
    this.fieldErrors = envelope.field_errors;
    this.requestId = envelope.request_id;
  }

  /** Full text for banners / toasts (includes field_errors when present). */
  formatted(): string {
    const lines: string[] = [this.message];
    if (this.fieldErrors.length > 0) {
      lines.push("", "Field details:");
      for (const fe of this.fieldErrors) {
        lines.push(`  • ${fe.field}: ${fe.reason}`);
      }
    }
    lines.push("", `Code: ${this.code} · Request ID: ${this.requestId} · HTTP ${this.status}`);
    return lines.join("\n");
  }
}

/** Use in catch blocks so ApiError and network errors both render well. */
export function formatThrownApiError(reason: unknown): string {
  if (reason instanceof ApiError) {
    return reason.formatted();
  }
  if (reason instanceof Error && reason.message.trim()) {
    return reason.message.trim();
  }
  if (typeof reason === "string" && reason.trim()) {
    return reason.trim();
  }
  return "Request failed.";
}

/** Human-readable message for thrown fetch failures (network, DNS, CORS, etc.). */
export function formatFetchFailure(reason: unknown): string {
  if (reason instanceof Error && reason.message.trim()) {
    return reason.message.trim();
  }
  if (typeof reason === "string" && reason.trim()) {
    return reason.trim();
  }
  return "Network request failed.";
}

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch (reason) {
    const detail = formatFetchFailure(reason);
    throw new Error(
      `Cannot reach API at ${API_BASE} (${detail}). Is the backend running and CORS allowing this origin?`,
    );
  }
  if (!response.ok) {
    let raw: unknown;
    try {
      raw = await response.json();
    } catch {
      raw = null;
    }
    if (isErrorResponsePayload(raw)) {
      throw new ApiError(response.status, raw);
    }
    const fallback =
      raw && typeof raw === "object" && typeof (raw as { message?: unknown }).message === "string"
        ? String((raw as { message: string }).message)
        : `Request failed with status ${response.status}`;
    throw new Error(fallback);
  }
  return (await response.json()) as T;
}

export async function fetchListingDetailsForRun(
  runId: string,
  listingIds: number[],
): Promise<Map<number, ListingDetail>> {
  const map = new Map<number, ListingDetail>();
  await Promise.all(
    listingIds.map(async (id) => {
      const d = await fetchJson<ListingDetail>(`/api/v1/rankings/${runId}/listings/${id}`);
      map.set(id, d);
    }),
  );
  return map;
}

export function sourcesQuery(status?: string, q?: string): string {
  const params = new URLSearchParams();
  if (status) {
    params.set("status", status);
  }
  if (q) {
    params.set("q", q);
  }
  const qs = params.toString();
  return qs ? `/api/v1/datasets/sources?${qs}` : "/api/v1/datasets/sources";
}
