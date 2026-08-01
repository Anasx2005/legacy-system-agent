import { FormEvent, useEffect, useMemo, useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";

import { ApiClient } from "./api/client";
import { ArtifactVersionsPage } from "./pages/ArtifactVersionsPage";
import { ElementsPage } from "./pages/ElementsPage";
import { OverviewPage } from "./pages/OverviewPage";
import { RunPage } from "./pages/RunPage";

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";
const configuredApiKey = import.meta.env.VITE_API_KEY ?? "";
const fallbackSystemId = Number(import.meta.env.VITE_SYSTEM_ID ?? "0");
const storedSystemId = Number(sessionStorage.getItem("system-id") ?? "0");

export function App() {
  const [apiKey, setApiKey] = useState(() => sessionStorage.getItem("api-key") ?? configuredApiKey);
  const [systemId, setSystemId] = useState<number | null>(
    storedSystemId || fallbackSystemId || null,
  );
  const [systemError, setSystemError] = useState<string | null>(null);
  const client = useMemo(
    () => new ApiClient(configuredBaseUrl.replace(/\/$/, ""), () => apiKey),
    [apiKey],
  );

  useEffect(() => {
    let active = true;
    setSystemError(null);
    client.getConfiguredSystem()
      .then((system) => {
        if (active) {
          sessionStorage.setItem("system-id", String(system.id));
          setSystemId(system.id);
        }
      })
      .catch((error: Error) => {
        if (!active) return;
        setSystemError(error.message);
      });
    return () => { active = false; };
  }, [client]);

  function saveApiKey(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    sessionStorage.setItem("api-key", apiKey);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">LS</span>
          <div>
            <strong>Legacy System</strong>
            <small>Model control plane</small>
          </div>
        </div>
        <nav aria-label="Main navigation">
          <NavLink to="/overview">Overview</NavLink>
          <NavLink to="/run">Run ingestion</NavLink>
          <NavLink to="/elements">Model elements</NavLink>
          <NavLink to="/versions">Versions &amp; PRs</NavLink>
        </nav>
        <form className="api-key-form" onSubmit={saveApiKey}>
          <label htmlFor="api-key">API key</label>
          <input
            id="api-key"
            type="password"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            placeholder="Enter X-API-Key"
            autoComplete="off"
          />
          <button type="submit" className="secondary-button">Save for this session</button>
        </form>
      </aside>
      <main>
        <header className="page-header">
          <div>
            <p className="eyebrow">Phase 1 · As-is model</p>
            <h1>Architecture recovery workspace</h1>
          </div>
          <span className="system-chip">{systemId ? `System #${systemId}` : "System unavailable"}</span>
        </header>
        {systemId ? (
          <Routes>
            <Route path="/overview" element={<OverviewPage />} />
            <Route path="/run" element={<RunPage client={client} systemId={systemId} />} />
            <Route path="/elements/:elementId?" element={<ElementsPage client={client} systemId={systemId} />} />
            <Route path="/versions" element={<ArtifactVersionsPage client={client} systemId={systemId} />} />
            <Route path="*" element={<Navigate to="/overview" replace />} />
          </Routes>
        ) : (
          <section className="panel empty-state">
            <h2>Connecting to the configured system</h2>
            <p>{systemError ?? "Loading the backend configuration…"}</p>
          </section>
        )}
      </main>
    </div>
  );
}
