import { aggregatorClient } from './http';
import type {
  DecisionResponse,
  FinalDecision,
  PendingDecisionResponse,
} from './types';
import { isFinalDecision } from './types';

// --- Request types ---

export interface GetDecisionResult {
  status: 200 | 202;
  data: DecisionResponse;
}

export interface PollDecisionOptions {
  intervalMs?: number;
  timeoutMs?: number;
  onPending?: (response: PendingDecisionResponse) => void;
}

export interface DeploymentDetail extends FinalDecision {
  repository?: string;
  commit_message?: string;
  author?: string;
  pull_request_title?: string;
  pull_request_body?: string;
  branch?: string;
  commit_sha?: string;
  status?: string;
}

export type PipelineStageStatus = 'completed' | 'active' | 'pending' | 'failed';

export interface PipelineTimelineStage {
  id: string;
  label: string;
  status: PipelineStageStatus;
  timestamp?: string;
  details: string;
}

export interface DeploymentTimelineResponse {
  correlation_id: string;
  stages: PipelineTimelineStage[];
}

// --- Existing endpoints ---

/**
 * GET /api/aggregator/decision/{correlation_id}
 * Returns 200 (final), 202 (pending), or throws on 404.
 */
export async function getDecision(
  correlationId: string
): Promise<GetDecisionResult> {
  const response = await aggregatorClient.get<DecisionResponse>(
    `/decision/${encodeURIComponent(correlationId)}`,
    { validateStatus: (status) => status === 200 || status === 202 }
  );

  return {
    status: response.status as 200 | 202,
    data: response.data,
  };
}

/** Fetch final decision only; returns null while pending. */
export async function getFinalDecision(
  correlationId: string
): Promise<FinalDecision | null> {
  const result = await getDecision(correlationId);
  if (result.status === 200 && isFinalDecision(result.data)) {
    return result.data;
  }
  return null;
}

/** Poll until final decision, timeout, or 404. */
export async function pollDecisionUntilComplete(
  correlationId: string,
  options: PollDecisionOptions = {}
): Promise<FinalDecision> {
  const {
    intervalMs = 3_000,
    timeoutMs = 15_000,
    onPending,
  } = options;

  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    const result = await getDecision(correlationId);

    if (result.status === 200 && isFinalDecision(result.data)) {
      return result.data;
    }

    if (result.status === 202) {
      onPending?.(result.data as PendingDecisionResponse);
    }

    await sleep(intervalMs);
  }

  throw new Error(
    `Decision polling timed out after ${timeoutMs}ms for correlation_id=${correlationId}`
  );
}

/** GET /deployments/{correlation_id} — full deployment with webhook metadata. */
export async function getDeployment(
  correlationId: string
): Promise<DeploymentDetail> {
  const { data } = await aggregatorClient.get<DeploymentDetail>(
    `/deployments/${encodeURIComponent(correlationId)}`
  );
  return data;
}



/** GET /deployments/{correlation_id}/timeline — pipeline stage timestamps. */
export async function getDeploymentTimeline(
  correlationId: string
): Promise<DeploymentTimelineResponse> {
  const { data } = await aggregatorClient.get<DeploymentTimelineResponse>(
    `/deployments/${encodeURIComponent(correlationId)}/timeline`
  );
  return data;
}



function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
