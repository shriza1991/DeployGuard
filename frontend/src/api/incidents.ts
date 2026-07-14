import { aggregatorClient } from './http';
import type { PaginatedResponse } from './types';

// --- Request types ---

export type IncidentSeverity = 'low' | 'medium' | 'high' | 'critical';

export interface ListIncidentsQuery {
  search?: string;
  severity?: IncidentSeverity;
  repo?: string;
  since?: string;
  page?: number;
  page_size?: number;
}

export interface SimilaritySearchRequest {
  text: string;
}

export interface CreateIncidentRequest {
  title: string;
  description: string;
  severity: IncidentSeverity;
  outcome: string;
  service: string;
  environment: string;
  root_cause?: string;
  rollback?: boolean;
  tags?: string[];
}

// --- Response types ---

export interface IncidentRecord {
  incident_id: string;
  title: string;
  description: string;
  severity: IncidentSeverity;
  outcome: string;
  service: string;
  environment: string;
  root_cause?: string;
  rollback?: boolean;
  timestamp?: string;
  tags?: string[];
  metadata?: Record<string, unknown>;
}

export interface SimilarIncidentMatch {
  incident_id: string;
  title: string;
  description: string;
  severity: IncidentSeverity;
  outcome: string;
  service: string;
  environment: string;
  similarity: number;
  root_cause?: string;
  rollback?: boolean;
  timestamp?: string;
}

export interface SimilaritySearchResponse {
  query: string;
  matches: SimilarIncidentMatch[];
}

export interface CreateIncidentResponse {
  incident: IncidentRecord;
}

// --- Proposed endpoints (backend not yet implemented) ---

/** GET /incidents — paginated incident archive. */
export async function listIncidents(
  query: ListIncidentsQuery = {}
): Promise<PaginatedResponse<IncidentRecord>> {
  const { data } = await aggregatorClient.get<
    PaginatedResponse<IncidentRecord>
  >('/incidents', { params: query });
  return data;
}

/** GET /incidents/{incident_id} — single incident detail. */
export async function getIncident(
  incidentId: string
): Promise<IncidentRecord> {
  const { data } = await aggregatorClient.get<IncidentRecord>(
    `/incidents/${encodeURIComponent(incidentId)}`
  );
  return data;
}

/** POST /incidents/similarity — semantic similarity search playground. */
export async function searchSimilarIncidents(
  request: SimilaritySearchRequest
): Promise<SimilaritySearchResponse> {
  const { data } = await aggregatorClient.post<SimilaritySearchResponse>(
    '/incidents/similarity',
    request
  );
  return data;
}

/** POST /incidents — create a manual incident report. */
export async function createIncident(
  request: CreateIncidentRequest
): Promise<CreateIncidentResponse> {
  const { data } = await aggregatorClient.post<CreateIncidentResponse>(
    '/incidents',
    request
  );
  return data;
}
