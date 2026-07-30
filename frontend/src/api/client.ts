export type JobStatus = "queued" | "running" | "succeeded" | "failed";

export interface Job {
  id: number;
  system_id: number;
  phase: string;
  status: JobStatus;
  run_id: string | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface ModelElementIndex {
  id: number;
  layer: string;
  archimate_type: string;
  name: string;
  git_path: string;
  current_commit: string | null;
  updated_at: string | null;
}

export interface EvidenceCitation {
  source_type?: string;
  locator: string;
  excerpt?: string;
}

export interface Relationship {
  target_id: string;
  type: string;
}

export interface ModelElementDetail {
  id: string;
  layer: string;
  archimate_type: string;
  name: string;
  documentation: string;
  confidence: string;
  evidence: EvidenceCitation[];
  relationships: Relationship[];
}

export interface ArtifactVersion {
  id: number;
  run_id: string | null;
  commit_sha: string | null;
  pr_number: number | null;
  phase: string | null;
  approval_status: string | null;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string | null;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

export class ApiClient {
  constructor(
    private readonly baseUrl: string,
    private readonly getApiKey: () => string,
  ) {}

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const apiKey = this.getApiKey().trim();
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...(apiKey ? { "X-API-Key": apiKey } : {}),
        ...init.headers,
      },
    });

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new ApiError(body.detail ?? `Request failed (${response.status}).`, response.status);
    }
    return response.json() as Promise<T>;
  }

  startIngestion(systemId: number, evidencePath: string) {
    return this.request<{ job_id: number; run_id: string; status: JobStatus }>(
      `/systems/${systemId}/ingest`,
      { method: "POST", body: JSON.stringify({ evidence_path: evidencePath }) },
    );
  }

  getJob(jobId: number) {
    return this.request<Job>(`/jobs/${jobId}`);
  }

  listElements(systemId: number) {
    return this.request<ModelElementIndex[]>(`/systems/${systemId}/elements`);
  }

  getElement(elementId: number) {
    return this.request<ModelElementDetail>(`/elements/${elementId}`);
  }

  listArtifactVersions(systemId: number) {
    return this.request<ArtifactVersion[]>(`/systems/${systemId}/artifact-versions`);
  }
}
