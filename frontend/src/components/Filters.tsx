import type { ContactFilters } from "../api/types";

interface Props {
  filters: ContactFilters;
  onChange: (next: ContactFilters) => void;
  onReset: () => void;
}

/**
 * Filter bar. Free-text search (`q`) uses the /search endpoint and, when set,
 * takes precedence over the structured title/country/company filters — so those
 * inputs are disabled while a search term is active (mirrors the API contract).
 */
export function Filters({ filters, onChange, onReset }: Props) {
  const searching = Boolean(filters.q?.trim());
  const set = (patch: Partial<ContactFilters>) => onChange({ ...filters, ...patch });

  return (
    <div className="filters">
      <div className="filters__field filters__field--search">
        <label htmlFor="q">Search</label>
        <input
          id="q"
          type="search"
          placeholder="name, title or email — e.g. cyber"
          value={filters.q ?? ""}
          onChange={(e) => set({ q: e.target.value })}
        />
      </div>

      <div className="filters__field">
        <label htmlFor="title">Title</label>
        <input
          id="title"
          type="text"
          placeholder="Certification"
          value={filters.title ?? ""}
          disabled={searching}
          onChange={(e) => set({ title: e.target.value })}
        />
      </div>

      <div className="filters__field">
        <label htmlFor="country">Country</label>
        <input
          id="country"
          type="text"
          placeholder="Germany"
          value={filters.country ?? ""}
          disabled={searching}
          onChange={(e) => set({ country: e.target.value })}
        />
      </div>

      <div className="filters__field">
        <label htmlFor="company">Company</label>
        <input
          id="company"
          type="text"
          placeholder="u-blox"
          value={filters.company ?? ""}
          disabled={searching}
          onChange={(e) => set({ company: e.target.value })}
        />
      </div>

      <button type="button" className="btn btn--ghost" onClick={onReset}>
        Reset
      </button>
    </div>
  );
}
