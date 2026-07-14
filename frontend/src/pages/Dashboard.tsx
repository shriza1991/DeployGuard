import React, { useCallback, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  triggerDeployment,
  getAggregatorHealth,
  getAgentStatus,
  getDeploymentMetrics,
  listDeployments,
  type DeploymentSummary,
  type TriggerDeploymentRequest,
} from '../api/dashboard';
import { getDecision } from '../api/deployments';
import { isFinalDecision } from '../api/types';
import type { FinalDecision } from '../api/types';
import {
  Shield,
  Play,
  Loader2,
  ArrowRight,
  Search,
  Sliders,
  ChevronDown,
  Bell,
  Calendar,
  TrendingUp,
  ChevronLeft,
  ChevronRight,
  Check,
  X,
  AlertCircle,
} from 'lucide-react';

import './Dashboard.css';

// ── types ──────────────────────────────────────────────────────────────────

/** Lightweight view model kept in component state. */
interface DeploymentRow {
  correlation_id: string;
  repository: string;
  branch?: string;
  commit_message?: string;
  status: 'pending' | 'complete' | 'failed';
  decision?: 'SAFE' | 'REVIEW' | 'BLOCK';
  overall_score?: number;
  overall_confidence?: number;
  severity?: string;
  generated_at?: string;
}

// ── constants ──────────────────────────────────────────────────────────────

const POLL_INTERVAL_MS = 3_000;
const POLL_TIMEOUT_MS = 60_000;

// ── helpers ─────────────────────────────────────────────────────────────────

function rowFromDecision(
  correlationId: string,
  decision: FinalDecision,
  partial: Partial<DeploymentRow> = {},
): DeploymentRow {
  return {
    correlation_id: correlationId,
    repository: partial.repository ?? decision.correlation_id,
    branch: partial.branch,
    commit_message: partial.commit_message,
    status: 'complete',
    decision: decision.decision,
    overall_score: decision.overall_score,
    overall_confidence: decision.overall_confidence,
    severity: decision.severity,
    generated_at: decision.generated_at,
  };
}

function getDateRange(period: '24h' | '7d' | '30d') {
  const end = new Date();
  const start = new Date(end);
  const days = period === '24h' ? 1 : period === '7d' ? 7 : 30;
  start.setDate(end.getDate() - days);

  return { start, end };
}

function formatDateRange(period: '24h' | '7d' | '30d') {
  const { start, end } = getDateRange(period);
  const formatter = new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: '2-digit',
    year: 'numeric',
  });

  return `${formatter.format(start)} - ${formatter.format(end)}`;
}

function formatDateInputValue(date: Date) {
  return date.toISOString().slice(0, 10);
}

// ── component ───────────────────────────────────────────────────────────────

