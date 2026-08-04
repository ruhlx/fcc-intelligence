import { useMemo, useState } from "react";

import { api } from "./api/client";
import type { ContactFilters } from "./api/types";
import { ContactsTable } from "./components/ContactsTable";
import { Filters } from "./components/Filters";
import { useContacts, useDebounced } from "./hooks/useContacts";
import { useStats } from "./hooks/useStats";

const EMPTY: ContactFilters = { q: "", title: "", country: "", company: "" };

export default function App() {
  const [filters, setFilters] = useState<ContactFilters>(EMPTY);
  const debounced = useDebounced(filters, 300);

  const { contacts, loading, error } = useContacts(debounced);
  const stats = useStats(0);

  const avgPriority = useMemo(() => {
    if (contacts.length === 0) return 0;
    const total = contacts.reduce((sum, c) => sum + c.priority, 0);
    return Math.round(total / contacts.length);
  }, [contacts]);

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

      <section className="stats">
        <StatTile label="Contacts shown" value={loading ? "…" : contacts.length} />
        <StatTile label="Avg priority" value={loading ? "…" : avgPriority} />
        <StatTile label="Companies" value={stats ? stats.companies : "…"} />
        <StatTile label="Filings" value={stats ? stats.filings : "…"} />
      </section>

      <Filters
        filters={filters}
        onChange={setFilters}
        onReset={() => setFilters(EMPTY)}
      />

      <ContactsTable contacts={contacts} loading={loading} error={error} />

      <footer className="footer">
        API: <code>{api.baseUrl}</code>
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
