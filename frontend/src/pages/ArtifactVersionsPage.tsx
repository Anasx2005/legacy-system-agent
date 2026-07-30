import { useEffect, useState } from "react";

import type { ApiClient, ArtifactVersion } from "../api/client";
import { StatusBadge } from "./RunPage";

interface Props { client: ApiClient; systemId: number; }
const modelRepo = import.meta.env.VITE_GITHUB_MODEL_REPO ?? "";

export function ArtifactVersionsPage({ client, systemId }: Props) {
  const [versions, setVersions] = useState<ArtifactVersion[]>([]);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { client.listArtifactVersions(systemId).then(setVersions).catch((requestError: Error) => setError(requestError.message)); }, [client, systemId]);
  return <section className="panel"><div className="panel-heading"><div><p className="eyebrow">Traceability</p><h2>Artifact versions &amp; pull requests</h2></div><span>{versions.length} versions</span></div>
    {error && <p className="error-message">{error}</p>}
    {!error && <div className="table-wrap"><table><thead><tr><th>Version</th><th>Commit</th><th>Phase</th><th>Approval</th><th>Reviewer</th><th>Created</th></tr></thead><tbody>{versions.map((version) => <tr key={version.id}><td>{version.pr_number && modelRepo ? <a href={`https://github.com/${modelRepo}/pull/${version.pr_number}`} target="_blank" rel="noreferrer">PR #{version.pr_number}</a> : "No PR"}</td><td className="mono">{version.commit_sha?.slice(0, 12) ?? "—"}</td><td>{version.phase ?? "—"}</td><td><StatusBadge status={version.approval_status ?? "unknown"} /></td><td>{version.approved_by ?? "—"}</td><td>{formatDate(version.created_at)}</td></tr>)}</tbody></table></div>}
  </section>;
}

function formatDate(value: string | null) { return value ? new Date(value).toLocaleString() : "—"; }
