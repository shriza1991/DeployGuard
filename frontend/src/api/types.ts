/** Shared backend-aligned types from FRONTEND_API_MAP.md */

export type DeploymentDecision = 'SAFE' | 'REVIEW' | 'BLOCK';

export type DeploymentSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type AgentSeverity = 'low' | 'medium' | 'high' | 'critical';

export type AgentName = 'code-risk' | 'infra-risk' | 'incident-history';

export type TimePeriod = '24h' | '7d' | '30d';

export type AnalyticsRange = '7d' | '14d' | '30d' | '90d';

export type DeploymentStatus = 'pending' | 'complete' | 'failed';

// --- Gateway ---

export interface GitHubUser {
  login?: string;
  name?: string;
}

export interface GitHubRepository {
  name?: string;
  full_name?: string;
}

export interface GitHubHeadCommit {
  message?: string;
  id?: string;
  author?: GitHubUser;
}

export interface GitHubPullRequest {
  title?: string;
  body?: string;
  url?: string;
  user?: GitHubUser;
}

export interface GitHubWebhookPayload {
  repository?: GitHubRepository | null;
  action?: string | null;
  sender?: Record<string, unknown> | null;
  head_commit?: GitHubHeadCommit | null;
  pull_request?: GitHubPullRequest | null;
}

export interface TriggerWebhookResponse {
  status: 'sent';
  correlation_id: string;
  topic: string;
}

// --- Aggregator health ---

export interface AggregatorHealthResponse {
  status: 'healthy';
}

export interface IncidentHistoryAgentHealthResponse {
  status: 'ok';
  agent: 'incident-history';
  qdrant_available: boolean;
  embedding_provider: string;
  llm_provider: string;
}

// --- Agent / decision models ---

export interface LLMResult {
  provider?: string | null;
  available?: boolean | null;
  summary?: string | null;
  risk_reasoning?: string[];
  recommendations?: string[];
  confidence?: number | null;
}

export interface SimilarIncidentRef {
  incident_id: string;
  similarity: number;
  severity: string;
  outcome: string;
  title: string;
  description?: string;
  service?: string;
  environment?: string;
}

export interface AgentResult {
  agent: AgentName | string;
  correlation_id: string;
  score: number;
  severity: AgentSeverity | string;
  confidence: number;
  reasons: string[];
  recommendations: string[];
  metadata: Record<string, unknown>;
  similar_incidents?: SimilarIncidentRef[];
  llm?: LLMResult | null;
}

export interface FinalDecision {
  correlation_id: string;
  overall_score: number;
  overall_confidence: number;
  decision: DeploymentDecision;
  severity: DeploymentSeverity;
  agents: Partial<Record<AgentName, AgentResult>> & Record<string, AgentResult>;
  summary: string;
  reasons: string[];
  recommendations: string[];
  generated_at: string;
}

export interface PendingDecisionResponse {
  status: 'pending';
  correlation_id: string;
  collected_agents: string[];
  message: string;
}

export type DecisionResponse = FinalDecision | PendingDecisionResponse;

export interface ApiErrorDetail {
  detail: string;
}

export function isFinalDecision(
  response: DecisionResponse
): response is FinalDecision {
  return 'decision' in response && typeof response.decision === 'string';
}

export function isPendingDecision(
  response: DecisionResponse
): response is PendingDecisionResponse {
  return 'status' in response && response.status === 'pending';
}

// --- Pagination ---

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
