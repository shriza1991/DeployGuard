/**
 * Utilities for formatting and displaying Analysis Confidence in DeployGuard.
 */

export function normalizeConfidence(value: number | null | undefined): number | null {
  if (value === null || value === undefined || isNaN(value)) {
    return null;
  }
  // Handles decimal scale (0.0 - 1.0) vs integer scale (0 - 100)
  if (value <= 1.0 && value >= 0.0) {
    return Math.round(value * 100);
  }
  return Math.round(Math.min(100, Math.max(0, value)));
}

export type ConfidenceLevel = 'high' | 'medium' | 'low' | 'unknown';

export function getConfidenceLevel(pct: number | null): ConfidenceLevel {
  if (pct === null) return 'unknown';
  if (pct >= 80) return 'high';
  if (pct >= 50) return 'medium';
  return 'low';
}

export function getConfidenceLabel(pct: number | null): string {
  const level = getConfidenceLevel(pct);
  switch (level) {
    case 'high':
      return 'High Confidence';
    case 'medium':
      return 'Medium Confidence';
    case 'low':
      return 'Low Confidence';
    default:
      return 'Unknown Confidence';
  }
}

export function getConfidenceColor(pct: number | null): string {
  const level = getConfidenceLevel(pct);
  switch (level) {
    case 'high':
      return '#10b981'; // Green
    case 'medium':
      return '#f59e0b'; // Amber
    case 'low':
      return '#ef4444'; // Red
    default:
      return '#6b7280'; // Gray
  }
}

export function getDefaultConfidenceFactors(pct: number | null): string[] {
  if (pct === null) return ['Analysis status unknown'];
  if (pct >= 80) {
    return [
      'Complete Git diff evaluated',
      'PR metadata parsed',
      'Deterministic analysis verified',
      'LLM reasoning completed',
    ];
  }
  if (pct >= 50) {
    return [
      'Partial Git diff available',
      'Repository context verified',
      'Rule evaluation completed',
    ];
  }
  return [
    'Limited evidence quality',
    'Metadata or diff incomplete',
    'Analysis fallback engaged',
  ];
}
