import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import type { ApiClient, ModelElementDetail, ModelElementIndex } from "../api/client";

interface Props { client: ApiClient; systemId: number; }

const layerOrder = ["motivation", "strategy", "business", "application", "technology"];
const evidenceRepo = import.meta.env.VITE_EVIDENCE_GITHUB_REPO ?? "";
const evidenceRef = import.meta.env.VITE_EVIDENCE_GITHUB_REF ?? "main";

export function ElementsPage({ client, systemId }: Props) {
  const { elementId } = useParams();
  const navigate = useNavigate();
  const [elements, setElements] = useState<ModelElementIndex[]>([]);
  const [details, setDetails] = useState<Record<number, ModelElementDetail>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    client.listElements(systemId)
      .then(async (result) => {
        setElements(result);
        const loadedDetails = await Promise.all(result.map(async (element) => [element.id, await client.getElement(element.id)] as const));
        setDetails(Object.fromEntries(loadedDetails));
      })
      .catch((requestError: Error) => setError(requestError.message));
  }, [client, systemId]);

  const selectedId = Number(elementId);
  const selected = elements.find((element) => element.id === selectedId) ?? null;
  const selectedDetail = selected ? details[selected.id] : null;
  const modelIdToIndexId = useMemo(
    () => new Map(Object.entries(details).map(([indexId, detail]) => [detail.id, Number(indexId)])),
    [details],
  );
  const grouped = layerOrder.map((layer) => [layer, elements.filter((element) => element.layer === layer)] as const);

  return (
    <section className="elements-layout">
      <article className="panel element-list-panel">
        <div className="panel-heading"><div><p className="eyebrow">Model browser</p><h2>Elements by layer</h2></div><span>{elements.length} total</span></div>
        {error && <p className="error-message">{error}</p>}
        {!error && elements.length === 0 && <p className="muted">No approved elements are indexed yet.</p>}
        {grouped.map(([layer, items]) => items.length > 0 && (
          <section key={layer} className="layer-group">
            <h3>{layer}</h3>
            {items.map((element) => (
              <button key={element.id} className={`element-row ${element.id === selectedId ? "selected" : ""}`} onClick={() => navigate(`/elements/${element.id}`)}>
                <span>{element.name}</span><small>{element.archimate_type}</small>
              </button>
            ))}
          </section>
        ))}
      </article>
      <ElementDetail element={selected} detail={selectedDetail} onNavigate={(id) => navigate(`/elements/${id}`)} modelIdToIndexId={modelIdToIndexId} />
    </section>
  );
}

function ElementDetail({ element, detail, onNavigate, modelIdToIndexId }: { element: ModelElementIndex | null; detail: ModelElementDetail | null; onNavigate: (id: number) => void; modelIdToIndexId: Map<string, number> }) {
  if (!element) return <article className="panel empty-state"><h2>Select an element</h2><p>Choose an element from the model browser to inspect evidence and relationships.</p></article>;
  if (!detail) return <article className="panel empty-state"><h2>Loading {element.name}…</h2></article>;
  return (
    <article className="panel element-detail">
      <p className="eyebrow">{detail.layer} · {detail.archimate_type}</p>
      <h2>{detail.name}</h2>
      <p className="muted">Confidence: <strong>{detail.confidence}</strong></p>
      <section><h3>Documentation</h3><p>{detail.documentation || "No documentation was supplied."}</p></section>
      <section><h3>Evidence citations</h3>
        {detail.evidence.map((citation, index) => <EvidenceRow key={`${citation.locator}-${index}`} locator={citation.locator} sourceType={citation.source_type} excerpt={citation.excerpt} />)}
      </section>
      <section><h3>Relationships</h3>
        {detail.relationships.length === 0 ? <p className="muted">No relationships recorded.</p> : <ul className="relationship-list">{detail.relationships.map((relationship) => {
          const relatedId = modelIdToIndexId.get(relationship.target_id);
          return <li key={`${relationship.type}-${relationship.target_id}`}><span className="relationship-type">{relationship.type}</span>{relatedId ? <button onClick={() => onNavigate(relatedId)}>{relationship.target_id}</button> : <span>{relationship.target_id}</span>}</li>;
        })}</ul>}
      </section>
    </article>
  );
}

function EvidenceRow({ locator, sourceType, excerpt }: { locator: string; sourceType?: string; excerpt?: string }) {
  const [filePath, fragment] = locator.split("#", 2);
  const url = evidenceRepo && filePath ? `https://github.com/${evidenceRepo}/blob/${evidenceRef}/${filePath}${fragment ? `#${fragment}` : ""}` : undefined;
  return <div className="evidence-row"><strong>{sourceType || "evidence"}</strong>{url ? <a href={url} target="_blank" rel="noreferrer">{locator}</a> : <code>{locator}</code>}{excerpt && <p>{excerpt}</p>}</div>;
}
