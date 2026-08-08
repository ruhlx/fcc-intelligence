// Response shapes mirrored from the FastAPI Pydantic schemas (app/services/schemas.py).

export interface Company {
  id: number;
  name: string;
  country: string | null;
  website: string | null;
}

export interface Filing {
  id: number;
  fcc_id: string;
  product_name: string | null;
  filing_date: string | null;
  filing_url: string | null;
  company_id: number;
}

// Every classified category is stored (not just the "core compliance" ones) —
// category filtering happens at query time via GET /contacts?category=.
export type ContactCategory =
  | "CERTIFICATION_MANAGER"
  | "PRODUCT_COMPLIANCE"
  | "REGULATORY_AFFAIRS"
  | "PRODUCT_SECURITY"
  | "QUALITY"
  | "ENGINEERING"
  | "EXECUTIVE"
  | "IGNORE";

export interface Contact {
  id: number;
  full_name: string;
  email: string | null;
  phone: string | null;
  title: string | null;
  category: ContactCategory;
  confidence: number;
  priority: number;
  company: Company;
  fcc_ids: string[];
}

export interface ContactFilters {
  q?: string;
  title?: string;
  country?: string;
  company?: string;
  category?: ContactCategory | "";
}

export type LlmProvider = "openai" | "gemini";

export interface IngestRequest {
  company: string;
  provider?: LlmProvider;
  api_key?: string;
  extract_pdfs?: boolean;
  max_filings?: number;
}

export interface IngestReport {
  applications: number;
  documents: number;
  contacts_created: number;
  contacts_merged: number;
  errors: string[];
}

export type JobStatus = "pending" | "running" | "completed" | "failed";

export interface IngestJob {
  id: string;
  company: string;
  status: JobStatus;
  created_at: string;
  report: IngestReport | null;
  error: string | null;
}

export type DiscoverRegions = "europe" | "all";

export interface DiscoverRequest {
  days?: number;
  regions?: string;
  extract_pdfs?: boolean;
  max_filings?: number;
}

export interface DiscoverReport {
  date_from: string;
  date_to: string;
  regions: string;
  filings_scanned: number;
  companies_touched: number;
  documents: number;
  contacts_created: number;
  contacts_merged: number;
  errors: string[];
}

export interface DiscoverJob {
  id: string;
  /** Synthetic label, e.g. "discovery:europe:3d" — not a real company name. */
  company: string;
  status: JobStatus;
  created_at: string;
  report: DiscoverReport | null;
  error: string | null;
}