export const Dashboard: React.FC = () => {
  const queryClient = useQueryClient();

  // ── local state ──────────────────────────────────────────────────────────

  /** IDs currently pending (being polled). */
  const [pendingIds, setPendingIds] = useState<Set<string>>(() => new Set());

  /** Deadlines per correlation_id for timeout handling. */
  const deadlines = useRef<Map<string, number>>(new Map());

  const [activeCorrelationId, setActiveCorrelationId] = useState<string | null>(null);

  // Webhook form fields
  const [repository, setRepository] = useState('');
  const [prTitle, setPrTitle] = useState('');
  const [prBody, setPrBody] = useState('');
  const [commitMsg, setCommitMsg] = useState('');

  // Search & filter
  const [searchQuery, setSearchQuery] = useState('');
  const [verdictFilter, setVerdictFilter] = useState('all');

  // Header dropdowns
  const [isProjectDropdownOpen, setIsProjectDropdownOpen] = useState(false);
  const [isAlertsOpen, setIsAlertsOpen] = useState(false);
  const [timePeriod, setTimePeriod] = useState<'24h' | '7d' | '30d'>('24h');
  const [isCustomDateOpen, setIsCustomDateOpen] = useState(false);

  const [readNotificationIds, setReadNotificationIds] = useState<Set<string>>(() => new Set());

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  // ── aggregator health ────────────────────────────────────────────────────

  const healthQuery = useQuery({
    queryKey: ['aggregatorHealth'],
    queryFn: getAggregatorHealth,
    refetchInterval: 30_000,
    retry: 1,
  });
  const backendOnline = healthQuery.data?.status === 'healthy';

  const metricsQuery = useQuery({
    queryKey: ['deploymentMetrics', timePeriod],
    queryFn: () => getDeploymentMetrics({ period: timePeriod }),
    refetchInterval: 30_000,
    retry: 1,
  });

  const deploymentsQuery = useQuery({
    queryKey: ['dashboardDeployments'],
    queryFn: () => listDeployments({ page: 1, page_size: 100 }),
    refetchInterval: 30_000,
    retry: 1,
  });

  const agentStatusQuery = useQuery({
    queryKey: ['agentStatus'],
    queryFn: getAgentStatus,
    refetchInterval: 30_000,
    retry: 1,
  });

  const rows: DeploymentRow[] = ((deploymentsQuery.data?.items ?? []) as DeploymentSummary[]).map(
    dep => ({
      correlation_id: dep.correlation_id,
      repository: dep.repository,
      branch: dep.branch,
      status: dep.status,
      decision: dep.decision,
      overall_score: dep.overall_score,
      overall_confidence: dep.overall_confidence,
      severity: dep.severity,
      generated_at: dep.generated_at,
    }),
  );

  const notifications =
    agentStatusQuery.data?.agents.map(agent => {
      const id = agent.name;
      return {
        id,
        message: `${agent.name}: ${agent.status}`,
        time: agent.region ?? 'backend',
        unread: !readNotificationIds.has(id),
        type:
          agent.status === 'online'
            ? 'safe'
            : agent.status === 'degraded'
              ? 'alert'
              : 'block',
      };
    }) ?? [];

  // ── webhook trigger mutation ──────────────────────────────────────────────

  const triggerMutation = useMutation({
    mutationFn: (req: TriggerDeploymentRequest) => triggerDeployment(req),
    onSuccess: (response) => {
      const cid = response.correlation_id;
      setActiveCorrelationId(cid);

      // Register deadline
      deadlines.current.set(cid, Date.now() + POLL_TIMEOUT_MS);

      setPendingIds(prev => new Set([...prev, cid]));
    },
  });

  const handleSimulateWebhook = (e: React.FormEvent) => {
    e.preventDefault();
    triggerMutation.mutate({
      repository,
      pullRequestTitle: prTitle,
      pullRequestBody: prBody,
      commitMessage: commitMsg,
    });
  };

  // ── polling for pending decisions ─────────────────────────────────────────

  /**
   * Resolves one pending correlation_id against the real aggregator.
   * Called by the polling query below.
   */
  const resolveDecision = useCallback(
    async (cid: string): Promise<void> => {
      const deadline = deadlines.current.get(cid) ?? Date.now() + POLL_TIMEOUT_MS;

      if (Date.now() > deadline) {
        // Timeout — mark failed
        setPendingIds(prev => {
          const next = new Set(prev);
          next.delete(cid);
          return next;
        });
        deadlines.current.delete(cid);
        return;
      }

      const result = await getDecision(cid);

      if (result.status === 200 && isFinalDecision(result.data)) {
        const existingRow = rows.find(r => r.correlation_id === cid);
        rowFromDecision(cid, result.data, existingRow);
        setPendingIds(prev => {
          const next = new Set(prev);
          next.delete(cid);
          return next;
        });
        deadlines.current.delete(cid);

        // Clear active pipeline indicator when it resolves
        setActiveCorrelationId(prev => (prev === cid ? null : prev));
        queryClient.invalidateQueries({ queryKey: ['dashboardDeployments'] });
        queryClient.invalidateQueries({ queryKey: ['deploymentMetrics'] });
        queryClient.invalidateQueries({ queryKey: ['agentStatus'] });
      }
      // If 202 / pending → leave in set; will be retried on next poll interval
    },
    [queryClient, rows],
  );

  // Single polling query — re-runs every POLL_INTERVAL_MS while there are pending IDs
  useQuery({
    queryKey: ['pendingDecisions', Array.from(pendingIds).sort().join(',')],
    queryFn: async () => {
      if (pendingIds.size === 0) return null;
      await Promise.allSettled(Array.from(pendingIds).map(resolveDecision));
      return null;
    },
    enabled: pendingIds.size > 0,
    refetchInterval: POLL_INTERVAL_MS,
    refetchIntervalInBackground: true,
    // Don't cache stale results
    staleTime: 0,
    gcTime: 0,
  });

  // ── derived metrics ───────────────────────────────────────────────────────

  const total = metricsQuery.data?.total ?? 0;
  const safe = metricsQuery.data?.safe ?? 0;
  const blocked = metricsQuery.data?.blocked ?? 0;
  const avgScore = metricsQuery.data?.avgRisk ?? 0;
  const safePercentage = metricsQuery.data?.safePercentage ?? 0;
  const blockedPercentage = metricsQuery.data?.blockedPercentage ?? 0;
  const totalProgress = metricsQuery.data?.totalProgress ?? 0;
  const totalTrend = metricsQuery.data?.totalTrend;
  const riskLevel = metricsQuery.data?.riskLevel;
  const activeRepository = rows[0]?.repository ?? 'Repository';
  const selectedDateRange = getDateRange(timePeriod);

  // ── filtered + paginated rows ─────────────────────────────────────────────

  const filteredRows = rows.filter(dep => {
    const query = searchQuery.toLowerCase().trim();
    const matchesSearch =
      query === '' ||
      dep.repository.toLowerCase().includes(query) ||
      (dep.commit_message ?? '').toLowerCase().includes(query) ||
      (dep.branch ?? '').toLowerCase().includes(query) ||
      dep.correlation_id.toLowerCase().includes(query);

    const matchesVerdict =
      verdictFilter === 'all' ||
      (dep.decision && dep.decision.toLowerCase() === verdictFilter.toLowerCase()) ||
      (dep.status === 'pending' && verdictFilter === 'pending') ||
      (dep.status === 'failed' && verdictFilter === 'failed');

    return matchesSearch && matchesVerdict;
  });

  const totalPages = Math.ceil(filteredRows.length / itemsPerPage) || 1;
  const paginatedRows = filteredRows.slice(
    (currentPage - 1) * itemsPerPage,
    (currentPage - 1) * itemsPerPage + itemsPerPage,
  );

  // ── loading / error states ────────────────────────────────────────────────

  const isSubmitting = triggerMutation.isPending;
  const submitError = triggerMutation.error;
  const isInitialLoading =
    healthQuery.isLoading ||
    metricsQuery.isLoading ||
    deploymentsQuery.isLoading ||
    agentStatusQuery.isLoading;

  // ── render ────────────────────────────────────────────────────────────────

  return (
    <div className="dashboard-container fade-in">
      {/* ── Header ── */}
      <div className="dashboard-header-container">
        <div className="dashboard-header-left">
          <div className="title-area">
            <div className="title-icon-wrapper">
              <Shield className="title-icon" />
            </div>
            <h1>Platform Dashboard</h1>
          </div>
          <p className="description">
            Real-time security auditing and risk gating pipeline analytics.
          </p>
        </div>

        <div className="dashboard-header-right">
          {/* Project selector */}
          <div className="relative-container">
            <button
              onClick={() => setIsProjectDropdownOpen(!isProjectDropdownOpen)}
              className="control-btn font-mono"
            >
              <span>{activeRepository}</span>
              <ChevronDown className={`chevron-icon ${isProjectDropdownOpen ? 'rotated' : ''}`} />
            </button>
            {isProjectDropdownOpen && (
              <div className="dropdown-menu project-menu">
                <div className="menu-header">Active Repository</div>
                <div className="menu-item active">
                  <div className="item-title font-mono">
                    <span>{activeRepository}</span>
                    <Check className="check-icon" />
                  </div>
                  <p className="item-desc">Primary workspace codebase repository.</p>
                </div>
              </div>
            )}
          </div>

          {/* Notifications bell */}
          <div className="relative-container">
            <button
              onClick={() => setIsAlertsOpen(!isAlertsOpen)}
              className="control-btn bell-btn"
            >
              <Bell className="bell-icon" />
              {notifications.some(n => n.unread) && <span className="notification-dot" />}
            </button>
            {isAlertsOpen && (
              <div className="dropdown-menu alerts-menu">
                <div className="menu-header flex-header">
                  <span>Security Log</span>
                  <button
                    onClick={() =>
                      setReadNotificationIds(new Set(notifications.map(n => n.id)))
                    }
                    className="mark-read-btn"
                  >
                    Mark all read
                  </button>
                </div>
                <div className="alerts-list">
                  {notifications.map(n => (
                    <div key={n.id} className={`alert-item ${n.unread ? 'unread' : ''}`}>
                      <div className="alert-meta">
                        <span className="alert-time">{n.time}</span>
                        <span className={`alert-dot ${n.type}`} />
                      </div>
                      <p className="alert-msg">{n.message}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Time range selector */}
          <div className="timeframe-selector">
            <button
              onClick={() => setTimePeriod('24h')}
              className={`time-btn ${timePeriod === '24h' ? 'active' : ''}`}
            >
              24h
            </button>
            <button
              onClick={() => setTimePeriod('7d')}
              className={`time-btn ${timePeriod === '7d' ? 'active' : ''}`}
            >
              7d
            </button>
            <button
              onClick={() => setTimePeriod('30d')}
              className={`time-btn ${timePeriod === '30d' ? 'active' : ''}`}
            >
              30d
            </button>
            <div className="divider-line" />
            <button
              onClick={() => setIsCustomDateOpen(!isCustomDateOpen)}
              className="calendar-btn"
            >
              <Calendar className="calendar-icon" />
              <span>{formatDateRange(timePeriod)}</span>
            </button>
            {isCustomDateOpen && (
              <div className="dropdown-menu calendar-dropdown">
                <div className="calendar-header">
                  <span>Custom Timeframe</span>
                  <button onClick={() => setIsCustomDateOpen(false)} className="close-btn">
                    <X className="x-icon" />
                  </button>
                </div>
                <div className="calendar-body">
                  <div className="date-group">
                    <label>Start Date</label>
                    <input
                      type="date"
                      value={formatDateInputValue(selectedDateRange.start)}
                      readOnly
                      className="date-input"
                    />
                  </div>
                  <div className="date-group">
                    <label>End Date</label>
                    <input
                      type="date"
                      value={formatDateInputValue(selectedDateRange.end)}
                      readOnly
                      className="date-input"
                    />
                  </div>
                  <button onClick={() => setIsCustomDateOpen(false)} className="apply-btn">
                    Apply Filter
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* New deployment scroll button */}
          <button
            onClick={() => {
              const el = document.getElementById('webhook-simulator-section');
              if (el) el.scrollIntoView({ behavior: 'smooth' });
            }}
            className="new-deployment-btn font-mono"
          >
            New Deployment
          </button>
        </div>
      </div>

      {/* ── Backend status banner ── */}
      {!isInitialLoading && !backendOnline && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.6rem 1rem',
            marginBottom: '1rem',
            background: 'rgba(239,68,68,0.12)',
            border: '1px solid rgba(239,68,68,0.35)',
            borderRadius: '8px',
            color: '#f87171',
            fontSize: '0.8rem',
            fontFamily: 'monospace',
          }}
        >
          <AlertCircle size={14} />
          Aggregator service unreachable — submitted deployments will be queued locally.
        </div>
      )}

      {/* ── KPI Cards ── */}
      <div className="kpi-grid">
        <div className="kpi-card total-card">
          <div className="kpi-card-header">
            <span className="kpi-title">TOTAL AUDITED</span>
            <span className="trend-badge">
              <TrendingUp className="trend-icon" />
              {totalTrend}
            </span>
          </div>
          <div className="kpi-card-value font-mono">{total}</div>
          <div className="kpi-progress-bar">
            <div className="kpi-progress-fill primary" style={{ width: `${totalProgress}%` }} />
          </div>
        </div>

        <div className="kpi-card safe-card">
          <div className="kpi-card-header">
            <span className="kpi-title">PASSED SAFE</span>
          </div>
          <div className="kpi-card-value-group">
            <span className="kpi-card-value safe-text font-mono">{safe}</span>
            <span className="kpi-percentage font-mono">
              {safePercentage.toFixed(1)}%
            </span>
          </div>
          <div className="kpi-progress-bar">
            <div
              className="kpi-progress-fill secondary"
              style={{ width: `${safePercentage}%` }}
            />
          </div>
        </div>

        <div className="kpi-card blocked-card">
          <div className="kpi-card-header">
            <span className="kpi-title">ROLLOUT BLOCKED</span>
          </div>
          <div className="kpi-card-value-group">
            <span className="kpi-card-value error-text font-mono">{blocked}</span>
            <span className="kpi-percentage font-mono">
              {blockedPercentage.toFixed(1)}%
            </span>
          </div>
          <div className="kpi-progress-bar">
            <div
              className="kpi-progress-fill error"
              style={{ width: `${blockedPercentage}%` }}
            />
          </div>
        </div>

        <div className="kpi-card risk-card">
          <div className="kpi-card-header">
            <span className="kpi-title">AVERAGE RISK SCORE</span>
          </div>
          <div className="kpi-card-value-group">
            <span className="kpi-card-value font-mono">{avgScore}</span>
            <span className="kpi-score-max font-mono">/100</span>
          </div>
          <div className="risk-level-tag font-mono">
            {riskLevel === 'HIGH' ? (
              <span className="tag-high">HIGH RISK</span>
            ) : riskLevel === 'MEDIUM' ? (
              <span className="tag-medium">MEDIUM RISK</span>
            ) : (
              <span className="tag-low">LOW RISK</span>
            )}
          </div>
          <div className="kpi-progress-bar">
            <div
              className={`kpi-progress-fill ${riskLevel === 'HIGH' ? 'error' : riskLevel === 'MEDIUM' ? 'tertiary' : 'secondary'}`}
              style={{ width: `${avgScore}%` }}
            />
          </div>
        </div>
      </div>

      <div className="dashboard-content-layout">
        {/* ── Webhook Simulator ── */}
        <section id="webhook-simulator-section" className="webhook-simulator-panel">
          <h2>Simulate GitHub Webhook</h2>
          <p className="section-desc">
            Submit a pull request payload to trigger the multi-agent Kafka pipeline.
          </p>

          {/* Submit error banner */}
          {submitError && (
            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '0.5rem',
                padding: '0.6rem 1rem',
                marginBottom: '1rem',
                background: 'rgba(239,68,68,0.12)',
                border: '1px solid rgba(239,68,68,0.35)',
                borderRadius: '8px',
                color: '#f87171',
                fontSize: '0.8rem',
                fontFamily: 'monospace',
              }}
            >
              <AlertCircle size={14} style={{ marginTop: '2px', flexShrink: 0 }} />
              <span>
                Failed to submit webhook:{' '}
                {submitError instanceof Error ? submitError.message : String(submitError)}
              </span>
            </div>
          )}

          <form onSubmit={handleSimulateWebhook} className="simulator-form">
            <div className="form-group font-mono">
              <label>Target Repository</label>
              <input
                type="text"
                value={repository}
                onChange={e => setRepository(e.target.value)}
                required
              />
            </div>

            <div className="form-group font-mono">
              <label>Pull Request Title</label>
              <input
                type="text"
                value={prTitle}
                onChange={e => setPrTitle(e.target.value)}
                required
              />
            </div>

            <div className="form-group font-mono">
              <label>PR Description</label>
              <textarea
                rows={2}
                value={prBody}
                onChange={e => setPrBody(e.target.value)}
                required
              />
            </div>

            <div className="form-group font-mono">
              <label>Commit Message</label>
              <input
                type="text"
                value={commitMsg}
                onChange={e => setCommitMsg(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="simulate-btn font-mono" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="btn-icon spin" />
                  <span>Dispatching...</span>
                </>
              ) : (
                <>
                  <Play className="btn-icon" />
                  <span>Send GitHub Webhook Event</span>
                </>
              )}
            </button>
          </form>

          {/* Active pipeline status indicator */}
          {activeCorrelationId && pendingIds.has(activeCorrelationId) && (
            <div className="active-pipeline-status">
              <div className="pipeline-header">
                <h3>
                  Active Audit:{' '}
                  <span className="font-mono">{activeCorrelationId.substring(0, 10)}...</span>
                </h3>
                <Loader2 className="spin pipe-loader" />
              </div>
              <div className="pipeline-steps font-mono">
                <div className="step active">Gateway</div>
                <div className="step-arrow">
                  <ArrowRight size={14} />
                </div>
                <div className="step active">Kafka Topic</div>
                <div className="step-arrow">
                  <ArrowRight size={14} />
                </div>
                <div className="step active">Agents</div>
                <div className="step-arrow">
                  <ArrowRight size={14} />
                </div>
                <div className="step">Aggregator</div>
              </div>
            </div>
          )}
        </section>

        {/* ── Recent Audits Table ── */}
        <section className="recent-audits-panel">
          <div className="panel-header-row">
            <div className="title-desc-group">
              <h2>Recent Deployment Audits</h2>
              <p className="section-desc">
                Audit results compiled from the distributed evaluation engine.
              </p>
            </div>

            <div className="controls-row">
              {/* Search */}
              <div className="search-bar-wrapper">
                <Search className="search-icon" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={e => {
                    setSearchQuery(e.target.value);
                    setCurrentPage(1);
                  }}
                  placeholder="Filter by ID or Repo..."
                  className="search-input font-mono"
                />
              </div>

              {/* Verdict filter */}
              <div className="filter-dropdown-wrapper">
                <Sliders className="filter-icon" />
                <select
                  value={verdictFilter}
                  onChange={e => {
                    setVerdictFilter(e.target.value);
                    setCurrentPage(1);
                  }}
                  className="filter-select font-mono"
                >
                  <option value="all">Decision: All</option>
                  <option value="safe">SAFE</option>
                  <option value="review">REVIEW</option>
                  <option value="block">BLOCK</option>
                  <option value="pending">PENDING</option>
                </select>
              </div>
            </div>
          </div>

          <div className="audits-table-wrapper">
            {/* ── Loading state — health check in flight ── */}
            {isInitialLoading ? (
              <div className="loading-state">
                <Loader2 className="spin load-spinner" />
                <span>Connecting to backend...</span>
              </div>
            ) : deploymentsQuery.isError ? (
              <div className="empty-state">Unable to load deployment audits.</div>
            ) : rows.length === 0 ? (
              <div className="empty-state">
                No audits yet. Submit a webhook event above to begin.
              </div>
            ) : filteredRows.length === 0 ? (
              <div className="empty-state">No audits match current filters.</div>
            ) : (
              <>
                <table className="audits-table font-mono">
                  <thead>
                    <tr>
                      <th className="repo-th">Repo</th>
                      <th className="score-th">Score</th>
                      <th className="verdict-th">Verdict</th>
                      <th className="status-th">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedRows.map(dep => (
                      <tr key={dep.correlation_id} className="table-row">
                        <td className="repo-col">
                          <span className="repo-name">{dep.repository}</span>
                          <span className="commit-desc">{dep.commit_message ?? dep.branch}</span>
                        </td>
                        <td>
                          {dep.status === 'pending' ? (
                            <span className="score-pending">-</span>
                          ) : dep.status === 'failed' ? (
                            <span className="score-pending">-</span>
                          ) : (
                            <span
                              className={`score-badge ${(dep.overall_score ?? 0) >= 60
                                  ? 'high'
                                  : (dep.overall_score ?? 0) >= 30
                                    ? 'medium'
                                    : 'low'
                                }`}
                            >
                              {dep.overall_score}
                            </span>
                          )}
                        </td>
                        <td>
                          {dep.status === 'pending' ? (
                            <span className="verdict-tag pending">PENDING</span>
                          ) : dep.status === 'failed' ? (
                            <span className="verdict-tag" style={{ color: '#94a3b8' }}>
                              TIMEOUT
                            </span>
                          ) : (
                            <span className={`verdict-tag ${dep.decision?.toLowerCase()}`}>
                              {dep.decision}
                            </span>
                          )}
                        </td>
                        <td>
                          {dep.status === 'pending' ? (
                            <span className="status-label processing">
                              <Loader2 className="spin badge-spinner" />
                              Evaluating
                            </span>
                          ) : dep.status === 'failed' ? (
                            <span className="status-label" style={{ color: '#94a3b8' }}>
                              Timed out
                            </span>
                          ) : (
                            <span className="status-label completed">Done</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {/* Pagination */}
                <div className="table-pagination">
                  <p className="pagination-text">
                    Showing{' '}
                    <span className="highlight">
                      {(currentPage - 1) * itemsPerPage + 1}-
                      {Math.min(currentPage * itemsPerPage, filteredRows.length)}
                    </span>{' '}
                    of <span className="highlight">{filteredRows.length}</span> deployments
                  </p>
                  <div className="pagination-buttons">
                    <button
                      onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                      disabled={currentPage === 1}
                      className="page-nav-btn"
                    >
                      <ChevronLeft className="nav-chevron" />
                    </button>
                    {Array.from({ length: totalPages }).map((_, i) => (
                      <button
                        key={i}
                        onClick={() => setCurrentPage(i + 1)}
                        className={`page-num-btn font-mono ${currentPage === i + 1 ? 'active' : ''}`}
                      >
                        {i + 1}
                      </button>
                    ))}
                    <button
                      onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                      disabled={currentPage === totalPages}
                      className="page-nav-btn"
                    >
                      <ChevronRight className="nav-chevron" />
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </section>
      </div>
    </div>
  );
};
