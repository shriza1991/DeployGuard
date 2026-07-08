/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export type Severity = 'CRIT' | 'HIGH' | 'MED' | 'LOW';

export type IncidentStatus = 'BLOCKED' | 'MITIGATED' | 'RESOLVED';

export interface LinkedDeployment {
  id: string;
  triggeredBy: string;
}

export interface Incident {
  id: string;
  title: string;
  severity: Severity;
  status: IncidentStatus;
  timestamp: string; // ISO string or display string
  repository: string;
  version: string;
  similarity: number; // percentage (e.g. 94)
  aiSummary: string;
  vulnerabilityType: string;
  detectedPattern: string;
  mitigationActions: string[];
  linkedDeployment?: LinkedDeployment;
  affectedClusters: string[];
  rollbackRequired: boolean;
}
