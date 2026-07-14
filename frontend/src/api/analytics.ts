import { aggregatorClient } from './http';
import type { AnalyticsRange, DeploymentDecision } from './types';
import type { TriggerDeploymentRequest } from './dashboard';
import { triggerDeployment } from './dashboard';

// --- Request types ---

export interface AnalyticsSummaryQuery {
  range?: AnalyticsRange;
}

export interface AnalyticsVolumeQuery {
  range?: AnalyticsRange;
}

export interface AnalyticsDecisionsQuery {
  range?: AnalyticsRange;
}

export interface AnalyticsBlocksQuery {
  range?: AnalyticsRange;
  severity?: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  search?: string;
  page?: number;
  page_size?: number;
}

export interface AnalyticsExportQuery {
  range?: AnalyticsRange;
  format?: 'csv';
}

// --- Response types ---

export interface AnalyticsTrendMetric {
  value: string;
  direction: 'up' | 'down' | 'flat';
}

export interface AnalyticsSummaryResponse {
  totalAnalyzed: number;
  avgRiskScore: number;
  avgConfidence: number;
  totalBlocked: number;
  trends: {
    totalAnalyzed: AnalyticsTrendMetric;
    avgRiskScore: AnalyticsTrendMetric;
    avgConfidence: AnalyticsTrendMetric;
    totalBlocked: AnalyticsTrendMetric;
  };
}

export interface AnalyticsVolumePoint {
  date: string;
  safe: number;
  review: number;
  blocked: number;
}

export interface AnalyticsVolumeResponse {
  range: AnalyticsRange;
  data: AnalyticsVolumePoint[];
}

export interface AnalyticsDecisionDistribution {
  SAFE: number;
  REVIEW: number;
  BLOCK: number;
}

export interface AnalyticsDecisionsResponse {
  range: AnalyticsRange;
  distribution: AnalyticsDecisionDistribution;
}

export interface AnalyticsBlockRecord {
  correlation_id: string;
  time: string;
  repository: string;
  risk_score: number;
  primary_threat: string;
  decision: DeploymentDecision;
  agent_scores: {
    code_risk: number;
    infra_risk: number;
    incident_risk: number;
  };
  details: string;
  recommendations: string[];
}

export interface AnalyticsBlocksResponse {
  items: AnalyticsBlockRecord[];
  total: number;
  page: number;
  page_size: number;
}

export interface SimulateScanRequest extends TriggerDeploymentRequest {}

export interface SimulateScanResponse {
  correlation_id: string;
  status: 'sent';
}


/** GET /analytics/summary — metric cards on analytics page. */
export async function getAnalyticsSummary(
  query: AnalyticsSummaryQuery = {}
): Promise<AnalyticsSummaryResponse> {
  const { data } = await aggregatorClient.get<AnalyticsSummaryResponse>(
    '/analytics/summary',
    { params: query }
  );
  return data;
}


/** GET /analytics/volume — deployment volume bar chart data. */
export async function getAnalyticsVolume(
  query: AnalyticsVolumeQuery = {}
): Promise<AnalyticsVolumeResponse> {
  const { data } = await aggregatorClient.get<AnalyticsVolumeResponse>(
    '/analytics/volume',
    { params: query }
  );
  return data;
}



/** GET /analytics/decisions — decision distribution donut chart data. */
export async function getAnalyticsDecisions(
  query: AnalyticsDecisionsQuery = {}
): Promise<AnalyticsDecisionsResponse> {
  const { data } = await aggregatorClient.get<AnalyticsDecisionsResponse>(
    '/analytics/decisions',
    { params: query }
  );
  return data;
}



/** GET /analytics/blocks — recent high-risk blocked deployments table. */
export async function getAnalyticsBlocks(
  query: AnalyticsBlocksQuery = {}
): Promise<AnalyticsBlocksResponse> {
  const { data } = await aggregatorClient.get<AnalyticsBlocksResponse>(
    '/analytics/blocks',
    { params: query }
  );
  return data;
}



/** GET /analytics/export — download analytics CSV export. */
export async function exportAnalytics(
  query: AnalyticsExportQuery = {}
): Promise<Blob> {
  const { data } = await aggregatorClient.get<Blob>('/analytics/export', {
    params: query,
    responseType: 'blob',
  });
  return data;
}
// --- Proposed endpoints (backend not yet implemented) ---
/**
 * Trigger a deployment scan via the gateway webhook (same pipeline as dashboard).
 * Used by the analytics "Simulate Scan" flow until a dedicated endpoint exists.
 */
export async function simulateScan(
  request: SimulateScanRequest
): Promise<SimulateScanResponse> {
  const result = await triggerDeployment(request);
  return {
    correlation_id: result.correlation_id,
    status: 'sent',
  };
}
