import { Link } from "react-router-dom";

export function OverviewPage() {
  return (
    <section className="page-grid overview-grid">
      <article className="hero-card">
        <p className="eyebrow">Evidence → model → review</p>
        <h2>Recover an auditable view of your legacy system.</h2>
        <p>
          Start an evidence-ingestion run, inspect every generated ArchiMate element,
          and follow approved model versions back to their pull requests.
        </p>
        <Link className="primary-button" to="/run">Start an ingestion run</Link>
      </article>
      <article className="info-card">
        <h3>1. Run</h3>
        <p>Send the configured evidence folder to the backend and monitor the job live.</p>
      </article>
      <article className="info-card">
        <h3>2. Review</h3>
        <p>Browse elements by layer and inspect cited source evidence.</p>
      </article>
      <article className="info-card">
        <h3>3. Approve</h3>
        <p>Track the pull request and approval state for every model version.</p>
      </article>
    </section>
  );
}
