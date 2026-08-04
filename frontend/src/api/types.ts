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

export type ContactCategory =
  | "CERTIFICATION_MANAGER"
  | "PRODUCT_COMPLIANCE"
  | "REGULATORY_AFFAIRS"
  | "PRODUCT_SECURITY";

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
}
