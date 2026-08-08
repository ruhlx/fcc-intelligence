import type { Contact, ContactCategory } from "../api/types";
import type { ColumnFilters } from "../lib/columnFilters";
import { EMPTY_COLUMN_FILTERS, hasActiveColumnFilter } from "../lib/columnFilters";
import { CategoryBadge } from "./CategoryBadge";
import { PriorityBar } from "./PriorityBar";

const CATEGORY_OPTIONS: { value: ContactCategory | ""; label: string }[] = [
  { value: "", label: "All" },
  { value: "CERTIFICATION_MANAGER", label: "Certification" },
  { value: "REGULATORY_AFFAIRS", label: "Regulatory" },
  { value: "PRODUCT_COMPLIANCE", label: "Compliance" },
  { value: "PRODUCT_SECURITY", label: "Security" },
  { value: "QUALITY", label: "Quality" },
  { value: "ENGINEERING", label: "Engineering" },
  { value: "EXECUTIVE", label: "Executive" },
  { value: "IGNORE", label: "Other" },
];

interface FilterOptions {
  names: string[];
  titles: string[];
  companies: string[];
}

interface Props {
  /** Already column-filtered rows to render. */
  contacts: Contact[];
  /** Total rows before column filters were applied (for the empty-state message). */
  totalBeforeColumnFilters: number;
  loading: boolean;
  error: string | null;
  filters: ColumnFilters;
  onFiltersChange: (next: ColumnFilters) => void;
  options: FilterOptions;
}

export function ContactsTable({
  contacts,
  totalBeforeColumnFilters,
  loading,
  error,
  filters,
  onFiltersChange,
  options,
}: Props) {
  const set = <K extends keyof ColumnFilters>(key: K, value: ColumnFilters[K]) =>
    onFiltersChange({ ...filters, [key]: value });

  if (error) {
    return <div className="state state--error">⚠️ {error}</div>;
  }
  if (loading) {
    return (
      <div className="state">
        Loading contacts… <span className="state__muted">(the free-tier API may take
        ~30s to wake up on first load)</span>
      </div>
    );
  }
  if (totalBeforeColumnFilters === 0) {
    return (
      <div className="state">
        No contacts match. Run the pipeline first, e.g.
        <code> python -m scripts.run_pipeline u-blox</code>
      </div>
    );
  }

  return (
    <div className="table-wrap">
      {hasActiveColumnFilter(filters) && (
        <div className="table-filters-bar">
          {contacts.length} of {totalBeforeColumnFilters} shown — quick filters active
          <button
            type="button"
            className="btn btn--ghost table-filters-bar__clear"
            onClick={() => onFiltersChange(EMPTY_COLUMN_FILTERS)}
          >
            Clear
          </button>
        </div>
      )}
      <table className="table">
        <thead>
          <tr>
            <th>Priority</th>
            <th>Name</th>
            <th>Title</th>
            <th>Category</th>
            <th>Company</th>
            <th>Contact</th>
            <th className="num">Filings</th>
          </tr>
          <tr className="table__filterrow">
            <th>
              <select
                value={filters.priority}
                onChange={(e) => set("priority", e.target.value as ColumnFilters["priority"])}
              >
                <option value="">All</option>
                <option value="high">High (≥70)</option>
                <option value="medium">Medium (40–69)</option>
                <option value="low">Low (&lt;40)</option>
              </select>
            </th>
            <th>
              <select value={filters.name} onChange={(e) => set("name", e.target.value)}>
                <option value="">All</option>
                {options.names.map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </th>
            <th>
              <select value={filters.title} onChange={(e) => set("title", e.target.value)}>
                <option value="">All</option>
                {options.titles.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </th>
            <th>
              <select
                value={filters.category}
                onChange={(e) => set("category", e.target.value as ColumnFilters["category"])}
              >
                {CATEGORY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </th>
            <th>
              <select value={filters.company} onChange={(e) => set("company", e.target.value)}>
                <option value="">All</option>
                {options.companies.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </th>
            <th>
              <select
                value={filters.contact}
                onChange={(e) => set("contact", e.target.value as ColumnFilters["contact"])}
              >
                <option value="">All</option>
                <option value="has_email">Has email</option>
                <option value="no_email">No email</option>
                <option value="has_phone">Has phone</option>
                <option value="no_phone">No phone</option>
              </select>
            </th>
            <th>
              <select
                value={filters.filings}
                onChange={(e) => set("filings", e.target.value as ColumnFilters["filings"])}
              >
                <option value="">All</option>
                <option value="1">1</option>
                <option value="2+">2+</option>
              </select>
            </th>
          </tr>
        </thead>
        <tbody>
          {contacts.length === 0 ? (
            <tr>
              <td colSpan={7} className="table__empty">
                No contacts match these quick filters.
              </td>
            </tr>
          ) : (
            contacts.map((c) => (
              <tr key={c.id}>
                <td>
                  <PriorityBar score={c.priority} />
                </td>
                <td className="cell--name">{c.full_name}</td>
                <td className="cell--muted">{c.title ?? "—"}</td>
                <td>
                  <CategoryBadge category={c.category} />
                </td>
                <td>
                  <div className="cell--company">{c.company.name}</div>
                  <div className="cell--muted">{c.company.country ?? ""}</div>
                </td>
                <td>
                  {c.email ? (
                    <a href={`mailto:${c.email}`}>{c.email}</a>
                  ) : (
                    <span className="cell--muted">no email</span>
                  )}
                  {c.phone && <div className="cell--muted">{c.phone}</div>}
                </td>
                <td className="num" title={c.fcc_ids.join(", ")}>
                  {c.fcc_ids.length}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
