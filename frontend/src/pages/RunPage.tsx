import { FormEvent, useEffect, useState } from "react";

import type { ApiClient, Job } from "../api/client";

interface Props {
  client: ApiClient;
  systemId: number;
}

const defaultEvidencePath = import.meta.env.VITE_EVIDENCE_PATH ?? "runtime/evidence";

export function RunPage({ client, systemId }: Props) {
  const [evidencePath, setEvidencePath] = useState(defaultEvidencePath);
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) return undefined;
    const timer = window.setInterval(() => {
      client.getJob(job.id).then(setJob).catch((requestError: Error) => setError(requestError.message));
    }, 3000);
    return () => window.clearInterval(timer);
  }, [client, job]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const started = await client.startIngestion(systemId, evidencePath);
      setJob({
        id: started.job_id,
        system_id: systemId,
        phase: "as-is",
        status: started.status,
        run_id: started.run_id,
        error_message: null,
        started_at: null,
        finished_at: null,
      });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not start the ingestion run.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="page-grid run-grid">
      <article className="panel">
        <p className="eyebrow">New job</p>
        <h2>Run Phase 1 ingestion</h2>
        <p className="muted">The server validates this path against its configured evidence directory.</p>
        <form className="stack-form" onSubmit={submit}>
          <label htmlFor="evidence-path">Server-side evidence path</label>
          <input id="evidence-path" value={evidencePath} onChange={(event) => setEvidencePath(event.target.value)} required />
          <button className="primary-button" type="submit" disabled={submitting}>
            {submitting ? "Starting…" : "Run ingestion"}
          </button>
        </form>
        {error && <p className="error-message" role="alert">{error}</p>}
      </article>
      <JobCard job={job} />
    </section>
  );
}

function JobCard({ job }: { job: Job | null }) {
  if (!job) {
    return <article className="panel empty-state"><h2>No active job</h2><p>Start a run to see its live status here.</p></article>;
  }
  return (
    <article className="panel job-card">
      <p className="eyebrow">Live job status</p>
      <div className="status-line"><h2>Job #{job.id}</h2><StatusBadge status={job.status} /></div>
      <dl>
        <dt>Phase</dt><dd>{job.phase}</dd>
        <dt>Trace ID</dt><dd className="mono">{job.run_id ?? "—"}</dd>
        <dt>Started</dt><dd>{formatDate(job.started_at)}</dd>
        <dt>Finished</dt><dd>{formatDate(job.finished_at)}</dd>
      </dl>
      {job.status === "failed" && <p className="error-message" role="alert">{job.error_message || "The job failed without an error message."}</p>}
      {["queued", "running"].includes(job.status) && <p className="muted">Refreshing every 3 seconds…</p>}
    </article>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return <span className={`status-badge status-${status}`}>{status}</span>;
}

function formatDate(value: string | null) {
  return value ? new Date(value).toLocaleString() : "—";
}
