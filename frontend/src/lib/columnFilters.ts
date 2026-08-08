import type { Contact, ContactCategory } from "../api/types";

export type PriorityBucket = "" | "high" | "medium" | "low";
export type FilingsBucket = "" | "1" | "2+";
export type ContactPresence = "" | "has_email" | "no_email" | "has_phone" | "no_phone";

/** One quick, client-side filter per table column — applied to already-fetched rows. */
export interface ColumnFilters {
  priority: PriorityBucket;
  name: string;
  title: string;
  category: ContactCategory | "";
  company: string;
  contact: ContactPresence;
  filings: FilingsBucket;
}

export const EMPTY_COLUMN_FILTERS: ColumnFilters = {
  priority: "",
  name: "",
  title: "",
  category: "",
  company: "",
  contact: "",
  filings: "",
};

export function hasActiveColumnFilter(f: ColumnFilters): boolean {
  return Object.values(f).some((v) => v !== "");
}

export function applyColumnFilters(contacts: Contact[], f: ColumnFilters): Contact[] {
  return contacts.filter((c) => {
    if (f.name && c.full_name !== f.name) return false;
    if (f.title && (c.title ?? "") !== f.title) return false;
    if (f.category && c.category !== f.category) return false;
    if (f.company && c.company.name !== f.company) return false;

    if (f.priority === "high" && c.priority < 70) return false;
    if (f.priority === "medium" && (c.priority < 40 || c.priority >= 70)) return false;
    if (f.priority === "low" && c.priority >= 40) return false;

    if (f.contact === "has_email" && !c.email) return false;
    if (f.contact === "no_email" && c.email) return false;
    if (f.contact === "has_phone" && !c.phone) return false;
    if (f.contact === "no_phone" && c.phone) return false;

    if (f.filings === "1" && c.fcc_ids.length !== 1) return false;
    if (f.filings === "2+" && c.fcc_ids.length < 2) return false;

    return true;
  });
}

/** Sorted, deduplicated non-empty values — used to populate the Name/Title/Company selects. */
export function uniqueSorted(values: (string | null | undefined)[]): string[] {
  return Array.from(new Set(values.filter((v): v is string => Boolean(v)))).sort((a, b) =>
    a.localeCompare(b),
  );
}
