import { useEffect, useRef, useState } from "react";

import { ApiError, api } from "../api/client";
import type { DiscoverJob, DiscoverRegions } from "../api/types";

interface Props {
  /** Called when a job finishes so the dashboard can refresh its data. */
  onCompleted: () => void;
}

/**
 * "Find new contacts" control: no company name needed — searches FCC by
 * grant-date window (all applicants) and keeps only the selected region,
 * reading each match's 731 Responsible Party. This is how new companies get
 * discovered instead of naming clients one at a time.
 */
export function DiscoverPanel({ onCompleted }: Props) {
  const [days, setDays] = useState(3);
  const [regions, setRegions] = useState<DiscoverRegions>("europe");
  const [job, setJob] = useState<DiscoverJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  const busy = job?.status === "pending" || job?.status === "running";

  useEffect(() => {
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, []);

  function poll(jobId: string) {
    pollRef.current = window.setInterval(async () => {
      try {
        const next = await api.getDiscoverJob(jobId);
        setJob(next);
        if (next.status === "completed" || next.status === "failed") {
          if (pollRef.current) window.clearInterval(pollRef.current);
          if (next.status === "completed") onCompleted();
        }
      } catch {
        if (pollRef.current) window.clearInterval(pollRef.current);
      }
    }, 2000);
  }

  async function run(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const started = await api.startDiscover({ days, regions });
      setJob(started);
      poll(started.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to start discovery");
    }
  }

  return (
    <form className="ingest ingest--discover" onSubmit={run}>
      <div className="ingest__row">
        <div className="ingest__field">
          <label htmlFor="days">Last N days</label>
          <input
            id="days"
            type="number"
            min={1}
            max={36500}
            value={days}
            onChange={(e) => setDays(Math.max(1, Number(e.target.value) || 1))}
          />
        </div>

        <div className="ingest__mode" role="group" aria-label="Region">
          <button
            type="button"
            className={`seg ${regions === "europe" ? "seg--on" : ""}`}
            onClick={() => setRegions("europe")}
            disabled={busy}
          >
            Europe
          </button>
          <button
            type="button"
            className={`seg ${regions === "all" ? "seg--on" : ""}`}
            onClick={() => setRegions("all")}
            disabled={busy}
          >
            Worldwide
          </button>
        </div>

        <button type="submit" className="btn btn--primary ingest__run" disabled={busy}>
          {busy ? "Discovering…" : "🔎 Find new contacts"}
        </button>
      </div>

      <div className="ingest__foot">
        <StatusLine job={job} error={error} />
      </div>
    </form>
  );
}

function StatusLine({ job, error }: { job: DiscoverJob | null; error: string | null }) {
  if (error) return <span className="ingest__status ingest__status--err">⚠️ {error}</span>;
  if (!job) {
    return (
      <span className="ingest__status ingest__status--hint">
        No company name needed — scans recent FCC filings from every applicant
        and keeps the selected region.
      </span>
    );
  }

  if (job.status === "failed") {
    return <span className="ingest__status ingest__status--err">⚠️ {job.error ?? "failed"}</span>;
  }
  if (job.status === "completed" && job.report) {
    const r = job.report;
    return (
      <span className="ingest__status ingest__status--ok">
        ✓ {r.date_from} → {r.date_to} ({r.regions}): {r.filings_scanned} filings,{" "}
        {r.companies_touched} companies → {r.contacts_created} new, {r.contacts_merged} merged
        {r.errors.length > 0 && ` (${r.errors.length} errors)`}
      </span>
    );
  }
  return (
    <span className="ingest__status ingest__status--run">
      <span className="spinner" /> {job.status} — scanning recent filings…
    </span>
  );
}
