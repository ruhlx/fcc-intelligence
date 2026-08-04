import { useEffect, useRef, useState } from "react";

import { ApiError, api } from "../api/client";
import type { IngestJob } from "../api/types";

interface Props {
  /** Called when a job finishes so the dashboard can refresh its data. */
  onCompleted: () => void;
}

/**
 * "Build the database" control: enter a company, click Run. The backend crawls
 * FCC, extracts contacts with Gemini (using the server's `GEMINI_API_KEY`), and
 * stores them. Polls job status and refreshes the table when done.
 */
export function IngestPanel({ onCompleted }: Props) {
  const [company, setCompany] = useState("");
  const [job, setJob] = useState<IngestJob | null>(null);
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
        const next = await api.getIngestJob(jobId);
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
      const started = await api.startIngest({ company: company.trim(), provider: "gemini" });
      setJob(started);
      poll(started.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to start ingestion");
    }
  }

  return (
    <form className="ingest" onSubmit={run}>
      <div className="ingest__row">
        <div className="ingest__field ingest__field--grow">
          <label htmlFor="company">Company / applicant to crawl</label>
          <input
            id="company"
            type="text"
            placeholder="e.g. u-blox"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            required
          />
        </div>

        <button
          type="submit"
          className="btn btn--primary ingest__run"
          disabled={busy || !company.trim()}
        >
          {busy ? "Running…" : "▶ Run"}
        </button>
      </div>

      <div className="ingest__foot">
        <StatusLine job={job} error={error} />
      </div>
    </form>
  );
}

function StatusLine({ job, error }: { job: IngestJob | null; error: string | null }) {
  if (error) return <span className="ingest__status ingest__status--err">⚠️ {error}</span>;
  if (!job) {
    return (
      <span className="ingest__status ingest__status--hint">
        Crawls FCC, extracts contacts with Gemini, and stores them.
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
        ✓ {job.company}: {r.applications} filings, {r.documents} docs →{" "}
        {r.contacts_created} new, {r.contacts_merged} merged
        {r.errors.length > 0 && ` (${r.errors.length} errors)`}
      </span>
    );
  }
  return (
    <span className="ingest__status ingest__status--run">
      <span className="spinner" /> {job.status} — crawling “{job.company}”…
    </span>
  );
}
