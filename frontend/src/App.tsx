import { useEffect, useMemo, useState } from "react";

import { api } from "./api/client";
import type { ContactFilters } from "./api/types";
import { ContactsTable } from "./components/ContactsTable";
import { DiscoverPanel } from "./components/DiscoverPanel";
import { Filters } from "./components/Filters";
import { IngestPanel } from "./components/IngestPanel";
import { useContacts, useDebounced } from "./hooks/useContacts";
import { useStats } from "./hooks/useStats";
import type { ColumnFilters } from "./lib/columnFilters";
import { EMPTY_COLUMN_FILTERS, applyColumnFilters, uniqueSorted } from "./lib/columnFilters";

const EMPTY: ContactFilters = { q: "", title: "", country: "", company: "", category: "" };

export default function App() {
  const [filters, setFilters] = useState<ContactFilters>(EMPTY);
  const [colFilters, setColFilters] = useState<ColumnFilters>(EMPTY_COLUMN_FILTERS);
  const [refreshKey, setRefreshKey] = useState(0);
  const debounced = useDebounced(filters, 300);

  const { contacts, loading, error } = useContacts(debounced, refreshKey);
  const stats = useStats(refreshKey);

  const refresh = () => setRefreshKey((k) => k + 1);

  // A new search/filter/crawl fetches a different set of rows — stale quick
  // filters (e.g. a company name that no longer appears) would just silently
  // hide everything, so reset them whenever the underlying data changes.
  useEffect(() => {
    setColFilters(EMPTY_COLUMN_FILTERS);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(debounced), refreshKey]);

  const options = useMemo(
    () => ({
      names: uniqueSorted(contacts.map((c) => c.full_name)),
      titles: uniqueSorted(contacts.map((c) => c.title)),
      companies: uniqueSorted(contacts.map((c) => c.company.name)),
    }),
    [contacts],
  );

  const visibleContacts = useMemo(
    () => applyColumnFilters(contacts, colFilters),
    [contacts, colFilters],
  );

  const avgPriority = useMemo(() => {
    if (visibleContacts.length === 0) return 0;
    const total = visibleContacts.reduce((sum, c) => sum + c.priority, 0);
    return Math.round(total / visibleContacts.length);
  }, [visibleContacts]);

  return (
    <div className="app">
      <header className="header">
        <div className="header__titles">
          <h1>FCC Regulatory Contact Intelligence</h1>
          <p>Product-compliance &amp; certification contacts from FCC filings.</p>
        </div>
        <a className="btn btn--primary" href={api.contactsCsvUrl()}>
          ↓ Export CSV
        </a>
      </header>

      <h2 className="section-label">Search a specific company</h2>
      <IngestPanel onCompleted={refresh} />

      <h2 className="section-label">Or discover automatically — no company name needed</h2>
      <DiscoverPanel onCompleted={refresh} />

      <section className="stats">
        <StatTile label="Contacts shown" value={loading ? "…" : visibleContacts.length} />
        <StatTile label="Avg priority" value={loading ? "…" : avgPriority} />
        <StatTile label="Companies" value={stats ? stats.companies : "…"} />
        <StatTile label="Filings" value={stats ? stats.filings : "…"} />
      </section>

      <Filters
        filters={filters}
        onChange={setFilters}
        onReset={() => setFilters(EMPTY)}
      />

      <ContactsTable
        contacts={visibleContacts}
        totalBeforeColumnFilters={contacts.length}
        loading={loading}
        error={error}
        filters={colFilters}
        onFiltersChange={setColFilters}
        options={options}
      />

      <footer className="footer">
        API: <code>{api.baseUrl || "same origin"}</code>
      </footer>
    </div>
  );
}

function StatTile({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="stat-tile">
      <div className="stat-tile__value">{value}</div>
      <div className="stat-tile__label">{label}</div>
    </div>
  );
}
