import type { Contact } from "../api/types";
import { CategoryBadge } from "./CategoryBadge";
import { PriorityBar } from "./PriorityBar";

interface Props {
  contacts: Contact[];
  loading: boolean;
  error: string | null;
}

export function ContactsTable({ contacts, loading, error }: Props) {
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
  if (contacts.length === 0) {
    return (
      <div className="state">
        No contacts match. Run the pipeline first, e.g.
        <code> python -m scripts.run_pipeline u-blox</code>
      </div>
    );
  }

  return (
    <div className="table-wrap">
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
        </thead>
        <tbody>
          {contacts.map((c) => (
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
          ))}
        </tbody>
      </table>
    </div>
  );
}
