import type {
  Company,
  Contact,
  ContactFilters,
  Filing,
  IngestJob,
  IngestRequest,
} from "./types";

const BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/**
 * Fetch with automatic retry for cold starts. Render's free tier sleeps after
 * ~15 min idle; the first request then fails (network error) or 502/503 while
 * the service wakes (~30-60s). We retry those transient failures so the UI
 * self-heals instead of showing a hard "cannot reach API" error.
 */
async function fetchWithWake(url: string, init?: RequestInit): Promise<Response> {
  const delaysMs = [1000, 2000, 4000, 6000, 8000, 10000]; // ~31s of retries
  for (let attempt = 0; attempt <= delaysMs.length; attempt++) {
    try {
      const resp = await fetch(url, init);
      // 502/503/504 are the gateway's "still waking" responses — retry them.
      if (resp.status >= 502 && resp.status <= 504 && attempt < delaysMs.length) {
        await sleep(delaysMs[attempt]);
        continue;
      }
      return resp;
    } catch {
      if (attempt < delaysMs.length) {
        await sleep(delaysMs[attempt]);
        continue;
      }
    }
  }
  throw new ApiError(
    `Cannot reach API at ${BASE_URL} after several retries. The server may be waking up — try again in a moment.`,
    0,
  );
}

async function getJson<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${BASE_URL}${path}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value) url.searchParams.set(key, value);
    }
  }
  const resp = await fetchWithWake(url.toString(), {
    headers: { Accept: "application/json" },
  });
  if (!resp.ok) {
    throw new ApiError(`Request failed (${resp.status}) for ${path}`, resp.status);
  }
  return (await resp.json()) as T;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const resp = await fetchWithWake(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    let detail = `Request failed (${resp.status})`;
    try {
      const data = (await resp.json()) as { detail?: string };
      if (data.detail) detail = data.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, resp.status);
  }
  return (await resp.json()) as T;
}

export const api = {
  baseUrl: BASE_URL,

  startIngest(req: IngestRequest): Promise<IngestJob> {
    return postJson<IngestJob>("/ingest", req);
  },

  getIngestJob(jobId: string): Promise<IngestJob> {
    return getJson<IngestJob>(`/ingest/${jobId}`);
  },

  /** Search/list contacts. Uses /search for free text, /contacts for filters. */
  async listContacts(filters: ContactFilters): Promise<Contact[]> {
    const q = filters.q?.trim();
    if (q) {
      return getJson<Contact[]>("/search", { q });
    }
    return getJson<Contact[]>("/contacts", {
      title: filters.title ?? "",
      country: filters.country ?? "",
      company: filters.company ?? "",
    });
  },

  listCompanies(): Promise<Company[]> {
    return getJson<Company[]>("/companies");
  },

  listFilings(): Promise<Filing[]> {
    return getJson<Filing[]>("/filings");
  },

  contactsCsvUrl(): string {
    return `${BASE_URL}/export/contacts.csv`;
  },
};
