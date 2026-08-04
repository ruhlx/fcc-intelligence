import { useEffect, useRef, useState } from "react";

import { ApiError, api } from "../api/client";
import type { IngestJob, LlmProvider } from "../api/types";

interface Props {
  /** Called when a job finishes so the dashboard can refresh its data. */
  onCompleted: () => void;
}

const KEY_STORAGE = "fcc_llm_api_key";
const PROVIDER_STORAGE = "fcc_llm_provider";

/**
 * "Build the database" control: enter a company + LLM key, click Run, and the
 * backend crawls FCC, extracts contacts, and stores them. Polls job status.
 */
export function IngestPanel({ onCompleted }: Props) {
  const [company, setCompany] = useState("");
  const [provider, setProvider] = useState<LlmProvider>(
    (localStorage.getItem(PROVIDER_STORAGE) as LlmProvider) || "gemini",
  );
  const [apiKey, setApiKey] = useState(localStorage.getItem(KEY_STORAGE) ?? "");
  const [remember, setRemember] = useState(Boolean(localStorage.getItem(KEY_STORAGE)));
  const [job, setJob] = useState<IngestJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  const busy = job?.status === "pending" || job?.status === "running";

  useEffect(() => {
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, []);

  function persist() {
    localStorage.setItem(PROVIDER_STORAGE, provider);
    if (remember && apiKey) localStorage.setItem(KEY_STORAGE, apiKey);
    else localStorage.removeItem(KEY_STORAGE);
  }

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
    persist();
    try {
      const started = await api.startIngest({
        company: company.trim(),
        provider,
        api_key: apiKey.trim() || undefined,
      });
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

        <div className="ingest__field">
          <label htmlFor="provider">LLM provider</label>
          <select
            id="provider"
            value={provider}
            onChange={(e) => setProvider(e.target.value as LlmProvider)}
          >
            <option value="gemini">Google Gemini</option>
            <option value="openai">OpenAI</option>
          </select>
        </div>

        <div className="ingest__field ingest__field--grow">
          <label htmlFor="apiKey">{provider === "gemini" ? "Gemini" : "OpenAI"} API key</label>
          <input
            id="apiKey"
            type="password"
            placeholder="paste your API key"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            autoComplete="off"
          />
        </div>

        <button type="submit" className="btn btn--primary ingest__run" disabled={busy}>
          {busy ? "Running…" : "▶ Run"}
        </button>
      </div>

      <div className="ingest__foot">
        <label className="ingest__remember">
          <input
            type="checkbox"
            checked={remember}
            onChange={(e) => setRemember(e.target.checked)}
          />
          Remember key in this browser
        </label>
        <StatusLine job={job} error={error} />
      </div>
    </form>
  );
}

function StatusLine({ job, error }: { job: IngestJob | null; error: string | null }) {
  if (error) return <span className="ingest__status ingest__status--err">⚠️ {error}</span>;
  if (!job) return <span className="ingest__status ingest__status--hint">Crawls FCC, extracts contacts with the LLM, and stores them.</span>;

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
