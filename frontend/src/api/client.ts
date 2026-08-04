import type { Company, Contact, ContactFilters, Filing } from "./types";

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

async function getJson<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${BASE_URL}${path}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value) url.searchParams.set(key, value);
    }
  }
  let resp: Response;
  try {
    resp = await fetch(url.toString(), { headers: { Accept: "application/json" } });
  } catch (cause) {
    throw new ApiError(`Cannot reach API at ${BASE_URL}. Is the backend running?`, 0);
  }
  if (!resp.ok) {
    throw new ApiError(`Request failed (${resp.status}) for ${path}`, resp.status);
  }
  return (await resp.json()) as T;
}

export const api = {
  baseUrl: BASE_URL,

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
