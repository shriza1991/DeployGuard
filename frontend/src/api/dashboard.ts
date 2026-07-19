import { aggregatorClient, gatewayClient, incidentHistoryClient } from './http';
import type {
  AggregatorHealthResponse,
  DeploymentDecision,
  GitHubWebhookPayload,
  IncidentHistoryAgentHealthResponse,
  PaginatedResponse,
  TimePeriod,
  TriggerWebhookResponse,
} from './types';

// --- Request types ---

export interface TriggerDeploymentRequest {
  repository: string;
  pullRequestTitle: string;
  pullRequestBody: string;
  commitMessage: string;
  author?: string;
}

export interface ListDeploymentsQuery {
  project?: string;
  since?: string;
  decision?: DeploymentDecision;
  page?: number;
  page_size?: number;
}

export interface DeploymentMetricsQuery {
  project?: string;
  period?: TimePeriod;
}

export interface AgentStatusItem {
  name: string;
  status: 'online' | 'offline' | 'degraded';
  latency_ms: number;
  region?: string;
  version?: string | null;
  uptime?: number | null;
  analysis_count?: number | null;
  last_run_timestamp?: string | null;
  average_confidence?: number | null;
  cpu_usage?: number | null;
  memory_usage?: number | null;
}

export interface AgentStatusResponse {
  agents: AgentStatusItem[];
}

export interface DeploymentSummary {
  correlation_id: string;
  repository: string;
  branch?: string;
  decision?: DeploymentDecision;
  overall_score?: number;
  overall_confidence?: number;
  severity?: string;
  generated_at?: string;
  status: 'pending' | 'complete';
}

export interface DeploymentMetricsResponse {
  total: number;
  safe: number;
  review: number;
  blocked: number;
  avgRisk: number;
  avgConfidence: number;
  safePercentage?: number;
  blockedPercentage?: number;
  totalProgress?: number;
  totalTrend?: number | string;
  riskLevel?: 'LOW' | 'MEDIUM' | 'HIGH';
}

// --- Existing endpoints ---

/** Build a GitHub webhook payload from dashboard form fields. */
export function buildWebhookPayload(
  request: TriggerDeploymentRequest
): GitHubWebhookPayload {
  const repoName = request.repository.split('/').pop() ?? request.repository;

  return {
    action: 'opened',
    repository: {
      name: repoName,
      full_name: request.repository,
    },
    pull_request: {
      title: request.pullRequestTitle,
      body: request.pullRequestBody,
      user: { login: request.author ?? 'deployguard-gui' },
    },
    head_commit: {
      message: request.commitMessage,
      author: { name: request.author ?? 'developer' },
    },
  };
}

/** POST /api/gateway/webhook/github — trigger a deployment through the pipeline. */
export async function triggerDeployment(
  request: TriggerDeploymentRequest
): Promise<TriggerWebhookResponse> {
  const payload = buildWebhookPayload(request);
  const { data } = await gatewayClient.post<TriggerWebhookResponse>(
    '/webhook/github',
    payload
  );
  return data;
}

/** GET /api/aggregator/health — aggregator service liveness. */
export async function getAggregatorHealth(): Promise<AggregatorHealthResponse> {
  const { data } = await aggregatorClient.get<AggregatorHealthResponse>(
    '/health'
  );
  return data;
}

/**
 * GET /api/incident-history/health — incident-history agent health.
 * Requires nginx/proxy route; not exposed in default docker-compose.
 */
export async function getIncidentHistoryAgentHealth(): Promise<IncidentHistoryAgentHealthResponse> {
  const { data } =
    await incidentHistoryClient.get<IncidentHistoryAgentHealthResponse>(
      '/health'
    );
  return data;
}



/** GET /deployments — paginated deployment list for dashboard table. */
export async function listDeployments(
  query: ListDeploymentsQuery = {}
): Promise<PaginatedResponse<DeploymentSummary>> {
  const { data } = await aggregatorClient.get<
    PaginatedResponse<DeploymentSummary>
  >('/deployments', { params: query });
  return data;
}

/** GET /deployments/metrics — aggregate metrics for dashboard cards. */
export async function getDeploymentMetrics(
  query: DeploymentMetricsQuery = {}
): Promise<DeploymentMetricsResponse> {
  const { data } = await aggregatorClient.get<DeploymentMetricsResponse>(
    '/deployments/metrics',
    { params: query }
  );
  return data;
}


/** GET /agents/status — agent fleet health for dashboard status panel. */
export async function getAgentStatus(): Promise<AgentStatusResponse> {
  const { data } = await aggregatorClient.get<AgentStatusResponse>(
    '/agents/status'
  );
  return data;
}

/**
 * Poll GET /decision/{correlation_id} until final decision or timeout.
 * Delegates to deployments API; re-exported here for dashboard convenience.
 */
export { pollDecisionUntilComplete, getDecision } from './deployments';
